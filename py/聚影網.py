# -*- coding: utf-8 -*-
"""
聚影网 (www.ni10.com) - TVBox 爬虫源 (maccms / myui 模板)
=========================================================
接口：homeContent / categoryContent(含筛选) / detailContent(懒加载)
      / playerContent(按需解析m3u8直链) / searchContent

站点实测结构：
1. 列表页：/vodshow/{tid}-----------.html(第1页)，翻页 /vodshow/{tid}--------{n}---.html
2. 排序筛选：/vodshow/{tid}--{by}---------.html（time/hits/score 实测生效，仅第1页）
   类型筛选 = 直接切换二级分类 tid
3. 详情页：/juyingtv/{vid}.html -> 播放源 tab(#playlist{n}) + 集数 /juyingtvkan/{vid}-{sid}-{nid}.html
4. 播放页：内嵌 player_xxxx JSON，url 字段即真实 m3u8 直链（json 标准转义斜杠）
5. 搜索：maccms suggest 接口（/index.php/ajax/suggest?mid=1&wd=，必须带 mid=1）
   兜底 /vodsearch/{kw}-------------.html + 分类爬取分词匹配
6. UA：PC/移动均可访问（移动端优先，兼容最稳）

速度优化：
- 全正则解析，零 bs4 依赖，解析开销极低
- 详情页懒加载：不再预解析所有集数 m3u8，秒开
- playerContent 按需解析 + 15分钟缓存 + 后台预取下一集
- 多级缓存：首页10分钟 / 分类5分钟 / 详情5分钟(失败30秒) / 搜索3分钟 / 播放15分钟
- 连接池复用(HTTPAdapter) + gzip 自动解压 + 短超时 + 0.2s 快速重试 + 429等待
- 搜索 suggest 接口一次 JSON 请求秒回，失败才降级
"""

import re
import json
import time
import threading
from urllib.parse import quote, urlencode

import requests
from requests.adapters import HTTPAdapter

try:
    from concurrent.futures import ThreadPoolExecutor, as_completed
except ImportError:
    ThreadPoolExecutor = None
    as_completed = None

try:
    import urllib3
    urllib3.disable_warnings()
except Exception:
    pass

try:
    import sys
    sys.path.append('..')
    from base.spider import Spider as _BaseSpider
except ImportError:
    _BaseSpider = None


# ============================================================
# 常量
# ============================================================
HOST = "https://www.ni10.com"

UA = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 "
    "Mobile/15E148 Safari/604.1"
)

# 超时（秒）
TIMEOUT_PAGE = 8
TIMEOUT_API = 5
TIMEOUT_PLAY = 4

# 缓存 TTL（秒）
TTL_HOME = 600
TTL_CAT = 300
TTL_DETAIL_OK = 300
TTL_DETAIL_EMPTY = 30
TTL_SEARCH = 180
TTL_PLAY = 900

# 排序选项（maccms 8段式第2段，实测生效）
SORTS = [
    {"n": "最新", "v": "time"},
    {"n": "最热", "v": "hits"},
    {"n": "评分", "v": "score"},
]

