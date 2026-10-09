# -*- coding: utf-8 -*-
"""
TVBox 爬虫 —— 皮狗DJ站
分页: /video/lists/{tid}/{page}.html  (data-uri 模板)
封面: localProxy + Referer=图片自身URL
"""

import sys
import re
import json
import time
from urllib.parse import quote, urljoin, unquote

import requests

sys.path.append('..')
try:
    from base.spider import Spider as BaseSpider
except Exception:
    class BaseSpider(object):
        pass


class Spider(BaseSpider):

    def getName(self):
        return "皮狗DJ"

    def init(self, extend=""):
        self.host = "https://www.pgdjz.com"
        self.ua = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
        self.sess = requests.Session()
        self.sess.headers.update({
            "User-Agent": self.ua,
            "Referer": self.host + "/",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9",
        })
        self.pic_headers = {
            "User-Agent": self.ua,
            "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Sec-Fetch-Dest": "image",
            "Sec-Fetch-Mode": "no-cors",
            "Sec-Fetch-Site": "cross-site",
        }
        self._proxy_cache = {}
        self._proxy_cache_ttl = 3600

        self.class_list = [
            {"type_id": "12",  "type_name": "超清MV"},
            {"type_id": "123", "type_name": "车载MV"},
            {"type_id": "112", "type_name": "跳舞MV"},
            {"type_id": "158", "type_name": "国内夜店"},
            {"type_id": "90",  "type_name": "派对MV"},
            {"type_id": "125", "type_name": "发烧MV"},
            {"type_id": "21",  "type_name": "国外夜店"},
            {"type_id": "20",  "type_name": "抒情MV"},
        ]

    # ================= 工具方法 =================
    def _get(self, url, timeout=15):
        try:
            r = self.sess.get(url, timeout=timeout)
            r.encoding = "utf-8"
            return r.text
        except Exception:
            return ""

    def _fix(self, url):
        if not url:
            return ""
        url = url.strip().strip('\'" \t\r\n')
        if not url:
            return ""
        url = url.replace("\\/", "/")
        if url.startswith("data:"):
            return url
        if url.startswith("//"):
            url = "https:" + url
        elif url.startswith("/"):
            url = self.host + url
        elif not url.startswith("http"):
            url = urljoin(self.host + "/", url)
        if url.startswith("http://"):
            url = "https://" + url[7:]
        if "://" in url:
            proto, rest = url.split("://", 1)
            rest = re.sub(r'/{2,}', '/', rest)
            url = proto + "://" + rest
        return url

    def _pic_url(self, url):
        """图片地址：★保留原始双斜杠★"""
        if not url:
            return ""
        url = url.strip().strip('\'" \t\r\n')
        if not url:
            return ""
        if url.startswith("//"):
            return "https:" + url
        if url.startswith("/"):
            return self.host + url
        if not url.startswith("http"):
            url = urljoin(self.host + "/", url)
        return url

    def _abs(self, href):
        href = (href or "").strip()
        if href.startswith("//"):
            return "https:" + href
        if href.startswith("http"):
            return href
        return urljoin(self.host + "/", href.lstrip("/"))

    def _clean(self, s):
        s = re.sub(r"<[^>]+>", "", s or "")
        s = (s.replace("&nbsp;", " ").replace("&amp;", "&")
              .replace("&quot;", '"').replace("&#39;", "'"))
        return s.strip()

    def _is_valid_pic(self, url):
        if not url:
            return False
        url = url.strip()
        if not url or url in ("#", "javascript:;", "about:blank"):
            return False
        if url.startswith("data:"):
            return True
        if "." not in url:
            return False
        low = url.lower()
        if any(k in low for k in ("loading.gif", "blank.gif", "placeholder")):
            if not any(d in low for d in ("pgdjz", "tp.", "upload")):
                return False
        return True

    def _extract_pic_from_tag(self, tag_html):
        if not tag_html:
            return ""
        for attr in ("data-original", "data-src", "data-echo",
                     "data-lazy-src", "data-lazyload", "data-url",
                     "data-pic", "data-img", "data-thumb"):
            m = re.search(r'%s\s*=\s*["\']([^"\']+)["\']' % attr, tag_html, re.I)
            if m and self._is_valid_pic(m.group(1)):
                return m.group(1).strip()
        m = re.search(r'\bsrc\s*=\s*["\']([^"\']+)["\']', tag_html, re.I)
        if m and self._is_valid_pic(m.group(1)):
            return m.group(1).strip()
        return ""

    def _find_img_in_block(self, block):
        if not block:
            return ""
        idx = 0
        while True:
            pos = block.find("<img", idx)
            if pos == -1:
                break
            i = pos + 4
            in_quote = None
            while i < len(block):
                ch = block[i]
                if in_quote:
                    if ch == in_quote:
                        in_quote = None
                else:
                    if ch in ('"', "'"):
                        in_quote = ch
                    elif ch == ">":
                        break
                i += 1
            tag = block[pos:i + 1]
            pic = self._extract_pic_from_tag(tag)
            if pic:
                return pic
            idx = i + 1
        return ""

    # ================= localProxy 核心 =================
    def _build_proxy_url(self, pic_url):
        if not pic_url or pic_url.startswith("data:"):
            return pic_url
        return "proxy://do=py&type=image&url=%s" % quote(pic_url, safe="")

    def _download_image(self, pic_url):
        """带 Referer=图片自身URL 下载图片"""
        if not pic_url:
            return None, None

        now = time.time()
        cached = self._proxy_cache.get(pic_url)
        if cached and now - cached[0] < self._proxy_cache_ttl:
            return cached[1], cached[2]

        # ★ 图片自身URL放第一位 ★
        referer_candidates = [
            pic_url,
            self.host + "/",
            self.host,
            "https://www.pgdjz.com/",
        ]

        for ref in referer_candidates:
            try:
                headers = dict(self.pic_headers)
                headers["Referer"] = ref
                r = self.sess.get(pic_url, headers=headers, timeout=10,
                                  allow_redirects=True)
                if r.status_code != 200 or not r.content or len(r.content) <= 200:
                    continue
                magic = r.content[:8]
                is_img = (
                    magic[:3] == b'\xff\xd8\xff'
                    or magic[:8] == b'\x89PNG\r\n\x1a\n'
                    or magic[:3] == b'GIF'
                    or magic[:4] == b'RIFF'
                )
                if not is_img:
                    continue
                ct = r.headers.get("Content-Type", "")
                if "image" not in ct:
                    if magic[:8] == b'\x89PNG\r\n\x1a\n':
                        ct = "image/png"
                    elif magic[:3] == b'GIF':
                        ct = "image/gif"
                    elif magic[:4] == b'RIFF':
                        ct = "image/webp"
                    else:
                        ct = "image/jpeg"
                self._proxy_cache[pic_url] = (now, r.content, ct)
                return r.content, ct
            except Exception:
                continue
        return None, None

    def localProxy(self, params):
        try:
            if isinstance(params, str):
                params = self._parse_query(params)
            elif not isinstance(params, dict):
                params = {}

            ptype = params.get("type", "")
            url = params.get("url", "")
            if url:
                url = unquote(url)

            if ptype == "image" and url:
                content, ct = self._download_image(url)
                if content:
                    return [
                        200, ct or "image/jpeg", content,
                        {"Cache-Control": "public, max-age=3600"},
                    ]
                return [404, "text/plain", b"image not found", {}]
            return [404, "text/plain", b"unsupported", {}]
        except Exception:
            return [500, "text/plain", b"error", {}]

    def _parse_query(self, qs):
        result = {}
        if not qs:
            return result
        qs = qs.lstrip("?")
        for pair in qs.split("&"):
            if "=" in pair:
                k, v = pair.split("=", 1)
                result[k] = unquote(v)
            else:
                result[pair] = ""
        return result

    def _extract_vid(self, html_or_url):
        m = re.search(r'id="mse"[^>]*data-id="(\d+)"', html_or_url or "")
        if m:
            return m.group(1)
        m = re.search(r'data-id="(\d+)"', html_or_url or "")
        if m:
            return m.group(1)
        m = re.search(r'/(\d+)\.html', html_or_url or "")
        if m:
            return m.group(1)
        return ""

    # ================= 列表解析 =================
    def _parse_list(self, html):
        result, seen = [], set()
        if not html:
            return result

        for m in re.finditer(r'<li[^>]*>(.*?)</li>', html, re.S):
            block = m.group(1)
            # 只接受含 imgbox 的 li（主列表特征），避免混入右侧推荐
            if 'imgbox' not in block:
                continue
            a_m = re.search(r'<a[^>]+href\s*=\s*["\']([^"\']+)["\']', block, re.I)
            if not a_m:
                continue
            href = a_m.group(1)
            url = self._abs(href)
            if not re.search(r'/(dance|video)/\d+\.html', url):
                continue
            if url in seen:
                continue
            seen.add(url)

            # 标题优先从 class="name" 的 a 标签抓
            title = ""
            nm = re.search(r'<a[^>]*class="[^"]*name[^"]*"[^>]*>(.*?)</a>', block, re.S)
            if nm:
                title = self._clean(nm.group(1))
            if not title:
                tm = re.search(r'title\s*=\s*["\']([^"\']*)["\']', block, re.I)
                if tm:
                    title = self._clean(tm.group(1))
            if not title:
                continue

            # 封面：localProxy
            pic = ""
            raw_pic = self._find_img_in_block(block)
            if raw_pic:
                fixed = self._pic_url(raw_pic)
                pic = self._build_proxy_url(fixed)

            result.append({
                "vod_id": url,
                "vod_name": title,
                "vod_pic": pic,
                "vod_remarks": "",
            })
        return result

    def _parse_page(self, html):
        if not html:
            return []
        # 优先：主内容区 zyvodlist（用 btnttbox 作为结束锚点）
        m = re.search(
            r'<div[^>]*class="[^"]*zyvodlist[^"]*"[^>]*>(.*?)<div[^>]*class="[^"]*btnttbox',
            html, re.S)
        if m:
            v = self._parse_list(m.group(1))
            if v:
                return v
        # 其次：vodlist
        blocks = re.findall(r'<ul[^>]*class="[^"]*vodlist[^"]*"[^>]*>(.*?)</ul>',
                            html, re.S)
        if blocks:
            v = self._parse_list("".join(blocks))
            if v:
                return v
        return self._parse_list(html)

    # ================= 分页信息提取 =================
    def _parse_pageinfo(self, html, pg):
        """
        从 #pages div 中提取分页信息：
            data-uri="/video/lists/12/[page].html"
            data-nums="8505"    总条数
            data-size="7"       每页条数
        """
        total = 0
        size = 0
        pagecount = pg  # 默认无下一页

        m = re.search(r'data-nums="(\d+)"', html)
        if m:
            total = int(m.group(1))
        m = re.search(r'data-size="(\d+)"', html)
        if m:
            size = int(m.group(1))

        if total > 0 and size > 0:
            pagecount = max(1, (total + size - 1) // size)
        elif total > 0:
            # size 缺失时按每页 20 估算
            pagecount = max(1, (total + 19) // 20)

        return total, pagecount

    # ================= 播放地址提取 =================
    def _scan_media_urls(self, text):
        if not text:
            return []
        out = []
        t = text.replace("\\/", "/")

        for pat in (
            r'<source[^>]+src=["\']([^"\']+)["\']',
            r'<video[^>]+src=["\']([^"\']+)["\']',
            r'<a[^>]+href=["\']([^"\']+\.(?:mp4|m3u8|flv|mkv))["\']',
        ):
            out.extend(re.findall(pat, t, re.I))

        for pat in (
            r'["\']?url["\']?\s*[:=]\s*["\']([^"\']+)["\']',
            r'["\']?videoUrl["\']?\s*[:=]\s*["\']([^"\']+)["\']',
            r'["\']?playUrl["\']?\s*[:=]\s*["\']([^"\']+)["\']',
            r'["\']?src["\']?\s*[:=]\s*["\']([^"\']+)["\']',
        ):
            for u in re.findall(pat, t, re.I):
                if re.search(r'\.(m3u8|mp4|flv|mkv|ts)(\?|$)', u, re.I):
                    out.append(u)

        out.extend(re.findall(
            r'https?://[^\s"\'<>\\]+?\.(?:m3u8|mp4|flv|mkv)(?:\?[^\s"\'<>\\]*)?',
            t, re.I))

        cleaned = []
        for u in out:
            u = self._fix(u.strip())
            if not re.search(r'\.(m3u8|mp4|flv|mkv|ts)(\?|$)', u, re.I):
                continue
            if u not in cleaned:
                cleaned.append(u)
        return cleaned

    def _fetch_real_url(self, vid, detail_html):
        u = self._scan_media_urls(detail_html)
        if u:
            return u
        if not vid:
            return []
        for path in ("/down/%s.html" % vid,
                     "/dance/down/%s.html" % vid,
                     "/video/down/%s.html" % vid):
            h = self._get(self.host + path)
            u = self._scan_media_urls(h)
            if u:
                return u
        for path in ("/dance/play/%s.html" % vid,
                     "/video/play/%s.html" % vid,
                     "/index.php?m=video&c=api&a=play&id=%s" % vid,
                     "/index.php?m=video&c=api&a=geturl&id=%s" % vid):
            h = self._get(self.host + path)
            u = self._scan_media_urls(h)
            if u:
                return u
        return []

    # ================= TVBox 接口 =================
    def homeContent(self, filter):
        return {"class": self.class_list, "filters": {}}

    def homeVideoContent(self):
        html = self._get(self.host + "/video.html")
        return {"list": self._parse_page(html)[:30]}

    def categoryContent(self, tid, pg, filter, extend):
        """
        ★ 分页 URL 修正：/video/lists/{tid}/{pg}.html
        """
        try:
            pg = int(pg)
        except Exception:
            pg = 1

        if pg <= 1:
            url = "%s/video/lists/%s.html" % (self.host, tid)
        else:
            url = "%s/video/lists/%s/%d.html" % (self.host, tid, pg)

        html = self._get(url)
        vlist = self._parse_page(html)

        # ★ 用真实总页数，让 TVBox 能一直翻 ★
        total, pagecount = self._parse_pageinfo(html, pg)
        if not vlist:
            pagecount = pg

        return {
            "list": vlist,
            "page": pg,
            "pagecount": pagecount,
            "limit": len(vlist) or 20,
            "total": total or 999999,
        }

    def detailContent(self, ids):
        url = self._abs(ids[0])
        html = self._get(url)

        vod = {
            "vod_id": url, "vod_name": "", "vod_pic": "", "vod_year": "",
            "vod_area": "", "vod_remarks": "", "vod_actor": "", "vod_director": "",
            "vod_content": "", "vod_play_from": "皮狗DJ", "vod_play_url": "",
        }
        if not html:
            vod["vod_name"] = url.split("/")[-1]
            return {"list": [vod]}

        m = re.search(r'<h1[^>]*>(.*?)</h1>', html, re.S)
        if m:
            t = self._clean(m.group(1))
            t = re.sub(r'(超清|高清|标清|蓝光)\s*$', '', t).strip()
            vod["vod_name"] = t
        if not vod["vod_name"]:
            m = re.search(r'<title>(.*?)</title>', html, re.S)
            if m:
                vod["vod_name"] = self._clean(m.group(1)).split("_")[0].split("-")[0].strip()

        # 封面
        pic = ""
        m = re.search(
            r'<div[^>]*class="[^"]*vodinfo[^"]*"[^>]*>(.*?)<div[^>]*class="[^"]*info',
            html, re.S | re.I)
        if m:
            pic = self._find_img_in_block(m.group(1))
        if not pic:
            m = re.search(
                r'<meta[^>]+property\s*=\s*["\']og:image["\'][^>]+content\s*=\s*["\']([^"\']+)["\']',
                html, re.I)
            if m:
                pic = m.group(1)
        if not pic:
            m = re.search(
                r'<img[^>]*?(?:data-original|data-src|src)\s*=\s*["\']'
                r'(https?://tp\.pgdjz\.fun/[^"\']+?\.(?:jpg|jpeg|png|webp))["\']',
                html, re.I)
            if m:
                pic = m.group(1)

        fixed_pic = self._pic_url(pic) if pic else ""
        vod["vod_pic"] = self._build_proxy_url(fixed_pic) if fixed_pic else ""

        m = re.search(
            r'<meta[^>]+name\s*=\s*["\']description["\'][^>]+content\s*=\s*["\']([^"\']*)["\']',
            html, re.S | re.I)
        if m:
            vod["vod_content"] = self._clean(m.group(1))

        vid = self._extract_vid(html) or self._extract_vid(url)
        real_urls = self._fetch_real_url(vid, html)

        if real_urls:
            if len(real_urls) == 1:
                vod["vod_play_url"] = "正片$" + real_urls[0]
            else:
                vod["vod_play_url"] = "#".join(
                    "线路%d$%s" % (i + 1, u) for i, u in enumerate(real_urls))
        else:
            vod["vod_play_url"] = "正片$" + url

        return {"list": [vod]}

    def searchContent(self, key, quick, pg="1"):
        q = quote(key)
        for u in ("%s/video/search.html?wd=%s" % (self.host, q),
                  "%s/video/search.html?keyword=%s" % (self.host, q),
                  "%s/video/search.html?key=%s" % (self.host, q),
                  "%s/video/search.html?search=%s" % (self.host, q)):
            html = self._get(u)
            if not html:
                continue
            vlist = self._parse_page(html)
            if vlist:
                return {"list": vlist}
        return {"list": []}

    def playerContent(self, flag, id, vipFlags):
        header = json.dumps({
            "User-Agent": self.ua,
            "Referer": self.host + "/",
        }, ensure_ascii=False)
        if re.search(r'\.(m3u8|mp4|flv|mkv|ts)(\?|$)', id or "", re.I):
            return {"parse": 0, "playUrl": "", "url": id, "header": header}
        url = self._abs(id)
        html = self._get(url)
        vid = self._extract_vid(html) or self._extract_vid(url)
        real = self._fetch_real_url(vid, html)
        if real:
            return {"parse": 0, "playUrl": "", "url": real[0], "header": header}
        return {"parse": 1, "playUrl": "", "url": url, "header": header}

    def isVideoFormat(self, url):
        return bool(re.search(r'\.(m3u8|mp4|flv|mkv|ts)(\?|$)', url or "", re.I))

    def manualVideoCheck(self):
        return False

    def destroy(self):
        try:
            self.sess.close()
        except Exception:
            pass