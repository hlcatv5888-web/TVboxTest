# -*- coding: utf-8 -*-
# 观影4k.py TV box Python 爬虫

import base64
import hashlib
import hmac
import json
import re
import threading
import time
import urllib.parse
import urllib.request

try:
    from base.spider import Spider as BaseSpider
except Exception:
    class BaseSpider(object):
        def init(self, extend=""):
            pass

        def destroy(self):
            pass


HOST = "https://www.4kvm.top"
REFERER = HOST + "/"

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

HEADERS = {
    "User-Agent": UA,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Referer": REFERER,
}

API_HEADERS = dict(HEADERS)
API_HEADERS["Accept"] = "application/json, text/plain, */*"
API_HEADERS["X-Requested-With"] = "XMLHttpRequest"

_SIGN_SECRET = b"nbmovie2024secretkey"
_SIGN_TAIL = b"\x27\x37\x01\x0a\x20\x59\x50\x65"

DEFAULT_QUALITY = "1080"

CLIENT_ONLY_QUALITY = "4K"

CATEGORIES = [
    {"type_id": "1", "type_name": "电影"},
    {"type_id": "2", "type_name": "电视剧"},
    {"type_id": "3", "type_name": "动漫"},
]

FILTER_TYPES = [
    ("", "全部"), ("1", "剧情"), ("2", "悬疑"), ("3", "恐怖"), ("4", "惊悚"),
    ("5", "喜剧"), ("6", "爱情"), ("9", "犯罪"), ("10", "动作"), ("11", "动画"),
    ("12", "奇幻"), ("13", "音乐"), ("14", "科幻"), ("15", "历史"), ("16", "战争"),
    ("18", "冒险"), ("19", "家庭"), ("20", "纪录"), ("23", "西部"), ("24", "电视电影"),
    ("26", "真人秀"), ("27", "古装"), ("28", "传记"), ("29", "同性"), ("30", "运动"),
    ("31", "武侠"), ("32", "歌舞"), ("33", "纪录片"), ("34", "灾难"), ("35", "短片"),
]

FILTER_YEARS = [("", "全部")] + [(str(i), str(i)) for i in range(1, 46)]

FILTER_AREAS = [("", "全部"), ("5", "中国大陆"), ("6", "中国香港"), ("7", "中国台湾"),
                ("9", "美国"), ("11", "韩国"), ("12", "日本"), ("14", "法国"),
                ("16", "英国"), ("17", "泰国"), ("18", "印度"), ("19", "德国")]

MAX_PAGE_GUESS = 300


def _r1(pattern, text, default=""):
    m = re.search(pattern, text, re.S | re.I)
    return m.group(1).strip() if m else default


def _txt(html):
    s = re.sub(r"<script.*?</script>", "", html, flags=re.S | re.I)
    s = re.sub(r"<style.*?</style>", "", s, flags=re.S | re.I)
    s = re.sub(r"<[^>]+>", " ", s)
    s = s.replace("&nbsp;", " ").replace("&amp;", "&")
    s = s.replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"')
    s = s.replace("&#39;", "'").replace("&mdash;", "—")
    return re.sub(r"\s+", " ", s).strip()


def make_s(dataid, vod_id, ts):
    msg = "%s:%s:%s" % (dataid, ts, vod_id)
    return hmac.new(vod_id.encode("utf-8"),
                    msg.encode("utf-8"),
                    hashlib.sha256).hexdigest()[:32]


def make_k(play_key):
    if not play_key or play_key == "0":
        return "0"
    raw = bytes(a ^ b for a, b in zip(play_key.encode("utf-8"), _SIGN_SECRET))
    return base64.b64encode(raw + _SIGN_TAIL).decode("ascii")


