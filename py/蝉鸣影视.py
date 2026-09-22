# -*- coding: utf-8 -*-
"""
chanmea (chanmea.cc / chanaas.cc) - TVBox 爬虫源（兼容 TVBox 裁剪 Python）
================================================================================
mytheme 伪静态模板，无公开采集 JSON，全部走 HTML 列表/详情/播放页解析：
- 一级分类：?cates-<id>.html / ?cates-<id>-<page>.html
- 二级分类：?lists-<id>.html / ?lists-<id>-<page>.html
- 详情页  ：?vodss-<id>.html
- 播放页  ：?plays-<vid>-<src>-<ep>.html（页内含 m3u8 直链，直链直出提速）
- 搜索页  ：/?search.html&keyword=<词>（站点单页返回全部结果）

接口：homeContent / homeVideoContent / categoryContent / detailContent /
playerContent / searchContent，支持二级分类（filters）、搜索、播放直链直出、
域名跟踪（多镜像自动探测切换）。

速度优化：
- 列表/搜索/详情均为单次请求；超时列表 5 秒 / 页面 6 秒；
- 首页/分类/详情/播放/搜索结果带 TTL 缓存；
- 播放页直接提取 m3u8 直链返回（实测无需 Referer 即可拉流），
  不再要求 TVBox 加载第三方解析页。

TVBox 兼容性改造：
- 移除 concurrent.futures（Python 2.7 缺失）；
- ssl 缺失时静默降级；
- 零 print；
"""

import gzip
import json
import re
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

# ============================================================
# 常量
# ============================================================
# 种子域名（chanmea 族；chanaas.cc 为异站已剔除，仅作友情链接存在）
SEED_DOMAINS = [
    "https://chanmea.cc",
]

# 域名发现正则：从页面中扫描同族镜像域名（chanmea.*，多后缀）
_DOMAIN_RE = re.compile(
    r'https?://(?:[a-z0-9-]+\.)*chanmea[a-z0-9-]*\.'
    r'(?:cc|top|app|ink|com|net|org|xyz)')

UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
      "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 "
      "Mobile/15E148 Safari/604.1")

TIMEOUT_LIST = 5
TIMEOUT_PAGE = 6
TIMEOUT_PROBE = 4
DOMAIN_PROBE_TTL = 60
REFRESH_DOMAINS_TTL = 600

TTL_HOME = 600
TTL_CAT = 300
TTL_DETAIL = 300
TTL_PLAY = 60
TTL_SEARCH = 180

SEARCH_MIN_INTERVAL = 0.3
PAGE_SIZE = 40

# 一级分类
CATS = [
    {"type_id": "1", "type_name": "电影"},
    {"type_id": "15", "type_name": "连续剧"},
    {"type_id": "24", "type_name": "综艺"},
    {"type_id": "30", "type_name": "动漫"},
    {"type_id": "47", "type_name": "短剧"},
]

# 二级分类（一级 -> lists id 列表）。站点实测得出，无公开 JSON 时直接内置。
SUBS = {
    "1": [
        ("2", "动作片"), ("3", "喜剧片"), ("4", "爱情片"), ("5", "科幻片"),
        ("6", "恐怖片"), ("7", "剧情片"), ("8", "战争片"), ("9", "纪录片"),
        ("10", "悬疑片"), ("11", "动画片"), ("12", "犯罪片"), ("13", "奇幻片"),
        ("14", "邵氏电影"),
    ],
    "15": [
        ("16", "国产剧"), ("17", "香港剧"), ("18", "台湾剧"), ("19", "美国剧"),
        ("20", "韩国剧"), ("21", "日本剧"), ("22", "海外剧"), ("23", "泰剧"),
    ],
    "24": [
        ("25", "大陆综艺"), ("26", "日韩综艺"), ("27", "港台综艺"),
        ("28", "欧美综艺"), ("29", "演唱会"),
    ],
    "30": [
        ("31", "国产动漫"), ("32", "日韩动漫"), ("33", "欧美动漫"),
        ("34", "港台动漫"), ("35", "海外动漫"),
    ],
    "47": [
        ("48", "有声动漫"), ("49", "女频恋爱"), ("50", "反转爽剧"),
        ("51", "脑洞悬疑"), ("52", "年代穿越"), ("53", "古装仙侠"),
        ("54", "现代都市"),
    ],
}