# 分类表（实测首页导航 / 聚合页 /juying/{id}.html 抓取）
# 一级分类 -> 二级分类（二级 tid 即类型筛选值）
CATS = [
    {"id": "1", "name": "电影", "subs": [
        ("6", "动作片"), ("7", "喜剧片"), ("8", "爱情片"), ("9", "科幻片"),
        ("10", "恐怖片"), ("11", "剧情片"), ("12", "战争片"), ("23", "纪录片"),
        ("38", "预告片"), ("39", "影视解说"), ("40", "4K电影"), ("46", "邵氏电影"),
        ("47", "悬疑片"), ("48", "犯罪片"), ("49", "奇幻片"),
    ]},
    {"id": "2", "name": "电视剧", "subs": [
        ("13", "国产剧"), ("14", "欧美剧"), ("15", "韩剧"), ("16", "日剧"),
        ("20", "港剧"), ("21", "台剧"), ("22", "泰剧"), ("24", "海外剧"),
    ]},
    {"id": "3", "name": "综艺", "subs": [
        ("25", "大陆综艺"), ("26", "日韩综艺"), ("27", "港台综艺"), ("28", "欧美综艺"),
        ("35", "演唱会"), ("36", "篮球"), ("37", "足球"),
    ]},
    {"id": "4", "name": "动漫", "subs": [
        ("29", "国产动漫"), ("30", "日韩动漫"), ("31", "欧美动漫"), ("32", "动画片"),
        ("33", "港台动漫"), ("34", "海外动漫"),
    ]},
    {"id": "5", "name": "短剧", "subs": [
        ("17", "爽文短剧"), ("18", "女频恋爱"), ("41", "反转爽剧"), ("42", "古装仙侠"),
        ("43", "年代穿越"), ("44", "脑洞悬疑"), ("45", "现代都市"), ("65", "有声动漫"),
    ]},
]


def _build_filters(cat):
    """构建筛选器：类型(二级分类) / 排序"""
    filters = [{
        "key": "class", "name": "类型",
        "value": [{"n": "全部", "v": ""}] + [{"n": n, "v": v} for v, n in cat["subs"]],
    }]
    filters.append({
        "key": "by", "name": "排序",
        "value": [{"n": "默认", "v": ""}] + SORTS,
    })
    return filters


# 全部分类 + 筛选器
ALL_CLASSES = [{"type_id": c["id"], "type_name": c["name"], "filter": 1} for c in CATS]
ALL_FILTERS = {c["id"]: _build_filters(c) for c in CATS}


# ============================================================
# Spider 主类
# ============================================================
_Base = _BaseSpider if _BaseSpider is not None else object


