# -*- coding: utf-8 -*-
# code: utf-8
"""
野果短剧 (yeguodj / vkwjlfdf.cc) Python Spider
适用：WebHomeTV / 影视仓 / OK影视 / PickTV（HKL 双壳兼容体系）

站点分析结论：
  - 前端：Nuxt 3 SSR + SPA（路由 /drama/detail/{id}/、/explore/drama/、/drama/video/{id}/ep-{n}/）
  - 后端：同源加密 JSON API，POST form 表单
        接口  /api.php/api/home/homePage | theater/exploreList | theater/videoRank
              /api/playlet/detail | /api/playlet/play | search/result
  - 响应：{"errcode":0,"timestamp":..,"data":"<base64>","sign":".."}
         data = AES-128-CBC(Key, IV) + PKCS7，解密后再内层 {data,status,msg}
  - Key/IV 为前端硬编码公开配置（见下）
  - 播放：m3u8 直链（带 auth_key 签名），无需二次解密

数据协议：多线路 $$$   剧集 #   集名$地址
播放 id 约定："{video_id}|{episode_id}"（playerContent 据此调用 play 接口取 m3u8）
"""

import re
import json
import time
import base64
import requests
from urllib.parse import quote

try:
    requests.packages.urllib3.disable_warnings()
except Exception:
    pass

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

# ===== 站点 / 接口默认值 =====
DEFAULT_HOST = "https://all.vkwjlfdf.cc"
API_PATH = "/api.php"
AES_KEY = b"2acf7e91e9864673"
AES_IV = b"1c29882d3ddfcfd6"

COMMON_PARAMS = {
    "bundleId": "com.pwa.mater",
    "version": "1.3.2",
    "oauth_type": "web",
    "language": "zh",
    "via": "pwa",
    "oauth_id": "7d05538c4b8a5e74e82f93c0dab0163c",
    "token": "",
}

# 展示分类
TYPES = [
    ("explore", "全部短剧"),
    ("rank",    "排行榜"),
    ("new",     "最新"),
    ("hot",     "最热"),
]

# 主题筛选（来自 /api/home/contentOptions -> video_filter）
THEME = [("7", "奇幻"), ("8", "脑洞"), ("9", "权谋"), ("11", "仙侠"),
         ("16", "青春"), ("18", "灵异"), ("46", "剧情"), ("54", "古风")]
SETTING = [("23", "大男主"), ("24", "大女主"), ("26", "重生"), ("27", "穿越"),
           ("28", "系统"), ("29", "神豪"), ("30", "小人物"), ("34", "虐恋"),
           ("52", "超能力"), ("53", "逆袭"), ("56", "魔改")]
BACKGROUND = [("39", "现代"), ("40", "都市"), ("41", "古代"), ("42", "乡村"),
              ("43", "年代"), ("44", "职场"), ("47", "校园")]