# ============================================================
# Spider 主类
# ============================================================
class Spider(object):

    siteUrl = SEED_DOMAINS[0]

    headers = {
        'User-Agent': UA,
        'Accept': 'text/html,application/xhtml+xml,application/json,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9',
        'Accept-Encoding': 'gzip, deflate',
    }

    def __init__(self):
        self._lock = threading.Lock()
        try:
            import ssl
            try:
                self._ctx = ssl.create_default_context()
                self._ctx.check_hostname = False
                self._ctx.verify_mode = ssl.CERT_NONE
            except Exception:
                self._ctx = None
        except Exception:
            self._ctx = None
        try:
            import ssl
            if self._ctx:
                self._opener = urllib.request.build_opener(
                    urllib.request.ProxyHandler({}),
                    urllib.request.HTTPSHandler(context=self._ctx),
                    urllib.request.HTTPRedirectHandler())
            else:
                self._opener = urllib.request.build_opener(
                    urllib.request.ProxyHandler({}),
                    urllib.request.HTTPSHandler(),
                    urllib.request.HTTPRedirectHandler())
        except Exception:
            self._opener = urllib.request.build_opener(
                urllib.request.ProxyHandler({}),
                urllib.request.HTTPRedirectHandler())

        self._domains = list(SEED_DOMAINS)
        self._domain = None
        self._domain_ok_at = 0.0
        self._last_refresh = 0.0

        self._home_cache = []
        self._home_cache_time = 0
        self._cat_cache = {}
        self._detail_cache = {}
        self._play_cache = {}
        self._search_cache = {}
        self._search_last_req = 0.0

    def init(self, extend=""):
        self.extend = extend or ""

    # ============================================================
    # 网络核心
    # ============================================================
    def _request(self, url, timeout=TIMEOUT_LIST, referer='', retry=1):
        hdrs = dict(self.headers)
        if referer:
            hdrs['Referer'] = referer
        for attempt in range(retry + 1):
            resp = None
            req = urllib.request.Request(url, headers=hdrs)
            try:
                resp = self._opener.open(req, timeout=timeout)
                content = resp.read()
            except urllib.error.HTTPError as e:
                try:
                    content = e.read()
                    resp = e
                except Exception:
                    content = None
            except Exception:
                content = None
            if content is None:
                if attempt < retry:
                    time.sleep(0.3)
                    continue
                return ''
            if resp is None:
                return ''
            try:
                enc = resp.headers.get('Content-Encoding', '')
            except Exception:
                enc = ''
            if enc and 'gzip' in enc:
                try:
                    content = gzip.decompress(content)
                except Exception:
                    pass
            try:
                return content.decode('utf-8', 'ignore')
            except Exception:
                try:
                    return content.decode('gbk', 'ignore')
                except Exception:
                    return ''

    def _abs(self, rel):
        """相对页面 URL -> 当前域绝对 URL；已带协议则原样返回。"""
        if not rel:
            return rel
        if rel.startswith('http'):
            return rel
        domain = self._get_domain()
        if not domain:
            return rel
        return '%s/%s' % (domain.rstrip('/'), rel.lstrip('/'))

    # ============================================================
    # 域名跟踪
    # ============================================================
    def _refresh_domains(self, force=False):
        now = time.time()
        if not force and now - self._last_refresh < REFRESH_DOMAINS_TTL:
            return True
        text = ''
        for d in self._domains[:2]:
            text = (self._request('%s/?cates-1.html' % d.rstrip('/'),
                                  timeout=TIMEOUT_LIST) or '')
            if text:
                break
        doms = sorted(set(_DOMAIN_RE.findall(str(text or ''))))
        doms = [d for d in doms if d]
        if not doms:
            doms = list(SEED_DOMAINS)
        else:
            cur = self._domain
            if cur in doms:
                doms.remove(cur)
                doms.insert(0, cur)
        for d in SEED_DOMAINS:
            if d not in doms:
                doms.append(d)
        with self._lock:
            self._domains = doms
            self._last_refresh = time.time()
        return bool(doms)

    def _probe_domain(self, domain):
        """以分类首页为探针：能返回同构卡片即视为可用。"""
        url = '%s/?cates-1.html' % domain.rstrip('/')
        text = self._request(url, timeout=TIMEOUT_PROBE)
        if not text:
            return False
        # 同构特征：存在 vodss 详情链接与 cates 分类链接
        if '?vodss-' in text and '?cates-1.html' in text:
            return True
        return False

    def _get_domain(self):
        with self._lock:
            if (self._domain and
                    time.time() - self._domain_ok_at < DOMAIN_PROBE_TTL):
                return self._domain
            if self._domain:
                cands = ([self._domain] +
                         [d for d in self._domains if d != self._domain])
            else:
                cands = list(self._domains)
        for d in cands:
            if self._probe_domain(d):
                with self._lock:
                    self._domain = d
                    self._domain_ok_at = time.time()
                return d
        if self._refresh_domains(force=True):
            with self._lock:
                cands = list(self._domains)
            for d in cands:
                if self._probe_domain(d):
                    with self._lock:
                        self._domain = d
                        self._domain_ok_at = time.time()
                    return d
        with self._lock:
            self._domain = (self._domains[0] if self._domains
                            else SEED_DOMAINS[0])
            self._domain_ok_at = time.time()
        return self._domain

    def _switch_domain(self):
        with self._lock:
            self._domain = None
            self._domain_ok_at = 0.0
            if len(self._domains) > 1:
                self._domains = self._domains[1:] + self._domains[:1]

    # ============================================================
    # 数据映射与列表页解析
    # ============================================================
    @staticmethod
    def _clean(text):
        if not text:
            return ''
        s = re.sub(r'<[^>]+>', '', text)
        s = re.sub(r'&nbsp;?', ' ', s)
        s = re.sub(r'\s+', ' ', s).strip()
        return s[:500]

    @staticmethod
    def _card(vid, name, pic, remarks):
        return {
            'vod_id': str(vid).strip(),
            'vod_name': name,
            'vod_pic': pic,
            'vod_remarks': remarks,
        }

    def _parse_list(self, html):
        """解析列表页卡片（首页/分类页/搜索页共用 myui-vodlist__thumb）。"""
        items, seen = [], set()
        if not html:
            return items
        for m in re.finditer(
                r'<a class="myui-vodlist__thumb[^>]*>(.*?)</a>',
                html, re.S):
            block = m.group(0)
            hm = re.search(r'href="\?vodss-([0-9]+)\.html"', block)
            if not hm:
                continue
            vid = hm.group(1)
            if vid in seen:
                continue
            nm = re.search(r'title="([^"]*)"', block)
            name = Spider._clean(nm.group(1)) if nm else ''
            pm = re.search(r'data-original="([^"]+)"', block)
            pic = pm.group(1).strip() if pm else ''
            if pic.startswith('/'):
                pic = ''
            rm = re.search(
                r'<span class="[^"]*pic-text[^"]*"[^>]*>([^<]*)</span>',
                block)
            remarks = Spider._clean(rm.group(1)) if rm else ''
            if not remarks:
                for tm in re.finditer(
                        r'<span class="[^"]*pic-tag[^"]*"[^>]*>([^<]*)</span>',
                        block):
                    remarks = Spider._clean(tm.group(1))
                    if remarks:
                        break
            if not name:
                tm = re.search(r'>([^<]+)</a>', block)
                if tm:
                    name = Spider._clean(tm.group(1))
            if not name:
                continue
            seen.add(vid)
            items.append(self._card(vid, name, pic, remarks))
        return items

    def _parse_search(self, html):
        """解析搜索页结果行（li.clearfix 列表结构）。"""
        items, seen = [], set()
        if not html:
            return items
        for m in re.finditer(r'<li class="clearfix">(.*?)</li>', html, re.S):
            block = m.group(1)
            hm = re.search(r'href="\?vodss-([0-9]+)\.html"', block)
            if not hm:
                continue
            vid = hm.group(1)
            if vid in seen:
                continue
            nm = re.search(r'title="([^"]+)"', block)
            name = Spider._clean(nm.group(1)) if nm else ''
            if not name:
                am = re.search(r'<h4[^>]*>.*?>([^<]+)</a>', block, re.S)
                if am:
                    name = Spider._clean(am.group(1))
            if not name:
                continue
            pm = re.search(r'data-original="([^"]+)"', block)
            pic = pm.group(1).strip() if pm else ''
            if pic.startswith('/'):
                pic = ''
            remarks = ''
            for tm in re.finditer(
                    r'<span class="[^"]*pic-tag[^"]*"[^>]*>([^<]*)</span>',
                    block):
                remarks = Spider._clean(tm.group(1))
                if remarks:
                    break
            seen.add(vid)
            items.append(self._card(vid, name, pic, remarks))
        return items

    def _parse_pages(self, html, mark):
        """从列表页解析页码控件取最大页数；无控件时返回 1。"""
        if not html:
            return 1
        nums = [int(m[0]) for m in re.findall(
            r'<a[^>]+href="\?%s-(\d+)\.html"[^>]*>(\d+)</a>'
            % re.escape(mark), html)]
        return max(nums) if nums else 1

    # ============================================================
    # 分类
    # ============================================================
    def _build_filters(self, tid):
        sub = [{"n": n, "v": v} for v, n in SUBS.get(tid, [])]
        if not sub:
            return []
        return [{
            'key': 't',
            'name': '分类',
            'value': [{"n": "全部", "v": ""}] + sub,
        }]

    def _empty_category(self, page=1):
        return {'list': [], 'page': page, 'pagecount': 1,
                'limit': PAGE_SIZE, 'total': 0}

    def _load_category(self, mark, page):
        """mark: 'cates-<tid>' 或 'lists-<lid>'。"""
        try:
            page = max(1, int(page or 1))
        except Exception:
            page = 1
        ckey = 'cat|%s|%d' % (mark, page)
        cached = self._cache_get(self._cat_cache, ckey, TTL_CAT)
        if cached is not None:
            return cached
        if page <= 1:
            rel = '?%s.html' % mark
        else:
            rel = '?%s-%d.html' % (mark, page)
        domain = self._get_domain()
        if not domain:
            return self._empty_category(page)
        html = self._request('%s/%s' % (domain.rstrip('/'), rel),
                             timeout=TIMEOUT_LIST, referer=domain + '/')
        items = self._parse_list(html)
        pagecount = self._parse_pages(html, mark)
        result = {
            'list': items,
            'page': page,
            'pagecount': max(pagecount, page),
            'limit': PAGE_SIZE,
            'total': len(items),
        }
        if items:
            self._cache_set(self._cat_cache, ckey, result, TTL_CAT)
        return result

    def categoryContent(self, tid, pg, filter, extend):
        ext = {}
        if isinstance(extend, dict):
            ext = extend
        elif isinstance(extend, str) and extend:
            try:
                ext = json.loads(extend)
            except Exception:
                ext = {}
        tid = str(tid or '').strip()
        sub = str(ext.get('t') or '').strip()
        if sub:
            result = self._load_category('lists-%s' % sub, pg)
        else:
            result = self._load_category('cates-%s' % tid, pg)
        filt = self._build_filters(tid)
        if filt:
            result['filters'] = filt
        return result

    # ============================================================
    # 首页
    # ============================================================
    def homeContent(self, filter=False):
        filters = {}
        for c in CATS:
            filters[c['type_id']] = self._build_filters(c['type_id'])
        return {
            'class': list(CATS),
            'filters': filters,
            'list': self._load_home()[:60],
        }

    def homeVideoContent(self):
        return {'list': self._load_home()[:60]}

    def _load_home(self):
        now = int(time.time())
        with self._lock:
            if self._home_cache and now - self._home_cache_time < TTL_HOME:
                return self._home_cache
        domain = self._get_domain()
        if not domain:
            return []
        html = self._request('%s/' % domain.rstrip('/'),
                             timeout=TIMEOUT_LIST, referer=domain + '/')
        items = self._parse_list(html)
        if items:
            with self._lock:
                self._home_cache = items
                self._home_cache_time = int(time.time())
        return items

    # ============================================================
    # 详情（HTML 页解析，多线路）
    # ============================================================
    def _parse_pdetail(self, html, vid):
        """从 ?vodss-<id>.html 提取影片信息 + 多线路播放列表。"""
        if not html:
            return None
        title = ''
        m = re.search(r'<title>([^<]*)</title>', html)
        if m:
            title = Spider._clean(m.group(1))
        # 名称：优先 h1
        name = ''
        m = re.search(r'<h1[^>]*>(.*?)</h1>', html, re.S)
        if m:
            name = Spider._clean(m.group(1))
        if not name and title:
            nm = re.search(r'《([^》]+)》', title)
            if nm:
                name = nm.group(1).strip()
            else:
                name = title.split(',')[0].strip()
        # 封面
        pic = ''
        m = re.search(r'<img[^>]+data-original="([^"]+)"', html)
        if m:
            pic = m.group(1).strip()
        if pic.startswith('/'):
            pic = ''
        # 分类 / 地区 / 年份
        type_name = area = year = ''
        m = re.search(r'分类：</span>\s*<a[^>]*>([^<]+)</a>', html)
        if m:
            type_name = Spider._clean(m.group(1))
        m = re.search(r'地区：</span>\s*<a[^>]*>([^<]+)</a>', html)
        if m:
            area = Spider._clean(m.group(1))
        m = re.search(r'年份：</span>\s*<a[^>]*>([^<]+)</a>', html)
        if m:
            year = Spider._clean(m.group(1))
        # 主演 / 导演
        actor = ''
        m = re.search(r'主演：</span>(.*?)</p>', html, re.S)
        if m:
            actor = Spider._clean(m.group(1))
        director = ''
        m = re.search(r'导演：</span>\s*<a[^>]*>([^<]+)</a>', html)
        if m:
            director = Spider._clean(m.group(1))
        # 更新备注（"更新第04集"/"更新HD"…）
        remarks = ''
        m = re.search(r'更新((?:第\d+集?|[A-Za-z0-9]{1,8}))', title)
        if m:
            remarks = m.group(1).strip()
        # 简介
        content = ''
        m = re.search(r'<p class="desc[^"]*"[^>]*>(.*?)</p>', html, re.S)
        if m:
            content = Spider._clean(m.group(1))
            if content.startswith('简介：'):
                content = content[3:].strip()
        # 播放线路与剧集
        groups = []
        for sm in re.finditer(
                r'<a href="#playlist([0-9]+)" data-toggle="tab">(.*?)</a>',
                html):
            src = sm.group(1)
            line_name = Spider._clean(sm.group(2))
            pm = re.search(
                r'<div id="playlist%s"[^>]*>(.*?)</ul>\s*</div>' % src,
                html, re.S)
            block = pm.group(1) if pm else ''
            eps = []
            for em in re.finditer(
                    r'href="\?plays-%s-%s-([0-9]+)\.html"[^>]*>([^<]+)</a>'
                    % (re.escape(vid), re.escape(src)), block):
                ep_name = Spider._clean(em.group(2))
                if not ep_name:
                    continue
                eps.append('%s$?plays-%s-%s-%s.html'
                           % (ep_name, vid, src, em.group(1)))
            if eps:
                groups.append((line_name, '#'.join(eps)))
        if not groups:
            return None
        play_from = '$$$'.join([g[0] for g in groups])
        play_url = '$$$'.join([g[1] for g in groups])
        return {
            'vod_id': vid,
            'vod_name': name,
            'vod_pic': pic,
            'type_name': type_name,
            'vod_year': year,
            'vod_area': area,
            'vod_director': director,
            'vod_actor': actor,
            'vod_remarks': remarks,
            'vod_play_from': play_from,
            'vod_play_url': play_url,
            'vod_content': content,
        }

    def detailContent(self, ids):
        if isinstance(ids, str):
            ids = [ids]
        try:
            raw = str(ids[0]).split(',')[0].strip()
        except Exception:
            raw = ''
        m = re.search(r'(\d+)', raw)
        if not m:
            return {'list': []}
        vid = m.group(1)
        cached = self._cache_get(self._detail_cache, vid, TTL_DETAIL)
        if cached is not None:
            return cached
        domain = self._get_domain()
        if not domain:
            return {'list': []}
        html = self._request('%s/?vodss-%s.html' % (domain.rstrip('/'), vid),
                             timeout=TIMEOUT_PAGE, referer=domain + '/')
        item = self._parse_pdetail(html, vid)
        if item:
            result = {'list': [item]}
            self._cache_set(self._detail_cache, vid, result, TTL_DETAIL)
            return result
        return {'list': []}

    # ============================================================
    # 播放（play 页 iframe 提取 m3u8 直链，直链直出）
    # ============================================================
    def _parse_play(self, html):
        """从播放页提取直链：iframe url= 参数优先，其次 iframe 整体。"""
        if not html:
            return ''
        m = re.search(r'<iframe[^>]+src="([^"]+)"', html, re.I)
        if not m:
            return ''
        frame = m.group(1).strip()
        q = re.search(r'[?&]url=([^&"\'<>]+)', frame)
        if q:
            return urllib.parse.unquote(q.group(1)).strip()
        return frame

    def playerContent(self, flag, id, vipFlags):
        if not id:
            return {'parse': 0, 'playUrl': '', 'url': ''}
        domain = self._get_domain()
        # 传入的已是直链，直接透传
        if id.startswith('http'):
            low = id.lower()
            is_m3u8 = '.m3u8' in low
            return {
                'parse': 0,
                'playUrl': '',
                'url': id,
                'header': {'User-Agent': UA, 'Referer': domain + '/'},
                'format': 'application/x-mpegURL' if is_m3u8 else '',
                'contentType': 'application/x-mpegURL' if is_m3u8 else '',
            }
        cached = self._cache_get(self._play_cache, id, TTL_PLAY)
        if cached is not None:
            return cached
        # 传入的是播放页相对 URL（?plays-<vid>-<src>-<ep>.html）
        rel = id if id.startswith('/') else ('/' + id)
        html = self._request('%s%s' % (domain.rstrip('/'), rel),
                             timeout=TIMEOUT_PAGE, referer=domain + '/')
        play = self._parse_play(html)
        if not play:
            # 兜底：把播放页当页面返回
            result = {
                'parse': 0,
                'playUrl': '',
                'url': domain + rel,
                'header': {'User-Agent': UA, 'Referer': domain + '/'},
            }
        elif ('.m3u8' in play.lower() or '.mp4' in play.lower()
              or 'm3u8' in play.lower()):
            is_m3u8 = '.m3u8' in play.lower()
            result = {
                'parse': 0,
                'playUrl': '',
                'url': play,
                'header': {'User-Agent': UA, 'Referer': domain + '/'},
                'format': 'application/x-mpegURL' if is_m3u8 else '',
                'contentType': 'application/x-mpegURL' if is_m3u8 else '',
            }
        else:
            # iframe 是网页解析器：交给 TVBox WebView
            result = {'parse': 1, 'playUrl': '', 'url': play}
        self._cache_set(self._play_cache, id, result, TTL_PLAY)
        return result

    # ============================================================
    # 搜索（站点单页全量返回，无真实分页）
    # ============================================================
    def _search_throttle(self):
        wait = SEARCH_MIN_INTERVAL - (time.time() - self._search_last_req)
        if wait > 0:
            time.sleep(wait)
        self._search_last_req = time.time()

    def searchContent(self, key, quick=False, pg="1"):
        key = (key or '').strip()
        empty = {'list': [], 'page': 1, 'pagecount': 1,
                 'limit': PAGE_SIZE, 'total': 0}
        if not key:
            return empty
        try:
            page = max(1, int(pg or 1))
        except Exception:
            page = 1
        ckey = 'sea|%s|%d' % (key, page)
        cached = self._cache_get(self._search_cache, ckey, TTL_SEARCH)
        if cached is not None and cached.get('list'):
            return cached
        domain = self._get_domain()
        if not domain:
            return empty
        if not quick:
            self._search_throttle()
        url = '%s/?search.html&keyword=%s' % (
            domain.rstrip('/'), urllib.parse.quote(key))
        html = self._request(url, timeout=TIMEOUT_LIST,
                             referer=domain + '/')
        items = self._parse_search(html)
        result = {
            'list': items,
            'page': page,
            'pagecount': 1,
            'limit': PAGE_SIZE,
            'total': len(items),
        }
        if items:
            self._cache_set(self._search_cache, ckey, result, TTL_SEARCH)
        return result

    # ===== 缓存 =====
    @staticmethod
    def _cache_get(cache, key, ttl=None):
        item = cache.get(key)
        if item and time.time() - item[0] < (ttl if ttl is not None
                                             else item[2]):
            return item[1]
        return None

    @staticmethod
    def _cache_set(cache, key, value, ttl=TTL_CAT):
        if len(cache) > 512:
            cache.clear()
        cache[key] = (time.time(), value, ttl)