class Spider(_Base):
    siteUrl = HOST
    headers = {
        'User-Agent': UA,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9',
        'Accept-Encoding': 'gzip, deflate',
        'Referer': HOST + '/',
    }

    # 卡片解析（通用属性提取，不依赖属性顺序）
    _A_TAG_RE = re.compile(r'<a\b([^>]*)>', re.S)
    _ATTR_RE = re.compile(r'([\w-]+)\s*=\s*"([^"]*)"')
    _DETAIL_ID_RE = re.compile(r'/juyingtv/(\d+)\.html$')

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        self.session.headers['Connection'] = 'keep-alive'
        self.session.verify = False
        adapter = HTTPAdapter(
            pool_connections=20, pool_maxsize=40,
            max_retries=0, pool_block=False,
        )
        self.session.mount('http://', adapter)
        self.session.mount('https://', adapter)

        # 缓存容器 + 锁
        self._lock = threading.Lock()
        self._home_cache = []
        self._home_cache_time = 0
        self._cat_cache = {}
        self._detail_cache = {}
        self._search_cache = {}
        self._play_cache = {}
        self._prefetching = set()

    def init(self, extend=""):
        self.extend = extend or ""

    # ===== 网络工具 =====
    def _get(self, url, referer='', timeout=TIMEOUT_PAGE):
        headers = {'Connection': 'keep-alive'}
        if referer:
            headers['Referer'] = referer
        for attempt in range(2):
            try:
                r = self.session.get(url, timeout=timeout, headers=headers)
                if r.status_code == 429:
                    time.sleep(2.0)
                    continue
                r.raise_for_status()
                r.encoding = r.apparent_encoding or 'utf-8'
                return r
            except Exception:
                if attempt == 0:
                    time.sleep(0.2)
                else:
                    return None
        return None

    def _get_text(self, url, referer='', timeout=TIMEOUT_PAGE):
        r = self._get(url, referer, timeout)
        return r.text if r is not None else ""

    # ===== 缓存 =====
    @staticmethod
    def _cache_get(cache, key, ttl=None):
        item = cache.get(key)
        if item and time.time() - item[0] < (ttl if ttl is not None else item[2]):
            return item[1]
        return None

    @staticmethod
    def _cache_set(cache, key, value, ttl=TTL_CAT):
        if len(cache) > 512:
            cache.clear()
        cache[key] = (time.time(), value, ttl)

    # ===== 工具 =====
    @staticmethod
    def _abs(u):
        u = (u or '').strip()
        if not u:
            return ''
        if u.startswith('//'):
            return 'https:' + u
        if u.startswith('/'):
            return HOST + u
        if not u.startswith('http'):
            return HOST + '/' + u
        return u

    @staticmethod
    def _clean(text):
        """清理 HTML 文本：去标签、&nbsp;、多余空白"""
        if not text:
            return ''
        text = re.sub(r'<[^>]+>', '', text)
        text = text.replace('&nbsp;', ' ').replace('\u3000', ' ')
        return re.sub(r'\s+', ' ', text).strip()

    @staticmethod
    def _clean_name(raw):
        if not raw:
            return raw
        return re.sub(r'\s*[（(]\s*\d{4}\s*[）)]\s*$', '', raw.strip())

    @staticmethod
    def _pick_year(text):
        m = re.search(r'[（(]\s*(\d{4})\s*[）)]', text)
        if m:
            return m.group(1)
        m = re.search(r'\b(19\d{2}|20\d{2})\b', text)
        return m.group(1) if m else ''

    @staticmethod
    def _pick_remarks(text):
        patterns = [
            r'(连载至\s*[\d]+集)',
            r'(更新至\s*[\d]+集)',
            r'(更新到\s*[\d]+集)',
            r'(全[\d]+集)',
            r'(已完结|全集|正片|HD中字|HD国语|TC中字|HD)',
        ]
        for p in patterns:
            m = re.search(p, text)
            if m:
                return m.group(1)
        return ''

    # ===== 卡片解析 =====
    def _parse_cards(self, html, limit=36):
        if not html:
            return []
        items = {}
        for m in self._A_TAG_RE.finditer(html):
            attrs = dict(self._ATTR_RE.findall(m.group(1)))
            cls = attrs.get('class', '')
            if 'myui-vodlist__thumb' not in cls:
                continue
            href = attrs.get('href', '')
            vid = None
            dm = self._DETAIL_ID_RE.search(href)
            if dm:
                vid = dm.group(1)
            if not vid:
                continue
            title = (attrs.get('title') or '').strip()
            if not title:
                continue
            pic = attrs.get('data-original') or attrs.get('data-src') or attrs.get('src') or ''
            remarks = ''
            pm = re.search(r'class="pic-text[^"]*"[^>]*>([^<]+)<', m.group(0), re.S)
            if pm:
                remarks = pm.group(1).strip()
            if not remarks:
                remarks = self._pick_remarks(title)
            if vid not in items:
                items[vid] = {
                    'vod_id': vid,
                    'vod_name': self._clean_name(title),
                    'vod_pic': self._abs(pic),
                    'vod_remarks': remarks,
                }
        return list(items.values())[:limit]

    # ============================================================
    # 首页
    # ============================================================
    def homeContent(self, filter=False):
        vod_list = self._home_list()
        return {
            "class": ALL_CLASSES,
            "filters": ALL_FILTERS,
            "list": vod_list,
        }

    def homeVideoContent(self):
        return {"list": self._home_list()}

    def _home_list(self):
        now = int(time.time())
        with self._lock:
            if self._home_cache and now - self._home_cache_time < TTL_HOME:
                return self._home_cache[:60]
        try:
            html = self._get_text(HOST)
            vod_list = self._parse_cards(html, limit=60)
            if vod_list:
                with self._lock:
                    self._home_cache = vod_list
                    self._home_cache_time = int(time.time())
            return vod_list[:60]
        except Exception:
            return []

    # ============================================================
    # 分类列表
    # ============================================================
    def _empty_category(self, page=1):
        return {"list": [], "page": page, "pagecount": 1, "limit": 36, "total": 0}

    def categoryContent(self, tid, pg, filter, extend):
        page = 1
        try:
            page = max(1, int(pg or 1))
            ext = {}
            if extend:
                if isinstance(extend, dict):
                    ext = extend
                elif isinstance(extend, str):
                    try:
                        ext = json.loads(extend)
                    except Exception:
                        ext = {}

            # 类型筛选 = 切换二级分类 tid
            sub_tid = (ext.get('class') or '').strip() or str(tid)
            by = (ext.get('by') or '').strip()

            ckey = "%s|%s|%d" % (sub_tid, by, page)
            cached = self._cache_get(self._cat_cache, ckey, TTL_CAT)
            if cached is not None:
                return cached

            if by:
                # 排序路由（实测仅第1页有效，激活排序时 pagecount=1 防翻空页）
                url = f"{HOST}/vodshow/{sub_tid}--{by}---------.html"
            else:
                page_str = str(page) if page > 1 else ''
                url = f"{HOST}/vodshow/{sub_tid}--------{page_str}---.html"

            html = self._get_text(url)
            if not html:
                return self._empty_category(page)

            pagecount = 1
            if not by:
                nums = [int(x) for x in re.findall(
                    r'/vodshow/\d+--------(\d+)---\.html', html)]
                if nums:
                    pagecount = max(nums)
                else:
                    m = re.search(r'btn-warm[^>]*>\s*\d+\s*/\s*(\d+)\s*<', html)
                    if m:
                        pagecount = int(m.group(1))

            vod_list = self._parse_cards(html, limit=36)

            result = {
                "list": vod_list,
                "page": page,
                "pagecount": pagecount,
                "limit": 36,
                "total": pagecount * 36,
            }
            self._cache_set(self._cat_cache, ckey, result, TTL_CAT)
            return result
        except Exception:
            return self._empty_category(page)

    # ============================================================
    # 详情页（懒加载）
    # ============================================================
    def detailContent(self, ids):
        if isinstance(ids, str):
            ids = [ids]
        vid = str(ids[0]).split(',')[0].strip()
        if not vid:
            return {"list": []}

        cached = self._cache_get(self._detail_cache, vid, None)
        if cached is not None:
            return cached

        result = self._fetch_detail(vid)
        ttl = TTL_DETAIL_OK if result.get("list") else TTL_DETAIL_EMPTY
        self._cache_set(self._detail_cache, vid, result, ttl)

        if result.get("list"):
            self._prefetch_play(result["list"][0])
        return result

    def _fetch_detail(self, vid):
        html = self._get_text(f"{HOST}/juyingtv/{vid}.html")
        if not html:
            return {"list": []}

        # --- 基本信息 ---
        name = ''
        m = re.search(r'<h1[^>]*>([^<]+)</h1>', html)
        if m:
            name = self._clean_name(self._clean(m.group(1)))
        if not name:
            m = re.search(r'<title>([^<]+)</title>', html)
            if m:
                name = self._clean_name(self._clean(m.group(1)))

        pic = ''
        m = re.search(r'myui-content__thumb[^>]*>.*?<img\b[^>]*>', html, re.S)
        if not m:
            m = re.search(r'myui-player__info[^>]*>.*?<img\b[^>]*>', html, re.S)
        if m:
            tag = m.group(0)
            for attr in ('data-original', 'data-src', 'src'):
                am = re.search(attr + r'="([^"]+)"', tag)
                if am:
                    cand = self._abs(am.group(1))
                    if 'loading' not in cand:
                        pic = cand
                        break

        def _meta(label):
            # 值可能被 <a> 链接包裹（主演/导演/地区等），取到下一个标签或 </p> 为止再清理
            m = re.search(
                r'<span[^>]*>%s[^<]*</span>(.*?)(?=<span[^>]*>|</p>)' % re.escape(label),
                html, re.S)
            return self._clean(m.group(1)) if m else ''

        actor = _meta('主演')
        director = _meta('导演')
        area = _meta('地区')
        lang = _meta('语言')
        year = ''
        m = re.search(r'<span[^>]*>年份[^<]*</span>(.*?)(?=<span[^>]*>|</p>)', html, re.S)
        if m:
            ym = re.search(r'(19\d{2}|20\d{2})', self._clean(m.group(1)))
            if ym:
                year = ym.group(1)

        content = ''
        m = re.search(r'<meta[^>]*name="description"[^>]*content="([^"]*)"', html)
        if m:
            c = self._clean(m.group(1))
            im = re.search(r'剧情简介[:：]\s*(.+)', c)
            content = im.group(1) if im else c[:200]

        remarks = self._pick_remarks(html)

        type_name = ''
        m = re.search(
            r'<span[^>]*>分类[^<]*</span>(.*?)(?=<span[^>]*>|</p>)', html, re.S)
        if m:
            type_name = self._clean(m.group(1))

        # --- 播放源与集数 ---
        tabs = re.findall(r'href="#(playlist\d+)"[^>]*>([^<]+)</a>', html)
        play_groups = []
        seen_ep = set()
        for pid, src_name in tabs:
            pane = re.search(r'id="%s"[^>]*>(.*?)</ul>' % pid, html, re.S)
            eps = []
            if pane:
                for em in re.finditer(
                        r'href="(/juyingtvkan/\d+-\d+-\d+\.html)"[^>]*>([^<]+)</a>',
                        pane.group(1)):
                    ep_url = self._abs(em.group(1))
                    if ep_url in seen_ep:
                        continue
                    seen_ep.add(ep_url)
                    eps.append((em.group(2).strip() or '播放', ep_url))
            if eps:
                play_groups.append((src_name.strip() or '线路', eps))

        # 兜底：全页找播放链接（pane 结构异常时）
        if not play_groups:
            eps = []
            for em in re.finditer(
                    r'href="(/juyingtvkan/\d+-\d+-\d+\.html)"[^>]*>([^<]+)</a>', html):
                ep_url = self._abs(em.group(1))
                if ep_url in seen_ep:
                    continue
                seen_ep.add(ep_url)
                eps.append((em.group(2).strip() or '播放', ep_url))
            if eps:
                play_groups.append(('默认线路', eps))

        play_from, play_url = '', ''
        for src_name, eps in play_groups:
            ep_parts = [f"{n}${u}" for n, u in eps]
            play_from = (play_from + '$$$' + src_name) if play_from else src_name
            play_url = (play_url + '$$$' + '#'.join(ep_parts)) if play_url else '#'.join(ep_parts)

        detail = {
            "vod_id": vid,
            "vod_name": name or f"视频{vid}",
            "vod_pic": pic or HOST,
            "type_name": type_name,
            "vod_remarks": remarks or '',
            "vod_year": year,
            "vod_area": area,
            "vod_lang": lang,
            "vod_director": director,
            "vod_actor": actor,
            "vod_content": content,
            "vod_play_from": play_from or '默认',
            "vod_play_url": play_url or '',
        }
        return {"list": [detail]}

    # ============================================================
    # 播放解析（按需 + 缓存 + 预取）
    # ============================================================
    def _resolve_play(self, play_url):
        cached = self._cache_get(self._play_cache, play_url, TTL_PLAY)
        if cached:
            return cached
        real = ''
        try:
            text = self._get_text(play_url, referer=HOST + '/', timeout=TIMEOUT_PLAY)
            if text:
                m = re.search(r'var\s+player_\w+\s*=\s*(\{.*?\})\s*[;<]', text, re.S)
                if m:
                    try:
                        data = json.loads(m.group(1))  # \/ 转义由 json 自动处理
                        u = (data.get('url') or '').strip()
                        if u:
                            real = self._abs(u)
                    except Exception:
                        pass
                if not real:
                    m2 = re.search(r'"url"\s*:\s*"([^"]+\.m3u8[^"]*)"', text)
                    if m2:
                        real = self._abs(m2.group(1).replace('\\/', '/'))
                if not real:
                    m3 = re.search(r'"url"\s*:\s*"(https?://[^"]+)"', text)
                    if m3:
                        u = m3.group(1).replace('\\/', '/').strip()
                        if '.m3u8' in u or '.mp4' in u:
                            real = self._abs(u)
        except Exception:
            real = ''
        if real:
            self._cache_set(self._play_cache, play_url, real, TTL_PLAY)
        return real

    def _first_play_url(self, vod):
        for seg in (vod.get("vod_play_url") or "").split("$$$"):
            for item in seg.split("#"):
                parts = item.split("$", 1)
                if len(parts) == 2 and parts[1]:
                    return parts[1]
        return None

    def _prefetch_play(self, vod):
        target = self._first_play_url(vod)
        if not target:
            return
        with self._lock:
            if self._cache_get(self._play_cache, target, TTL_PLAY) or target in self._prefetching:
                return
            self._prefetching.add(target)

        def _job():
            try:
                self._resolve_play(target)
            except Exception:
                pass
            finally:
                with self._lock:
                    self._prefetching.discard(target)

        threading.Thread(target=_job, daemon=True).start()

    def _prefetch_next(self, play_url, vod_id):
        # 从播放 URL 中提取真实 vid（调用方传入的 vod_id 可能是 play_url 本身）
        if not vod_id or 'juyingtvkan' in str(vod_id):
            m = re.search(r'/juyingtvkan/(\d+)-', play_url)
            vod_id = m.group(1) if m else vod_id
        cached = self._cache_get(self._detail_cache, vod_id, TTL_DETAIL_OK)
        if not cached or not cached.get("list"):
            return
        vod = cached["list"][0]
        for seg in (vod.get("vod_play_url") or "").split("$$$"):
            items = seg.split("#")
            for i, item in enumerate(items):
                parts = item.split("$", 1)
                if len(parts) == 2 and self._abs(parts[1]) == play_url:
                    if i + 1 < len(items):
                        next_parts = items[i + 1].split("$", 1)
                        if len(next_parts) == 2 and next_parts[1]:
                            next_url = self._abs(next_parts[1])
                            with self._lock:
                                if (self._cache_get(self._play_cache, next_url, TTL_PLAY)
                                        or next_url in self._prefetching):
                                    return
                                self._prefetching.add(next_url)

                            def _job(url=next_url):
                                try:
                                    self._resolve_play(url)
                                except Exception:
                                    pass
                                finally:
                                    with self._lock:
                                        self._prefetching.discard(url)

                            threading.Thread(target=_job, daemon=True).start()
                    return

    def _play_payload(self, playurl):
        is_m3u8 = '.m3u8' in playurl.lower()
        return {
            "parse": 0,
            "playUrl": "",
            "url": playurl,
            "header": {
                "User-Agent": UA,
                "Referer": HOST + "/",
                "Origin": HOST,
            },
            "format": "application/x-mpegURL" if is_m3u8 else "",
            "contentType": "application/x-mpegURL" if is_m3u8 else "",
        }

    def playerContent(self, flag, id, vipFlags):
        if not id:
            return {"parse": 0, "playUrl": "", "url": ""}
        play_url = self._abs(str(id))

        cached = self._cache_get(self._play_cache, play_url, TTL_PLAY)
        if cached:
            self._prefetch_next(play_url, play_url)
            return self._play_payload(cached)

        m3u8 = self._resolve_play(play_url)
        if m3u8:
            self._prefetch_next(play_url, play_url)
            return self._play_payload(m3u8)

        # 主线路失败 -> 尝试同片其它播放源（并行）
        alts = self._alt_play_urls(play_url)
        if alts and ThreadPoolExecutor is not None:
            try:
                with ThreadPoolExecutor(max_workers=3) as ex:
                    futs = [ex.submit(self._resolve_play, u) for u in alts]
                    for f in as_completed(futs, timeout=TIMEOUT_PLAY):
                        u = f.result(timeout=TIMEOUT_PLAY)
                        if u:
                            self._cache_set(self._play_cache, play_url, u, TTL_PLAY)
                            return self._play_payload(u)
            except Exception:
                pass
        else:
            for u in alts:
                m = self._resolve_play(u)
                if m:
                    self._cache_set(self._play_cache, play_url, m, TTL_PLAY)
                    return self._play_payload(m)

        return {
            "parse": 1,
            "playUrl": "",
            "url": play_url,
            "header": {"User-Agent": UA, "Referer": HOST + "/"},
        }

    def _alt_play_urls(self, play_url, limit=6):
        m = re.search(r'/juyingtvkan/(\d+)-', play_url)
        if not m:
            return []
        vid = m.group(1)
        cached = self._cache_get(self._detail_cache, vid, TTL_DETAIL_OK)
        if not cached or not cached.get("list"):
            return []
        vod = cached["list"][0]
        out, seen = [], {play_url}
        for seg in (vod.get("vod_play_url") or "").split("$$$"):
            for item in seg.split("#"):
                parts = item.split("$", 1)
                if len(parts) == 2 and parts[1]:
                    u = parts[1]
                    if u not in seen:
                        seen.add(u)
                        out.append(u)
                        if len(out) >= limit:
                            return out
        return out

    # ============================================================
    # 搜索（suggest 接口 -> 站内搜索页 -> 分类爬取兜底）
    # ============================================================
    @staticmethod
    def _filter_by_keyword(cards, raw, limit=24):
        """分词模糊匹配 + 评分排序（比纯包含匹配命中率高得多）"""
        if not raw:
            return cards[:limit]
        raw = raw.lower().replace(' ', '').strip()
        if not raw:
            return cards[:limit]

        if len(raw) <= 2:
            tokens = [raw]
        else:
            tokens = [raw[i:i + 2] for i in range(0, len(raw) - 1)]
        tokens += list(raw)

        def score(name):
            name = (name or '').lower().replace(' ', '')
            if not name:
                return 0
            if raw in name:
                return 100
            return sum(1 for t in tokens if t in name)

        matched = [(score(c.get('vod_name') or ''), c) for c in cards]
        matched = [c for s, c in matched if s > 0]
        matched.sort(key=lambda c: score(c.get('vod_name') or ''), reverse=True)
        return matched[:limit]

    def _search_suggest(self, kw, page):
        """策略0：maccms suggest 接口（实测必须带 mid=1，一次 JSON 请求秒回）"""
        url = f"{HOST}/index.php/ajax/suggest?mid=1&wd={kw}&page={page}"
        text = self._get_text(url, referer=HOST + '/', timeout=TIMEOUT_API)
        if not text:
            return None
        text = text.strip()
        i = text.find('{')
        if i < 0:
            return None
        try:
            data = json.loads(text[i:])
        except Exception:
            return None
        out = []
        for it in (data.get('list') or data.get('data') or []):
            if not isinstance(it, dict):
                continue
            vid = str(it.get('id') or '')
            name = str(it.get('name') or '').strip()
            if vid and name:
                out.append({
                    'vod_id': vid,
                    'vod_name': self._clean_name(name),
                    'vod_pic': self._abs(it.get('pic') or ''),
                    'vod_remarks': str(it.get('remark') or ''),
                })
        return {"list": out} if out else None

    def _search_site(self, kw, raw):
        """策略1：站内搜索页 /vodsearch/{kw}-------------.html"""
        url = f"{HOST}/vodsearch/{kw}-------------.html"
        try:
            html = self._get_text(url, referer=HOST + '/', timeout=TIMEOUT_API)
            if not html:
                return None
            if '搜索功能' in html and ('关闭' in html or '暂停' in html):
                return None
            cards = self._parse_cards(html, limit=36)
            if not cards:
                return None
            matched = self._filter_by_keyword(cards, raw)
            return {"list": matched} if matched else None
        except Exception:
            return None

    def _search_by_scrape(self, raw):
        """策略2：分类爬取兜底（并行抓各分类第1-2页，分词评分过滤）"""
        pages = (1, 2)
        if len(raw) >= 3:
            pages = (1, 2, 3, 4)

        def _fetch_cat(args):
            cat_id, p = args
            page_str = str(p) if p > 1 else ''
            url = f"{HOST}/vodshow/{cat_id}--------{page_str}---.html"
            html = self._get_text(url, timeout=TIMEOUT_API)
            return self._parse_cards(html, limit=36)

        all_cards = []
        if ThreadPoolExecutor is not None:
            tasks = [(c['id'], p) for c in CATS for p in pages]
            with ThreadPoolExecutor(max_workers=5) as ex:
                futs = [ex.submit(_fetch_cat, t) for t in tasks]
                for f in as_completed(futs, timeout=TIMEOUT_API * 5):
                    try:
                        all_cards.extend(f.result(timeout=TIMEOUT_API))
                    except Exception:
                        continue
        else:
            for c in CATS:
                for p in pages:
                    try:
                        page_str = str(p) if p > 1 else ''
                        url = f"{HOST}/vodshow/{c['id']}--------{page_str}---.html"
                        html = self._get_text(url, timeout=TIMEOUT_API)
                        all_cards.extend(self._parse_cards(html, limit=36))
                    except Exception:
                        continue

        matched = self._filter_by_keyword(all_cards, raw, limit=24)
        return {"list": matched} if matched else None

    def searchContent(self, keyword, quick=False, pg=1):
        """多策略搜索：suggest 接口 -> 站内搜索页 -> 分类爬取兜底"""
        kw = quote((keyword or '').strip())
        raw = (keyword or '').strip().lower()
        if not kw:
            return {"list": [], "msg": "请输入搜索关键词"}

        page = int(pg or 1)
        ckey = f"{page}|{raw}"
        cached = self._cache_get(self._search_cache, ckey, TTL_SEARCH)
        if cached is not None:
            return cached

        result = self._search_suggest(kw, page)
        if not result:
            result = self._search_site(kw, raw)
        if not result:
            result = self._search_by_scrape(raw)

        if result and result.get("list"):
            self._cache_set(self._search_cache, ckey, result, TTL_SEARCH)
            return result

        result = {"list": [], "msg": "未找到相关内容，请尝试其他关键词或通过分类浏览"}
        self._cache_set(self._search_cache, ckey, result, TTL_SEARCH)
        return result

    # ============================================================
    # 本地代理 & 清理
    # ============================================================
    def localProxy(self, param):
        return [200, "video/MP2T", b"", ""]

    def destroy(self):
        try:
            self.session.close()
        except Exception:
            pass

    def close(self):
        self.destroy()