# ===================== 纯 Python AES-128-CBC 解密（无依赖兜底） =====================
_SBOX = bytes([
    0x63,0x7c,0x77,0x7b,0xf2,0x6b,0x6f,0xc5,0x30,0x01,0x67,0x2b,0xfe,0xd7,0xab,0x76,
    0xca,0x82,0xc9,0x7d,0xfa,0x59,0x47,0xf0,0xad,0xd4,0xa2,0xaf,0x9c,0xa4,0x72,0xc0,
    0xb7,0xfd,0x93,0x26,0x36,0x3f,0xf7,0xcc,0x34,0xa5,0xe5,0xf1,0x71,0xd8,0x31,0x15,
    0x04,0xc7,0x23,0xc3,0x18,0x96,0x05,0x9a,0x07,0x12,0x80,0xe2,0xeb,0x27,0xb2,0x75,
    0x09,0x83,0x2c,0x1a,0x1b,0x6e,0x5a,0xa0,0x52,0x3b,0xd6,0xb3,0x29,0xe3,0x2f,0x84,
    0x53,0xd1,0x00,0xed,0x20,0xfc,0xb1,0x5b,0x6a,0xcb,0xbe,0x39,0x4a,0x4c,0x58,0xcf,
    0xd0,0xef,0xaa,0xfb,0x43,0x4d,0x33,0x85,0x45,0xf9,0x02,0x7f,0x50,0x3c,0x9f,0xa8,
    0x51,0xa3,0x40,0x8f,0x92,0x9d,0x38,0xf5,0xbc,0xb6,0xda,0x21,0x10,0xff,0xf3,0xd2,
    0xcd,0x0c,0x13,0xec,0x5f,0x97,0x44,0x17,0xc4,0xa7,0x7e,0x3d,0x64,0x5d,0x19,0x73,
    0x60,0x81,0x4f,0xdc,0x22,0x2a,0x90,0x88,0x46,0xee,0xb8,0x14,0xde,0x5e,0x0b,0xdb,
    0xe0,0x32,0x3a,0x0a,0x49,0x06,0x24,0x5c,0xc2,0xd3,0xac,0x62,0x91,0x95,0xe4,0x79,
    0xe7,0xc8,0x37,0x6d,0x8d,0xd5,0x4e,0xa9,0x6c,0x56,0xf4,0xea,0x65,0x7a,0xae,0x08,
    0xba,0x78,0x25,0x2e,0x1c,0xa6,0xb4,0xc6,0xe8,0xdd,0x74,0x1f,0x4b,0xbd,0x8b,0x8a,
    0x70,0x3e,0xb5,0x66,0x48,0x03,0xf6,0x0e,0x61,0x35,0x57,0xb9,0x86,0xc1,0x1d,0x9e,
    0xe1,0xf8,0x98,0x11,0x69,0xd9,0x8e,0x94,0x9b,0x1e,0x87,0xe9,0xce,0x55,0x28,0xdf,
    0x8c,0xa1,0x89,0x0d,0xbf,0xe6,0x42,0x68,0x41,0x99,0x2d,0x0f,0xb0,0x54,0xbb,0x16])
_INV_SBOX = bytes([_SBOX.index(i) for i in range(256)])
_RCON = [0x01,0x02,0x04,0x08,0x10,0x20,0x40,0x80,0x1b,0x36]


def _xtime(a):
    return ((a << 1) ^ 0x1b) & 0xff if a & 0x80 else (a << 1) & 0xff


def _gmul(a, b):
    r = 0
    while b:
        if b & 1:
            r ^= a
        b >>= 1
        a = _xtime(a)
    return r