def build_play_url(dataid, vod_id, play_key, quality=DEFAULT_QUALITY, ts=None):
    ts = ts or int(time.time() * 1000)
    return "/video/play?p=%s&v=%s&q=%s&s=%s&t=%s&k=%s" % (
        urllib.parse.quote(str(dataid)),
        urllib.parse.quote(str(vod_id)),
        urllib.parse.quote(str(quality)),
        make_s(dataid, vod_id, ts),
        ts,
        urllib.parse.quote(make_k(play_key), safe=""),
    )


class Spider(BaseSpider):

    def __init__(self):
        self._init_done = False
        self._cache = {}
        self._empty_cats = set()
        self._cats_ready = False


    def getName(self):
        return "4K影视"

    def init(self, extend=""):
        self._init_done = True
        try:
            super(Spider, self).init(extend)
        except Exception:
            pass
        return self

    def isVideoFormat(self, url):
        if not url:
            return False
        u = url.lower().split("?")[0]
        return any(u.endswith(x) for x in
                   (".m3u8", ".mp4", ".mkv", ".flv", ".avi", ".ts", ".mov", ".m4v"))

    def manualVideoCheck(self):
        return False

    def destroy(self):
        self._init_done = False

    def localProxy(self, params):
        return None


    def _fetch(self, url, headers=None, binary=False):
        req = urllib.request.Request(url, headers=headers or HEADERS)
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                raw = resp.read()
                if resp.headers.get("Content-Encoding") == "gzip":
                    import gzip
                    raw = gzip.decompress(raw)
                if binary:
                    return raw
                for enc in ("utf-8", "gbk", "latin-1"):
                    try:
                        return raw.decode(enc)
                    except Exception:
                        continue
                return raw.decode("utf-8", "replace")
        except Exception:
            try:
                req2 = urllib.request.Request(url, headers={
                    "User-Agent": UA, "Accept": "*/*"})
                with urllib.request.urlopen(req2, timeout=20) as resp:
                    raw = resp.read()
                    if binary:
                        return raw
                    return raw.decode("utf-8", "replace")
            except Exception:
                return ""

    def _fetch_cached(self, url, ttl=300):
        now = time.time()
        hit = self._cache.get(url)
        if hit and now - hit[0] < ttl:
            return hit[1]
        txt = self._fetch(url)
        if txt:
            if len(self._cache) > 64:
                for k in [k for k, v in self._cache.items()
                          if now - v[0] >= ttl]:
                    self._cache.pop(k, None)
            self._cache[url] = (now, txt)
        return txt

    def _fetch_json(self, url, headers=None):
        txt = self._fetch(url, headers or API_HEADERS)
        if not txt:
            return None
        try:
            return json.loads(txt)
        except Exception:
            return None


    def homeContent(self, filter):
        out = {"class": [], "filters": {}}

        cats = list(CATEGORIES)
        page = ""
        try:
            page = self._fetch_cached(HOST + "/filter", ttl=600)
        except Exception:
            page = ""

        try:
            seen = {c["type_id"] for c in cats}
            for m in re.finditer(
                    r'href="\?classify=(\d+)"[^>]*>\s*([^<]{1,16})\s*<', page):
                tid, name = m.group(1), m.group(2).strip()
                if tid and tid not in seen and name:
                    seen.add(tid)
                    cats.append({"type_id": tid, "type_name": name})
        except Exception:
            pass

        cats = self._probe_categories(cats)
        out["class"] = cats

        all_val = [{"n": "全部", "v": ""}]
        area_val = all_val + [{"n": n, "v": v} for v, n in FILTER_AREAS]
        year_val = all_val + [{"n": n, "v": v} for v, n in FILTER_YEARS]
        type_val = [{"n": n, "v": v} for v, n in FILTER_TYPES]

        for c in cats:
            out["filters"][c["type_id"]] = [
                {"key": "areas", "name": "地区", "value": area_val},
                {"key": "years", "name": "年份", "value": year_val},
                {"key": "types", "name": "类型", "value": type_val},
            ]

        try:
            if page:
                out["list"] = self._parse_list(page)
            else:
                out["list"] = self._parse_list(
                    self._fetch_cached(HOST + "/", ttl=300))
        except Exception:
            out["list"] = []

        return out

    def _probe_categories(self, cats):
        if self._cats_ready:
            return [c for c in cats if c["type_id"] not in self._empty_cats]

        # 并发探测, 避免串行等待站点逐个响应
        results = {}
        threads = []
        for c in cats:
            t = threading.Thread(target=self._probe_one, args=(c, results))
            t.daemon = True
            t.start()
            threads.append(t)
        for t in threads:
            t.join(timeout=30)

        alive = [c for c in cats if results.get(c["type_id"], True)]
        for c in cats:
            if not results.get(c["type_id"], True):
                self._empty_cats.add(c["type_id"])

        self._cats_ready = True
        return alive if alive else list(cats)

    def _probe_one(self, cat, results):
        url = "%s/filter?classify=%s&page=1" % (HOST, cat["type_id"])
        try:
            html = self._fetch_cached(url, ttl=600)
            results[cat["type_id"]] = 'data-vod-id="' in html
        except Exception:
            results[cat["type_id"]] = True


    def categoryContent(self, tid, pg, filter, extend):
        result = {"list": [], "page": int(pg), "pagecount": 1,
                  "limit": 24, "total": 24}
        try:
            page = int(pg)
        except Exception:
            page = 1

        extend = extend or {}

        if tid in ("home", "", None):
            params = {"page": page}
        else:
            params = {"classify": tid, "page": page}
            for key, alias in (("areas", "area"), ("years", "year"),
                               ("types", "type")):
                v = extend.get(key) or extend.get(alias)
                if v:
                    params[key] = v
        url = "%s/filter?%s" % (HOST, urllib.parse.urlencode(params))

        html = self._fetch_cached(url, ttl=180)
        items = self._parse_list(html)

        result["list"] = items
        result["limit"] = len(items)

        total, pagecount = self._parse_pager(html)

        if tid not in ("home", "", None) and not items and not pagecount:
            if "暂无" in html or not html:
                self._empty_cats.add(tid)

        if pagecount:
            result["pagecount"] = pagecount
            result["total"] = total or pagecount * 24
        elif items and len(items) >= 20 and page < MAX_PAGE_GUESS:
            result["pagecount"] = page + 1
            result["total"] = 24 * (page + 1)
        else:
            result["pagecount"] = page
            result["total"] = len(items)

        return result

    @staticmethod
    def _parse_pager(html):
        if not html:
            return 0, 0
        m = re.search(r'共\s*(\d+)\s*页\s*[，,]\s*共\s*(\d+)\s*个结果', html)
        if m:
            return int(m.group(2)), int(m.group(1))
        m = re.search(r'/\s*共\s*(\d+)\s*页', html)
        if m:
            return 0, int(m.group(1))
        return 0, 0


    def searchContent(self, key, quick, pg=1):
        result = {"list": [], "page": 1}
        try:
            params = {"q": key}
            if pg and int(pg) > 1:
                params["page"] = int(pg)
            url = "%s/search?%s" % (HOST, urllib.parse.urlencode(params))
            html = self._fetch_cached(url, ttl=300)
            if html:
                items = self._parse_list(html, search_mode=True)
                result["list"] = items
                result["page"] = int(pg) if pg else 1
        except Exception:
            pass
        return result


    def detailContent(self, array):
        if not array:
            return {"list": []}
        vod_id = array[0] if isinstance(array, (list, tuple)) else array
        vod_id = str(vod_id).strip()
        if vod_id.startswith("http"):
            vod_id = vod_id.rstrip("/").split("/")[-1].split("?")[0]

        result = {"list": []}
        try:
            html = self._fetch_cached("%s/play/%s" % (HOST, vod_id), ttl=300)
            if not html:
                return result

            name = (_r1(r'<meta property="og:title" content="([^"]*)"', html)
                    or _r1(r'<h1[^>]*>\s*([^<]{1,80})\s*</h1>', html)
                    or vod_id)
            name = re.sub(r"\s*[-–]\s*第\d+集.*$", "", name).strip()

            pic = _r1(r'<meta property="og:image" content="([^"]*)"', html)
            if not pic:
                pic = _r1(r'<img[^>]+data-src="([^"]+)"', html) or \
                      _r1(r'<img[^>]+src="(https?://[^"]+)"', html)

            desc = (_r1(r'<meta property="og:description" content="([^"]*)"', html)
                    or _r1(r'<meta name="description" content="([^"]*)"', html))
            if not desc:
                desc = _txt(_r1(r'<div[^>]*class="[^"]*intro[^"]*"[^>]*>(.*?)</div>',
                                html, ""))

            year = _r1(r'(\d{4})\s*年', html)
            if not year:
                year = _r1(r'"datePublished"\s*:\s*"(\d{4})', html)
            if not year:
                m = re.search(r'(20\d{2}|19\d{2})', _r1(
                    r'<meta name="keywords" content="([^"]*)"', html, ""))
                year = m.group(1) if m else ""

            score = _r1(r'(\d{1,2}\.\d)\s*分', html)
            if not score:
                score = _r1(r'"ratingValue"\s*:\s*"?(\d{1,2}\.?\d?)', html)

            remarks = _r1(r'第\s*(\d+)\s*集', html)
            if remarks:
                remarks = "更新至第%s集" % remarks

            froms, urls = self._parse_episodes(html, vod_id)

            result["list"].append({
                "vod_id": vod_id,
                "vod_name": name,
                "vod_pic": pic,
                "vod_year": str(year),
                "vod_area": "",
                "vod_remarks": remarks or "4K",
                "vod_content": desc or name,
                "vod_actor": "",
                "vod_director": "",
                "vod_score": str(score) if score else "",
                "type_name": "",
                "vod_play_from": "$$$".join(froms) if froms else "4K影视",
                "vod_play_url": "$$$".join(urls) if urls else "",
            })
        except Exception:
            pass

        return result


    def playerContent(self, flag, id, vipFlags):
        out = {"parse": 0, "playUrl": "", "url": "", "header": "",
               "flag": flag, "format": "application/vnd.apple.mpegurl"}

        vod_id, dataid = self._split_id(id)
        if not dataid:
            return self._play_error(out, "剧集 ID 解析失败")

        is_vip = False
        last_code = 0

        try:
            html = self._fetch("%s/play/%s" % (HOST, vod_id))
            play_key = self._extract_play_key(html) if html else ""
            base_ts = self._extract_server_ts(html) if html else 0
            is_vip = self._is_vip_page(html) if html else False

            ts = base_ts if base_ts > 0 else int(time.time() * 1000)

            for q in (DEFAULT_QUALITY, "1"):
                data, ts = self._try_quality(dataid, vod_id, play_key, q, ts)
                if not data:
                    continue

                code = data.get("code") or 0
                last_code = code
                if code == 401:
                    is_vip = True
                    break
                if code == 403:
                    continue
                if code != 200:
                    continue

                url = self._pick_url(
                    (data.get("data") or {}).get("quality_urls") or [], q)
                if url:
                    out["url"] = url
                    out["playUrl"] = ""
                    out["parse"] = 0
                    out["header"] = self._play_header()
                    return out
        except Exception:
            pass

        if is_vip:
            return self._play_error(out, "该片为 VIP 专享，需登录官网开通会员后播放")
        if last_code == 403:
            return self._play_error(out, "该画质仅官方客户端可用")
        return self._play_error(out, "该片暂时无可用播放地址")

    @staticmethod
    def _play_header():
        return json.dumps({"User-Agent": UA}, ensure_ascii=False)

    @staticmethod
    def _play_error(out, message):
        out["url"] = ""
        out["playUrl"] = ""
        out["parse"] = 0
        out["header"] = json.dumps({"_4kvm_error": message}, ensure_ascii=False)
        return out

    def _try_quality(self, dataid, vod_id, play_key, quality, ts):
        data = self._fetch_json(HOST + build_play_url(dataid, vod_id,
                                                      play_key, quality, ts))
        if data:
            return data, ts
        ts = int(time.time() * 1000)
        return (self._fetch_json(HOST + build_play_url(dataid, vod_id,
                                                       play_key, quality, ts)),
                ts)

    @staticmethod
    def _pick_url(quality_urls, want):
        real = ""
        backup = ""
        for item in quality_urls:
            u = (item.get("url") or "").strip()
            if not u or u in ("0", "1"):
                continue
            if item.get("locked") or item.get("isvip"):
                continue
            if not backup:
                backup = u
            if str(item.get("bitrate")) == str(want):
                real = u
                break
        return real or backup

    @staticmethod
    def _is_vip_page(html):
        if not html:
            return False
        return bool(re.search(r'ri-vip-crown|>\s*VIP\s*<|VIP专享|会员专享', html))


    @staticmethod
    def _split_id(id_str):
        s = str(id_str or "").strip()
        parts = [p for p in re.split(r"[|,\$]", s) if p]
        vod_id, dataid = "", ""
        for p in parts:
            if re.fullmatch(r"\d+", p):
                if not dataid:
                    dataid = p
            else:
                if not vod_id:
                    vod_id = p
        if not vod_id and len(parts) == 1:
            vod_id = parts[0]
        if not vod_id:
            vod_id = dataid
        return vod_id, dataid

    @staticmethod
    def _extract_play_key(html):
        for pat in (r"userlink\s*:\s*'([^']+)'",
                    r'userlink\s*:\s*"([^"]+)"',
                    r"myuserlink\s*=\s*'([^']+)'",
                    r'myuserlink\s*=\s*"([^"]+)"'):
            m = re.search(pat, html)
            if m:
                return m.group(1).strip()
        return ""

    @staticmethod
    def _extract_server_ts(html):
        for pat in (r'id="nb-st"[^>]*content="(\d+)"',
                    r'content="(\d+)"[^>]*id="nb-st"'):
            m = re.search(pat, html)
            if m:
                try:
                    return int(m.group(1))
                except Exception:
                    pass
        return 0

    def _parse_episodes(self, html, vod_id):
        froms, urls = [], []

        lines = []
        mgr = re.search(r"episodeManager\(\s*\d+\s*,\s*\d+\s*,\s*\[(.*?)\]\s*\)",
                        html, re.S)
        if mgr:
            for lm in re.finditer(
                    r"lineName\s*:\s*['\"]([^'\"]*)['\"]\s*,\s*"
                    r"episodeCount\s*:\s*(\d+)", mgr.group(1)):
                name = _txt(lm.group(1)).strip() or "线路"
                try:
                    cnt = int(lm.group(2))
                except Exception:
                    cnt = 0
                lines.append({"name": name, "count": cnt})

        eps = re.findall(
            r'data-line="(\d+)"[^>]*data-episode="(\d+)"[^>]*dataid="(\d+)"'
            r'[^>]*>\s*([^<]{0,24})\s*<',
            html, re.S)
        if not eps:
            eps = re.findall(
                r'dataid="(\d+)"[^>]*data-line="(\d+)"[^>]*data-episode="(\d+)"',
                html, re.S)

        if eps:
            groups = {}
            for row in eps:
                line, ep, dataid = int(row[0]), int(row[1]), row[2]
                label = (row[3] if len(row) > 3 else "").strip()
                groups.setdefault(line, []).append((ep, dataid, label))

            for idx, line in enumerate(sorted(groups)):
                items = sorted(groups[line], key=lambda x: x[0])
                names = []
                for ep, dataid, label in items:
                    nm = re.sub(r"\s+", "", label) or ("第%d集" % ep)
                    names.append("%s$%s|%s" % (nm, vod_id, dataid))
                if lines and idx < len(lines) and lines[idx]["name"]:
                    froms.append(lines[idx]["name"])
                else:
                    froms.append("线路%d" % line)
                urls.append("#".join(names))

        else:
            ids = re.findall(r'dataid="(\d+)"', html)
            seen, names = set(), []
            for i, did in enumerate(ids, 1):
                if did in seen:
                    continue
                seen.add(did)
                names.append("第%d集$%s|%s" % (i, vod_id, did))
            if names:
                froms.append("4K影视")
                urls.append("#".join(names))

        return froms, urls

    _REMARK_RE = re.compile(
        r'>\s*(全\d+集|更新至第?\d+集?|更新\d+集|完结|已完结|HD高清|HD|BD|'
        r'抢先版|预告|第\d+集|共\d+集)\s*<')
    _SCORE_RE = re.compile(r'>\s*(\d{1,2}\.\d)\s*<')
    _VIP_RE = re.compile(r'ri-vip-crown|>\s*VIP\s*<')

    def _parse_list(self, html, search_mode=False):
        if not html:
            return []

        items = self._parse_by_vodid(html)
        if items:
            return items

        return self._parse_by_link(html)

    def _parse_by_vodid(self, html):
        items, seen = [], set()
        chunks = re.split(r'(?=data-vod-id=")', html)
        for chunk in chunks:
            m = re.match(r'data-vod-id="([^"]+)"', chunk)
            if not m:
                continue
            vid = m.group(1).strip()
            if not vid or vid in seen:
                continue
            chunk = chunk[:4000]

            name = _r1(r'alt="([^"]{1,80})"', chunk)
            if not name:
                name = _r1(r'<h3[^>]*>\s*([^<]{1,80})\s*</h3>', chunk)
            name = re.sub(r"\s+", " ", _txt(name)).strip()
            if not name:
                continue
            seen.add(vid)

            pic = _r1(r'data-src="([^"]+)"', chunk) or \
                  _r1(r'src="(https?://[^"]+\.(?:jpg|jpeg|png|webp)[^"]*)"', chunk)
            pic = pic.replace("&amp;", "&")

            rem_m = self._REMARK_RE.search(chunk)
            remarks = rem_m.group(1) if rem_m else ""
            sc_m = self._SCORE_RE.search(chunk)
            score = sc_m.group(1) if sc_m else ""
            year = _r1(r'(19\d{2}|20\d{2})', remarks)

            if self._VIP_RE.search(chunk):
                remarks = ("VIP " + remarks).strip() if remarks else "VIP专享"

            items.append({
                "vod_id": vid,
                "vod_name": name,
                "vod_pic": pic,
                "vod_remarks": remarks or (score and ("评分 " + score)) or "",
                "vod_year": year,
                "vod_score": score,
                "vod_content": "",
                "vod_play_from": "4K影视",
                "vod_play_url": "",
            })
        return items

    def _parse_by_link(self, html):
        items, seen = [], set()
        for m in re.finditer(r'<a[^>]+href="/play/([a-z0-9]+)"[^>]*>(.*?)(?=<a\s|</div>\s*</div>|$)',
                             html, re.S):
            vid, inner = m.group(1), m.group(2)
            if vid in seen:
                continue
            name = (_r1(r'<h3[^>]*>\s*([^<]{1,80})\s*</h3>', inner)
                    or _r1(r'alt="([^"]{1,80})"', inner))
            name = re.sub(r"\s+", " ", _txt(name)).strip()
            if not name or len(name) > 80:
                continue
            seen.add(vid)
            items.append({
                "vod_id": vid,
                "vod_name": name,
                "vod_pic": _r1(r'data-src="([^"]+)"', inner)
                           or _r1(r'src="(https?://[^"]+)"', inner),
                "vod_remarks": "",
                "vod_year": "",
                "vod_score": "",
                "vod_content": "",
                "vod_play_from": "4K影视",
                "vod_play_url": "",
            })
        return items

    def _parse_search_fallback(self, html):
        return self._parse_by_link(html)