# ============================================================
# 本地测试
# ============================================================
if __name__ == '__main__':
    import sys as _sys
    s = Spider()
    action = _sys.argv[1] if len(_sys.argv) > 1 else 'home'
    if action == 'home':
        print(json.dumps(s.homeContent(), ensure_ascii=False)[:900])
    elif action == 'category':
        tid = _sys.argv[2] if len(_sys.argv) > 2 else '1'
        pg = _sys.argv[3] if len(_sys.argv) > 3 else '1'
        cl = _sys.argv[4] if len(_sys.argv) > 4 else ''
        by = _sys.argv[5] if len(_sys.argv) > 5 else ''
        ext = {}
        if cl:
            ext['class'] = cl
        if by:
            ext['by'] = by
        print(json.dumps(
            s.categoryContent(tid, pg, False, ext), ensure_ascii=False)[:900])
    elif action == 'detail':
        vid = _sys.argv[2] if len(_sys.argv) > 2 else '26239'
        r = s.detailContent(vid)
        d = r['list'][0] if r.get('list') else {}
        print(json.dumps(d, ensure_ascii=False)[:900])
    elif action == 'play':
        pid = _sys.argv[2] if len(_sys.argv) > 2 else ''
        print(json.dumps(s.playerContent('', pid, []), ensure_ascii=False)[:600])
    elif action == 'search':
        kw = _sys.argv[2] if len(_sys.argv) > 2 else '协商'
        print(json.dumps(s.searchContent(kw), ensure_ascii=False)[:600])