def _key_expand(key):
    nk = len(key) // 4
    w = [int.from_bytes(key[i:i + 4], "big") for i in range(0, len(key), 4)]
    for i in range(nk, 44):
        t = w[i - 1]
        if i % nk == 0:
            t = ((t << 8) | (t >> 24)) & 0xffffffff
            t = (((_SBOX[(t >> 24) & 0xff] << 24) | (_SBOX[(t >> 16) & 0xff] << 16) |
                  (_SBOX[(t >> 8) & 0xff] << 8) | _SBOX[t & 0xff]) ^ (_RCON[i // nk - 1] << 24))
        w.append(w[i - nk] ^ t)
    return [[(x >> 24) & 0xff, (x >> 16) & 0xff, (x >> 8) & 0xff, x & 0xff] for x in w]


def _dec_block(key, block):
    w = _key_expand(key)
    s = list(block)

    def ark(rnd):
        for c in range(4):
            for r in range(4):
                s[4 * c + r] ^= w[rnd * 4 + c][r]

    def isb():
        for i in range(16):
            s[i] = _INV_SBOX[s[i]]

    def isr():
        t = s[:]
        for r in range(1, 4):
            for c in range(4):
                s[4 * c + r] = t[4 * ((c - r) % 4) + r]

    def imc():
        for c in range(4):
            a0, a1, a2, a3 = s[4 * c], s[4 * c + 1], s[4 * c + 2], s[4 * c + 3]
            s[4 * c] = _gmul(a0, 0x0e) ^ _gmul(a1, 0x0b) ^ _gmul(a2, 0x0d) ^ _gmul(a3, 0x09)
            s[4 * c + 1] = _gmul(a0, 0x09) ^ _gmul(a1, 0x0e) ^ _gmul(a2, 0x0b) ^ _gmul(a3, 0x0d)
            s[4 * c + 2] = _gmul(a0, 0x0d) ^ _gmul(a1, 0x09) ^ _gmul(a2, 0x0e) ^ _gmul(a3, 0x0b)
            s[4 * c + 3] = _gmul(a0, 0x0b) ^ _gmul(a1, 0x0d) ^ _gmul(a2, 0x09) ^ _gmul(a3, 0x0e)

    ark(10)
    for rnd in range(9, 0, -1):
        isr(); isb(); ark(rnd); imc()
    isr(); isb(); ark(0)
    return bytes(s)


def _aes_cbc_decrypt(key, iv, data):
    # 优先 pycryptodome
    try:
        from Crypto.Cipher import AES as _AES
        return _AES.new(key, _AES.MODE_CBC, iv).decrypt(data)
    except Exception:
        pass
    # 纯 Python 兜底
    out = bytearray()
    prev = iv
    for i in range(0, len(data), 16):
        blk = data[i:i + 16]
        out += bytes(a ^ b for a, b in zip(_dec_block(key, blk), prev))
        prev = blk
    return bytes(out)


def _pkcs7_unpad(b):
    if not b:
        return b
    pad = b[-1]
    if 1 <= pad <= 16 and b[-pad:] == bytes([pad]) * pad:
        return b[:-pad]
    return b


# ================================ Spider ================================
class Spider(object):

    def __init__(self):
        self.host = DEFAULT_HOST
        self.api_base = DEFAULT_HOST + API_PATH
        self.timeout = 15
        self.headers = {
            "User-Agent": UA,
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9",
        }
        self.session = None

    # ==================== 壳生命周期 ====================
    def getDependence(self):
        return ["requests"]

    def init(self, extend=""):
        self.session = requests.Session()
        self.session.verify = False
        self.session.headers.update(self.headers)
        try:
            cfg = {}
            if extend:
                cfg = extend if isinstance(extend, dict) else json.loads(extend)
            if isinstance(cfg, dict):
                if cfg.get("host"):
                    self.host = str(cfg["host"]).rstrip("/")
                self.api_base = str(cfg.get("api") or (self.host + API_PATH))
                if cfg.get("ua"):
                    self.headers["User-Agent"] = cfg["ua"]
                    self.session.headers.update({"User-Agent": cfg["ua"]})
                if cfg.get("timeout"):
                    self.timeout = int(cfg["timeout"])
        except Exception:
            pass
        return True

    def destroy(self):
        try:
            if self.session:
                self.session.close()
        except Exception:
            pass
        return True

    def action(self, action):
        return {}

    def manualVideoCheck(self):
        return False

    def getName(self):
        return "野果短剧"

    def isVideoFormat(self, url):
        u = url or ""
        return ".m3u8" in u or ".mp4" in u

    def localProxy(self, param):
        return [200, "text/plain", "", {}]

    # ==================== 基础工具 ====================
    def _page(self, pg):
        try:
            n = int(pg)
        except Exception:
            return 1
        return n if n >= 1 else 1

    @staticmethod
    def _clean(s):
        return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", s or "")).strip()

    def _req_headers(self):
        h = dict(self.headers)
        h["Origin"] = self.host
        h["Referer"] = self.host + "/"
        h["Content-Type"] = "application/x-www-form-urlencoded;charset=UTF-8"
        return h

    def _decrypt_json(self, data_b64):
        try:
            raw = _aes_cbc_decrypt(AES_KEY, AES_IV, base64.b64decode(str(data_b64).replace(" ", "+")))
            return json.loads(_pkcs7_unpad(raw).decode("utf-8", errors="ignore"))
        except Exception:
            return None

    def _api(self, path, data):
        """调用加密 API，返回内层 data 字段（失败返回 None）"""
        if self.session is None:
            self.init("")
        body = dict(COMMON_PARAMS)
        body.update(data or {})
        try:
            r = self.session.post(self.api_base + path, data=body,
                                  headers=self._req_headers(), timeout=self.timeout, verify=False)
            j = r.json()
        except Exception:
            try:
                r = requests.post(self.api_base + path, data=body,
                                  headers=self._req_headers(), timeout=self.timeout, verify=False)
                j = r.json()
            except Exception:
                return None
        if isinstance(j, dict) and isinstance(j.get("data"), str) and j.get("sign") is not None:
            inner = self._decrypt_json(j["data"])
            if isinstance(inner, dict):
                return inner.get("data") if inner.get("status") == 1 else None
            return None
        if isinstance(j, dict) and j.get("status") == 1:
            return j.get("data")
        return None

    # ---- 列表项 -> 标准结构 ----
    @staticmethod
    def _fmt_count(n):
        try:
            n = int(n)
        except Exception:
            return ""
        if n >= 10000:
            return "%.1fW" % (n / 10000.0)
        return str(n)

    def _map_item(self, it):
        vid = it.get("video_id") or it.get("id")
        if not vid:
            return None
        rem = it.get("serialize_status_text") or ""
        cnt = it.get("play_count_text") or self._fmt_count(it.get("play_count"))
        if cnt:
            rem = (rem + " · " + str(cnt)) if rem else str(cnt)
        if not rem and it.get("episodes"):
            rem = "更新至%s集" % it["episodes"]
        return {
            "vod_id": str(vid),
            "vod_name": self._clean(it.get("title") or it.get("name") or ""),
            "vod_pic": it.get("cover") or "",
            "vod_remarks": rem,
        }

    def _map_list(self, lst):
        out = []
        for it in (lst or []):
            m = self._map_item(it)
            if m:
                out.append(m)
        return out

    # ==================== 首页 ====================
    def homeContent(self, filter):
        classes = [{"type_id": t[0], "type_name": t[1]} for t in TYPES]
        common = [
            {"key": "theme", "name": "主题",
             "value": [{"n": "全部", "v": ""}] + [{"n": n, "v": v} for v, n in THEME]},
            {"key": "setting", "name": "设定",
             "value": [{"n": "全部", "v": ""}] + [{"n": n, "v": v} for v, n in SETTING]},
            {"key": "background", "name": "背景",
             "value": [{"n": "全部", "v": ""}] + [{"n": n, "v": v} for v, n in BACKGROUND]},
        ]
        filters = {
            "explore": [dict(x) for x in common],
            "new": [dict(x) for x in common],
            "hot": [dict(x) for x in common],
            "rank": [{"key": "type", "name": "榜单",
                      "value": [{"n": "周榜", "v": "week"}, {"n": "月榜", "v": "month"}]}],
        }
        return {"class": classes, "filters": filters}

    def homeVideoContent(self):
        d = self._api("/api/home/homePage", {})
        videos = []
        if isinstance(d, dict):
            videos += self._map_list(d.get("top_list"))
            mods = d.get("modules")
            if isinstance(mods, dict):
                mods = mods.get("list") or []
            for m in (mods or []):
                if isinstance(m, dict):
                    videos += self._map_list(m.get("items"))
        # 去重
        seen, uniq = set(), []
        for v in videos:
            if v["vod_id"] in seen:
                continue
            seen.add(v["vod_id"])
            uniq.append(v)
        return {"list": uniq[:60]}

    # ==================== 分类 ====================
    def categoryContent(self, tid, pg, filter, extend):
        pg = self._page(pg)
        ext = extend if isinstance(extend, dict) else {}

        if tid == "rank":
            d = self._api("/api/theater/videoRank",
                          {"page": pg, "limit": 30, "type": ext.get("type") or "week"})
        else:
            params = {"page": pg, "limit": 30}
            if tid == "new":
                params["recommend"] = "1"
            elif tid == "hot":
                params["recommend"] = "2"
            for k in ("theme", "setting", "background", "time", "recommend"):
                v = ext.get(k)
                if v not in (None, "", "全部"):
                    params[k] = v
            d = self._api("/api/theater/exploreList", params)

        if not isinstance(d, dict):
            return {"list": [], "page": pg, "pagecount": pg, "limit": 30, "total": 0}
        lst = self._map_list(d.get("list"))
        limit = int(d.get("limit") or 30) or 30
        total = int(d.get("total") or 0)
        pagecount = (total + limit - 1) // limit if total else pg
        return {"list": lst, "page": pg, "pagecount": max(pagecount, pg),
                "limit": limit, "total": total}

    # ==================== 详情 ====================
    def detailContent(self, ids):
        if isinstance(ids, (list, tuple)):
            vid = str(ids[0]) if ids else ""
        else:
            vid = str(ids).split(",")[0]
        vid = re.sub(r"[^0-9]", "", vid)
        if not vid:
            return {"list": []}
        d = self._api("/api/playlet/detail", {"video_id": vid})
        if not isinstance(d, dict) or not d.get("video_id"):
            return {"list": []}

        eps = d.get("episodes") or []
        ep_parts = []
        for e in eps:
            eid = e.get("id")
            sort = e.get("sort")
            if eid is None:
                continue
            name = ("第%s集" % sort) if sort is not None else "正片"
            ep_parts.append("%s$%s|%s" % (name, vid, eid))

        remark = d.get("serialize_status_text") or ""
        if d.get("episode_count"):
            remark = ("%s · 共%s集" % (remark, d["episode_count"])).strip(" ·")

        vod = {
            "vod_id": vid,
            "vod_name": self._clean(d.get("title") or ""),
            "vod_pic": d.get("cover") or "",
            "vod_content": self._clean(d.get("description") or ""),
            "vod_remarks": remark,
            "vod_play_from": "野果短剧",
            "vod_play_url": "#".join(ep_parts),
        }
        return {"list": [vod]}

    # ==================== 搜索 ====================
    def searchContent(self, key, quick, pg=1):
        pg = self._page(pg)
        kw = (key or "").strip()
        params={"keyword": kw, "page": pg, "tab": "video"}
        if not kw:
            return {"list": [], "page": pg, "pagecount": pg, "limit": 10, "total": 0}
        d = self._api("/api/search/result", params)
        if not isinstance(d, dict):
            return {"list": [], "page": pg, "pagecount": pg, "limit": 10, "total": 0}
        lst = self._map_list(d.get("list"))
        total = int(d.get("total") or 0)
        limit = int(d.get("limit") or 10) or 10
        pagecount = (total + limit - 1) // limit if total else pg
        return {"list": lst, "page": pg, "pagecount": max(pagecount, pg), "limit": limit, "total": total}

    # ==================== 播放 ====================
    def _resolve_episode(self, vid, eid):
        """把播放 id 统一解析成 (video_id, episode_id)"""
        if "|" in eid:
            a, b = eid.split("|", 1)
            return re.sub(r"\D", "", a), re.sub(r"\D", "", b)
        # 兜底：可能是播放页 URL /drama/video/{vid}/ep-{n}/ 或纯数字
        m = re.search(r"/drama/video/(\d+)/ep-(\d+)", eid)
        if m:
            v, sort = m.group(1), m.group(2)
            d = self._api("/api/playlet/detail", {"video_id": v})
            for e in (d or {}).get("episodes", []) if isinstance(d, dict) else []:
                if str(e.get("sort")) == str(sort):
                    return v, str(e.get("id"))
            return v, ""
        m2 = re.search(r"/ep-(\d+)", eid)
        if m2 and vid:
            d = self._api("/api/playlet/detail", {"video_id": vid})
            for e in (d or {}).get("episodes", []) if isinstance(d, dict) else []:
                if str(e.get("sort")) == m2.group(1):
                    return vid, str(e.get("id"))
        return vid, re.sub(r"\D", "", eid)

    def playerContent(self, flag, ids, vipFlags):
        pid = ids if isinstance(ids, str) else (ids[0] if ids else "")
        vid = ""
        m = re.search(r"(\d+)\|\d+", pid)
        if m:
            vid = m.group(1)
        vid, eid = self._resolve_episode(vid, pid)
        url = ""
        if vid and eid:
            d = self._api("/api/playlet/play", {"video_id": vid, "episode_id": eid})
            if isinstance(d, dict):
                url = d.get("video_url") or d.get("video_url_h265") or ""
        header = {"User-Agent": UA, "Referer": self.host + "/"}
        return {"parse": 0, "playUrl": "", "url": url, "header": header}