def _selftest():
    sp = Spider()
    sp.init("")

    print("=" * 68)
    print("4K影视 Spider 自测")
    print("=" * 68)

    print("\n[1] 签名算法")
    p, v, q = "38761", "ch4k8uf4p", "1"
    ts = 1789558097646
    s = make_s(p, v, ts)
    print("    s =", s)
    print("    期望 0a6f6eb9dc62bd33a5c080d34ad51fe3 ->",
          "OK" if s == "0a6f6eb9dc62bd33a5c080d34ad51fe3" else "FAIL")
    k = make_k("X1VVVkNQXAcCBA4FCgc7IUleV05W")
    print("    k =", k)
    print("    期望 NlM7OSACK2Noc1cwJyJGIzcMBk4nNwEKIFlQZQ== ->",
          "OK" if k == "NlM7OSACK2Noc1cwJyJGIzcMBk4nNwEKIFlQZQ==" else "FAIL")

    print("\n[2] 首页分类")
    hc = sp.homeContent(False)
    print("    分类数:", len(hc["class"]))
    for c in hc["class"]:
        print("      - %s (type_id=%s)" % (c["type_name"], c["type_id"]))
    print("    首页条目:", len(hc["list"]))
    for it in hc["list"][:3]:
        print("      -", it["vod_name"], "|", it["vod_remarks"])

    print("\n[3] 各分类内容区分")
    sigs = {}
    for c in hc["class"]:
        cc = sp.categoryContent(c["type_id"], 1, False, {})
        ids = tuple(x["vod_id"] for x in cc["list"][:4])
        sigs[c["type_name"]] = ids
        first = cc["list"][0]["vod_name"] if cc["list"] else "(空)"
        print("      %-6s 条目=%-3d 首条=%s" % (c["type_name"], len(cc["list"]), first))
    uniq = set(v for v in sigs.values() if v)
    if len(uniq) == len([v for v in sigs.values() if v]):
        print("    -> 各分类内容互不相同 ✓")
    else:
        print("    -> 存在内容重复的分类")

    print("\n[4] 分类翻页 (电影)")
    for pg in (1, 2, 3):
        cc = sp.categoryContent("1", pg, False, {})
        f = cc["list"][0]["vod_name"] if cc["list"] else "(空)"
        print("      page=%d 条目=%-3d 首条=%s" % (pg, len(cc["list"]), f))

    print("\n[5] 搜索 '阿嬷'")
    sc = sp.searchContent("阿嬷", False, 1)
    print("    条目:", len(sc["list"]))
    for it in sc["list"][:3]:
        print("      -", it["vod_name"], "|", it["vod_id"])

    if sc["list"]:
        vid = sc["list"][0]["vod_id"]
        print("\n[6] 详情:", vid)
        dc = sp.detailContent([vid])
        if dc["list"]:
            d = dc["list"][0]
            print("    名称:", d["vod_name"])
            print("    线路:", d["vod_play_from"])
            eps = d["vod_play_url"].split("$$$")[0].split("#")
            print("    剧集数:", len(eps))
            print("    首集:", eps[0] if eps else "-")

            if eps:
                print("\n[7] 播放解析")
                pc = sp.playerContent("线路1", eps[0].split("$")[-1], [])
                print("    url:", pc.get("url") or "(无)")
                print("    parse:", pc.get("parse"))
                print("    format:", pc.get("format"))

    print("\n" + "=" * 68)


if __name__ == "__main__":
    _selftest()
