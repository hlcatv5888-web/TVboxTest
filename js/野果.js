/**
 * 野果短剧 Streama（原生契约）
 * 站点: https://yeguodj.com
 *
 * 按原生契约修订：
 * - 顶层 `var WidgetMetadata` 声明，列表模块显式 `type: "video"`、播放源 `type: "stream"`
 * - 媒体项 / 详情 / 剧集 / 播放源统一使用原生契约字段 `headers`（原 `customHeaders` 非标准）
 * - `loadDetail(link, extraParams)` 接收第二个参数，全局参数 apiBase/coverProxy/coverToken 在详情页生效；空链接抛带上下文短错误（不返回 null）
 * - 【详情页 videoUrl 修复】详情测试要求 videoUrl 非空，loadDetail 预取第一集播放地址填入 videoUrl
 * - `search` 兼容 keyword/query/wd/search 四别名，page 校验
 * - `Widget.http` 统一设置 timeout（毫秒）并按 ok/status 判定失败
 * - 列表 / 搜索路径不缓存（吸取 mav.js 教训：缓存空结果会导致后续无返回数据）
 */
var WidgetMetadata = {
  id: "Streama.yeguodj",
  title: "野果短剧",
  version: "2.0.0",
  detailCacheDuration: 180,
  globalParams: [
    {
      name: "apiBase",
      title: "API 地址",
      type: "input",
      value: "https://www.yeguodj.com/api.php"
    },
    {
      name: "coverProxy",
      title: "封面解密代理",
      type: "input",
      value: "https://huangguo.wulii.de5.net"
    },
    {
      name: "coverToken",
      title: "封面代理 Token",
      type: "input",
      value: "hg8f3a2c91b7e04d6a"
    }
  ],
  modules: [
    { id: "home", title: "首页推荐", type: "video", functionName: "loadHome", cacheDuration: 300, params: [{ name: "page", title: "页码", type: "page", value: "1", startPage: 1 }] },
    { id: "explore", title: "发现", type: "video", functionName: "loadExplore", cacheDuration: 300, params: [{ name: "page", title: "页码", type: "page", value: "1", startPage: 1 }] },
    { id: "rank", title: "排行榜", type: "video", functionName: "loadRank", cacheDuration: 300, params: [{ name: "page", title: "页码", type: "page", value: "1", startPage: 1 }] },
    { id: "dushi", title: "都市", type: "video", functionName: "loadDushi", cacheDuration: 300, params: [{ name: "page", title: "页码", type: "page", value: "1", startPage: 1 }] },
    { id: "xiandai", title: "现代", type: "video", functionName: "loadXiandai", cacheDuration: 300, params: [{ name: "page", title: "页码", type: "page", value: "1", startPage: 1 }] },
    { id: "xiaoyuan", title: "校园", type: "video", functionName: "loadXiaoyuan", cacheDuration: 300, params: [{ name: "page", title: "页码", type: "page", value: "1", startPage: 1 }] },
    { id: "gudai", title: "古代", type: "video", functionName: "loadGudai", cacheDuration: 300, params: [{ name: "page", title: "页码", type: "page", value: "1", startPage: 1 }] },
    { id: "xiangcun", title: "乡村", type: "video", functionName: "loadXiangcun", cacheDuration: 300, params: [{ name: "page", title: "页码", type: "page", value: "1", startPage: 1 }] },
    { id: "zhichang", title: "职场", type: "video", functionName: "loadZhichang", cacheDuration: 300, params: [{ name: "page", title: "页码", type: "page", value: "1", startPage: 1 }] },
    { id: "chongsheng", title: "重生", type: "video", functionName: "loadChongsheng", cacheDuration: 300, params: [{ name: "page", title: "页码", type: "page", value: "1", startPage: 1 }] },
    { id: "chuanyue", title: "穿越", type: "video", functionName: "loadChuanyue", cacheDuration: 300, params: [{ name: "page", title: "页码", type: "page", value: "1", startPage: 1 }] },
    { id: "xitong", title: "系统", type: "video", functionName: "loadXitong", cacheDuration: 300, params: [{ name: "page", title: "页码", type: "page", value: "1", startPage: 1 }] },
    { id: "nixi", title: "逆袭", type: "video", functionName: "loadNixi", cacheDuration: 300, params: [{ name: "page", title: "页码", type: "page", value: "1", startPage: 1 }] },
    { id: "mogai", title: "魔改", type: "video", functionName: "loadMogai", cacheDuration: 300, params: [{ name: "page", title: "页码", type: "page", value: "1", startPage: 1 }] },
    {
      id: "loadResource",
      title: "播放资源",
      functionName: "loadResource",
      type: "stream",
      timeoutSeconds: 20,
      cacheDuration: 0,
      params: []
    }
  ],
  search: {
    title: "搜索",
    functionName: "search",
    params: [
      { name: "keyword", title: "关键词", type: "input" },
      { name: "page", title: "页码", type: "page", value: "1", startPage: 1 }
    ]
  }
};

var API_KEY = "2acf7e91e9864673";
var API_IV = "1c29882d3ddfcfd6";
var MEDIA_KEY = "f5d965df75336270";
var MEDIA_IV = "97b60394abc2fbe1";
var UA =
  "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15";
/* Widget.http 超时（毫秒） */
var HTTP_TIMEOUT = 20000;

function t(v) {
  return String(v == null ? "" : v).trim();
}

/* page 参数校验：非法抛带上下文短错误 */
function normPage(params, fnName) {
  var page = Number((params && params.page) || 1);
  if (!Number.isFinite(page) || page < 1) {
    throw new Error((fnName || "loadList") + ": page 必须是正整数");
  }
  return page;
}

function cfg(params) {
  params = params || {};
  return {
    apiBase: t(params.apiBase || "https://www.yeguodj.com/api.php").replace(
      /\/+$/,
      ""
    ),
    coverProxy: t(params.coverProxy || "https://huangguo.wulii.de5.net").replace(
      /\/+$/,
      ""
    ),
    coverToken: t(params.coverToken || "hg8f3a2c91b7e04d6a")
  };
}

/* 播放请求头：播放器需要 UA/Referer/Origin */
function playHeaders() {
  return {
    "User-Agent": UA,
    Referer: "https://yeguodj.com/",
    Origin: "https://yeguodj.com",
    "X-Forward-Skip-Redirect-Probe": "1"
  };
}

function qs(obj) {
  var parts = [];
  Object.keys(obj || {}).forEach(function (k) {
    if (obj[k] == null || obj[k] === "") return;
    parts.push(encodeURIComponent(k) + "=" + encodeURIComponent(String(obj[k])));
  });
  return parts.length ? "?" + parts.join("&") : "";
}


/** UTF-8 / Base64 helpers (no TextEncoder) */
function strToBytes(str) {
  var out = [];
  for (var i = 0; i < str.length; i++) {
    var c = str.charCodeAt(i);
    if (c < 0x80) out.push(c);
    else if (c < 0x800) out.push(0xc0 | (c >> 6), 0x80 | (c & 0x3f));
    else if (c < 0xd800 || c >= 0xe000) {
      out.push(0xe0 | (c >> 12), 0x80 | ((c >> 6) & 0x3f), 0x80 | (c & 0x3f));
    } else {
      i++;
      var c2 = 0x10000 + (((c & 0x3ff) << 10) | (str.charCodeAt(i) & 0x3ff));
      out.push(0xf0 | (c2 >> 18), 0x80 | ((c2 >> 12) & 0x3f), 0x80 | ((c2 >> 6) & 0x3f), 0x80 | (c2 & 0x3f));
    }
  }
  return out;
}
function bytesToStr(bytes) {
  var out = "", i = 0;
  while (i < bytes.length) {
    var c = bytes[i++];
    if (c < 0x80) out += String.fromCharCode(c);
    else if (c < 0xe0) out += String.fromCharCode(((c & 0x1f) << 6) | (bytes[i++] & 0x3f));
    else if (c < 0xf0) {
      out += String.fromCharCode(((c & 0x0f) << 12) | ((bytes[i++] & 0x3f) << 6) | (bytes[i++] & 0x3f));
    } else {
      var cp = ((c & 0x07) << 18) | ((bytes[i++] & 0x3f) << 12) | ((bytes[i++] & 0x3f) << 6) | (bytes[i++] & 0x3f);
      cp -= 0x10000;
      out += String.fromCharCode(0xd800 + (cp >> 10), 0xdc00 + (cp & 0x3ff));
    }
  }
  return out;
}
function bytesToB64(bytes) {
  var table = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
  var out = "";
  var i = 0;
  while (i < bytes.length) {
    var a = bytes[i++] | 0;
    var b = i < bytes.length ? bytes[i++] : NaN;
    var c = i < bytes.length ? bytes[i++] : NaN;
    var n = (a << 16) | ((isNaN(b) ? 0 : b) << 8) | (isNaN(c) ? 0 : c);
    out += table.charAt((n >> 18) & 63);
    out += table.charAt((n >> 12) & 63);
    out += isNaN(b) ? "=" : table.charAt((n >> 6) & 63);
    out += isNaN(c) ? "=" : table.charAt(n & 63);
  }
  return out;
}

function isPlainImageBytes(bytes) {
  if (!bytes || bytes.length < 3) return false;
  if (bytes[0] === 0xff && bytes[1] === 0xd8) return true; // jpeg
  if (bytes[0] === 0x89 && bytes[1] === 0x50 && bytes[2] === 0x4e) return true; // png
  if (bytes[0] === 0x47 && bytes[1] === 0x49 && bytes[2] === 0x46) return true; // gif
  return false;
}

/** 拉取加密封面并 AES 解密为 data URL（不依赖外部代理） */
async function decryptCoverDataUrl(url) {
  url = t(url);
  if (!url) return "";
  if (url.indexOf("data:image") === 0) return url;
  try {
    var res = await Widget.http.get(url, {
      headers: {
        Accept: "image/*,*/*;q=0.8",
        "User-Agent": UA,
        Referer: "https://yeguodj.com/",
        Origin: "https://yeguodj.com"
      },
      base64Data: 1,
      timeout: HTTP_TIMEOUT
    });
    var raw = res && res.data;
    var cipherBytes = [];
    if (typeof raw === "string") {
      // 可能是 base64 或 普通文本
      if (/^data:/.test(raw)) return raw;
      var cleaned = raw.replace(/^data:[^;]+;base64,/, "");
      // 粗判 base64
      if (/^[A-Za-z0-9+/=\s]+$/.test(cleaned.slice(0, 80))) {
        cipherBytes = b64ToBytes(cleaned);
      } else {
        // 当普通二进制字符串
        for (var i = 0; i < raw.length; i++) cipherBytes.push(raw.charCodeAt(i) & 0xff);
      }
    } else if (raw && raw.length != null) {
      for (var j = 0; j < raw.length; j++) cipherBytes.push(raw[j] & 0xff);
    } else {
      return "";
    }
    var plain = cipherBytes;
    if (!isPlainImageBytes(cipherBytes)) {
      // AES-CBC 解密（复用块解密）
      var keyBytes = strToBytes(MEDIA_KEY);
      var ivBytes = strToBytes(MEDIA_IV);
      while (keyBytes.length < 16) keyBytes.push(0);
      while (ivBytes.length < 16) ivBytes.push(0);
      keyBytes = keyBytes.slice(0, 16);
      ivBytes = ivBytes.slice(0, 16);
      var w = keyExpansion(keyBytes);
      var prev = ivBytes.slice();
      plain = [];
      for (var off = 0; off + 16 <= cipherBytes.length; off += 16) {
        var block = cipherBytes.slice(off, off + 16);
        var dec = decryptBlock(block, w);
        for (var k = 0; k < 16; k++) plain.push(dec[k] ^ prev[k]);
        prev = block;
      }
      if (plain.length) {
        var pad = plain[plain.length - 1];
        if (pad >= 1 && pad <= 16) plain = plain.slice(0, plain.length - pad);
      }
    }
    if (!isPlainImageBytes(plain)) return "";
    var mime = "image/jpeg";
    if (plain[0] === 0x89) mime = "image/png";
    if (plain[0] === 0x47) mime = "image/gif";
    return "data:" + mime + ";base64," + bytesToB64(plain);
  } catch (e) {
    return "";
  }
}

async function hydrateCovers(c, items) {
  if (!items || !items.length) return items;
  // 并发解密封面（限制 6）
  var i = 0;
  async function worker() {
    while (i < items.length) {
      var idx = i++;
      var it = items[idx];
      var src = t(it._encCover || "");
      if (!src && it.coverUrl && it.coverUrl.indexOf("http") === 0 && it.coverUrl.indexOf("huangguo") < 0 && it.coverUrl.indexOf("data:") !== 0) {
        src = it.coverUrl;
      }
      // 若 coverUrl 已是代理地址，抽出原 url
      if (src && src.indexOf("url=") >= 0) {
        try {
          var m = src.match(/[?&]url=([^&]+)/);
          if (m) src = decodeURIComponent(m[1]);
        } catch (e) {}
      }
      if (!src) continue;
      var dataUrl = await decryptCoverDataUrl(src);
      if (dataUrl) {
        it.coverUrl = dataUrl;
        it.posterPath = dataUrl;
        it.backdropPath = dataUrl;
      }
    }
  }
  var n = Math.min(6, items.length);
  var jobs = [];
  for (var k = 0; k < n; k++) jobs.push(worker());
  await Promise.all(jobs);
  return items;
}

function b64ToBytes(b64) {
  b64 = String(b64 || "").replace(/[\r\n\s]/g, "").replace(/-/g, "+").replace(/_/g, "/");
  while (b64.length % 4) b64 += "=";
  var table = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
  var out = [];
  for (var i = 0; i < b64.length; i += 4) {
    var c1 = table.indexOf(b64.charAt(i));
    var c2 = table.indexOf(b64.charAt(i + 1));
    var c3 = table.indexOf(b64.charAt(i + 2));
    var c4 = table.indexOf(b64.charAt(i + 3));
    if (c1 < 0 || c2 < 0) continue;
    out.push(((c1 << 2) | (c2 >> 4)) & 0xff);
    if (c3 >= 0) out.push((((c2 & 15) << 4) | (c3 >> 2)) & 0xff);
    if (c4 >= 0) out.push((((c3 & 3) << 6) | c4) & 0xff);
  }
  return out;
}

var SBOX = [99,124,119,123,242,107,111,197,48,1,103,43,254,215,171,118,202,130,201,125,250,89,71,240,173,212,162,175,156,164,114,192,183,253,147,38,54,63,247,204,52,165,229,241,113,216,49,21,4,199,35,195,24,150,5,154,7,18,128,226,235,39,178,117,9,131,44,26,27,110,90,160,82,59,214,179,41,227,47,132,83,209,0,237,32,252,177,91,106,203,190,57,74,76,88,207,208,239,170,251,67,77,51,133,69,249,2,127,80,60,159,168,81,163,64,143,146,157,56,245,188,182,218,33,16,255,243,210,205,12,19,236,95,151,68,23,196,167,126,61,100,93,25,115,96,129,79,220,34,42,144,136,70,238,184,20,222,94,11,219,224,50,58,10,73,6,36,92,194,211,172,98,145,149,228,121,231,200,55,109,141,213,78,169,108,86,244,234,101,122,174,8,186,120,37,46,28,166,180,198,232,221,116,31,75,189,139,138,112,62,181,102,72,3,246,14,97,53,87,185,134,193,29,158,225,248,152,17,105,217,142,148,155,30,135,233,206,85,40,223,140,161,137,13,191,230,66,104,65,153,45,15,176,84,187];
var INV_SBOX = [82,9,106,213,48,54,165,56,191,64,163,158,129,243,215,251,124,227,57,130,155,47,255,135,52,142,67,68,196,222,233,203,84,123,148,50,166,194,35,61,238,76,149,11,66,250,195,78,8,46,161,102,40,217,36,178,118,91,162,73,109,139,209,37,114,248,246,100,134,104,152,22,212,164,92,204,93,101,182,146,108,112,72,80,253,237,185,218,94,21,70,87,167,141,157,132,144,216,171,0,140,188,211,10,247,228,88,5,184,179,69,6,208,44,30,143,202,63,15,2,193,175,189,3,1,19,138,107,58,145,17,65,79,103,220,234,151,242,207,206,240,180,230,115,150,172,116,34,231,173,53,133,226,249,55,232,28,117,223,110,71,241,26,113,29,41,197,137,111,183,98,14,170,24,190,27,252,86,62,75,198,210,121,32,154,219,192,254,120,205,90,244,31,221,168,51,136,7,199,49,177,18,16,89,39,128,236,95,96,81,127,169,25,181,74,13,45,229,122,159,147,201,156,239,160,224,59,77,174,42,245,176,200,235,187,60,131,83,153,97,23,43,4,126,186,119,214,38,225,105,20,99,85,33,12,125];

var RCON = [0x00,0x01,0x02,0x04,0x08,0x10,0x20,0x40,0x80,0x1b,0x36];

function rotWord(w) { return [w[1], w[2], w[3], w[0]]; }
function subWord(w) { return [SBOX[w[0]], SBOX[w[1]], SBOX[w[2]], SBOX[w[3]]]; }

function keyExpansion(keyBytes) {
  var Nk = 4, Nr = 10, w = [];
  for (var i = 0; i < Nk; i++) w[i] = [keyBytes[4*i], keyBytes[4*i+1], keyBytes[4*i+2], keyBytes[4*i+3]];
  for (var i = Nk; i < 4 * (Nr + 1); i++) {
    var temp = w[i - 1].slice();
    if (i % Nk === 0) {
      temp = subWord(rotWord(temp));
      temp[0] ^= RCON[i / Nk];
    }
    w[i] = [w[i-Nk][0]^temp[0], w[i-Nk][1]^temp[1], w[i-Nk][2]^temp[2], w[i-Nk][3]^temp[3]];
  }
  return w;
}
function addRoundKey(state, w, round) {
  for (var c = 0; c < 4; c++)
    for (var r = 0; r < 4; r++) state[r][c] ^= w[round * 4 + c][r];
}
function invSubBytes(state) {
  for (var r = 0; r < 4; r++)
    for (var c = 0; c < 4; c++) state[r][c] = INV_SBOX[state[r][c]];
}
function invShiftRows(state) {
  var t;
  t = state[1][3]; state[1][3]=state[1][2]; state[1][2]=state[1][1]; state[1][1]=state[1][0]; state[1][0]=t;
  t = state[2][0]; var t2 = state[2][1]; state[2][0]=state[2][2]; state[2][1]=state[2][3]; state[2][2]=t; state[2][3]=t2;
  t = state[3][0]; state[3][0]=state[3][1]; state[3][1]=state[3][2]; state[3][2]=state[3][3]; state[3][3]=t;
}
function mul(a, b) {
  var r = 0;
  for (var i = 0; i < 8; i++) {
    if (b & 1) r ^= a;
    var hi = a & 0x80;
    a = (a << 1) & 0xff;
    if (hi) a ^= 0x1b;
    b >>= 1;
  }
  return r & 0xff;
}
function invMixColumns(state) {
  for (var c = 0; c < 4; c++) {
    var a0 = state[0][c], a1 = state[1][c], a2 = state[2][c], a3 = state[3][c];
    state[0][c] = mul(a0,0x0e)^mul(a1,0x0b)^mul(a2,0x0d)^mul(a3,0x09);
    state[1][c] = mul(a0,0x09)^mul(a1,0x0e)^mul(a2,0x0b)^mul(a3,0x0d);
    state[2][c] = mul(a0,0x0d)^mul(a1,0x09)^mul(a2,0x0e)^mul(a3,0x0b);
    state[3][c] = mul(a0,0x0b)^mul(a1,0x0d)^mul(a2,0x09)^mul(a3,0x0e);
  }
}
function decryptBlock(input, w) {
  var state = [[0,0,0,0],[0,0,0,0],[0,0,0,0],[0,0,0,0]];
  for (var i = 0; i < 16; i++) state[i % 4][(i / 4) | 0] = input[i];
  addRoundKey(state, w, 10);
  for (var round = 9; round >= 1; round--) {
    invShiftRows(state); invSubBytes(state); addRoundKey(state, w, round); invMixColumns(state);
  }
  invShiftRows(state); invSubBytes(state); addRoundKey(state, w, 0);
  var out = [];
  for (var i = 0; i < 16; i++) out.push(state[i % 4][(i / 4) | 0]);
  return out;
}
function aesCbcDecryptBase64(b64, keyStr, ivStr) {
  var cipherBytes = b64ToBytes(b64);
  var keyBytes = strToBytes(keyStr);
  var ivBytes = strToBytes(ivStr);
  while (keyBytes.length < 16) keyBytes.push(0);
  while (ivBytes.length < 16) ivBytes.push(0);
  keyBytes = keyBytes.slice(0, 16);
  ivBytes = ivBytes.slice(0, 16);
  var w = keyExpansion(keyBytes);
  var prev = ivBytes.slice();
  var plain = [];
  for (var off = 0; off + 16 <= cipherBytes.length; off += 16) {
    var block = cipherBytes.slice(off, off + 16);
    var dec = decryptBlock(block, w);
    for (var i = 0; i < 16; i++) plain.push(dec[i] ^ prev[i]);
    prev = block;
  }
  if (plain.length) {
    var pad = plain[plain.length - 1];
    if (pad >= 1 && pad <= 16) plain = plain.slice(0, plain.length - pad);
  }
  return bytesToStr(plain);
}


async function apiPost(c, path, body) {
  var url = c.apiBase + path;
  var headers = {
    Accept: "application/json, text/plain, */*",
    "Content-Type": "application/json",
    "User-Agent": UA,
    Referer: "https://yeguodj.com/",
    Origin: "https://yeguodj.com"
  };
  var payload = body || {};
  var res;
  if (Widget.http.post) {
    try {
      res = await Widget.http.post(url, payload, { headers: headers, timeout: HTTP_TIMEOUT });
    } catch (e1) {
      res = null;
    }
  }
  if (!res && Widget.http.request) {
    res = await Widget.http.request({
      url: url,
      method: "POST",
      headers: headers,
      body: JSON.stringify(payload),
      timeout: HTTP_TIMEOUT
    });
  }
  if (!res) {
    // 部分接口也支持 GET
    res = await Widget.http.get(url + qs(payload), { headers: headers, timeout: HTTP_TIMEOUT });
  }
  // 失败时 status === 0 且带 error；成功靠 ok / status 判定
  if (!res || !res.ok) {
    var code = res && res.status ? res.status : 0;
    throw new Error("请求失败(" + (code || "网络错误") + "): " + path);
  }
  var d = res && res.data;
  if (typeof d === "string") {
    try {
      d = JSON.parse(d);
    } catch (e) {}
  }
  if (!d) throw new Error("空响应: " + path);
  // 加密 data 字段
  if (typeof d.data === "string" && d.data.length > 20) {
    try {
      var plain = aesCbcDecryptBase64(d.data, API_KEY, API_IV);
      d.data = JSON.parse(plain);
    } catch (e) {
      throw new Error("API 解密失败: " + (e && e.message));
    }
  }
  return d;
}

function unwrap(d) {
  if (!d) return {};
  var x = d.data != null ? d.data : d;
  if (x && x.data != null && typeof x.data === "object") return x.data;
  return x;
}

function proxiedCover(c, url) {
  url = t(url);
  if (!url) return "";
  // 野果封面为 AES 密文，必须走解密代理，否则 App 无法显示
  if (!c.coverProxy) return url;
  var base = c.coverProxy.replace(/\/+$/, "");
  var q = { url: url };
  if (c.coverToken) q.token = c.coverToken;
  // https://host/?url=...&token=...
  return base + "/" + qs(q);
}

function toItem(c, it) {
  if (!it) return null;
  var id = t(it.video_id != null ? it.video_id : it.id);
  if (!id) return null;
  var title = t(it.title || it.video_title || it.name);
  var cover = proxiedCover(c, t(it.cover || it.cover_img || it.pic || ""));
  var ep = it.episode_count || it.episodes || it.total_serial || "";
  var remark = t(it.update_status || it.serialize_status_text || "");
  if (!remark && ep) remark = "更新至" + ep + "集";
  return {
    id: "yeguo:" + id,
    type: "url",
    title: title || id,
    coverUrl: cover,
    posterPath: cover,
    backdropPath: cover,
    description: remark,
    mediaType: "tv",
    link: "yeguo:" + id,
    headers: playHeaders()
  };
}

function listFromPayload(c, data) {
  var inner = unwrap({ data: data });
  var arr =
    (inner && inner.list) ||
    (inner && inner.top_list) ||
    (Array.isArray(inner) ? inner : []);
  var out = [];
  for (var i = 0; i < arr.length; i++) {
    var item = toItem(c, arr[i]);
    if (item) out.push(item);
  }
  return out;
}

async function listFromPayloadHydrated(c, data) {
  var out = listFromPayload(c, data);
  return out;
}

async function loadExplore(params) {
  params = params || {};
  var c = cfg(params);
  var page = normPage(params, "loadExplore");
  var d = await apiPost(c, "/api/theater/exploreList", {
    page: page,
    limit: 24
  });
  return listFromPayload(c, d.data);
}

async function loadRank(params) {
  params = params || {};
  var c = cfg(params);
  var page = normPage(params, "loadRank");
  var d = await apiPost(c, "/api/theater/videoRank", {
    page: page,
    limit: 24
  });
  return listFromPayload(c, d.data);
}

async function loadHome(params) {
  params = params || {};
  var c = cfg(params);
  var page = normPage(params, "loadHome");
  if (page > 1) return loadExplore(params);
  var d = await apiPost(c, "/api/home/homePage", {});
  var inner = unwrap(d);
  var list = (inner && inner.top_list) || [];
  // 合并 modules.list 里的条目
  var mods = (inner && inner.modules && inner.modules.list) || [];
  for (var i = 0; i < mods.length; i++) {
    var m = mods[i];
    if (m && Array.isArray(m.list)) list = list.concat(m.list);
    else if (m && m.video_id) list.push(m);
  }
  var seen = {};
  var out = [];
  for (var j = 0; j < list.length; j++) {
    var it = toItem(c, list[j]);
    if (!it || seen[it.id]) continue;
    seen[it.id] = 1;
    out.push(it);
  }
  return out;
}

async function loadByBackground(params, bg) {
  params = params || {};
  var c = cfg(params);
  var page = normPage(params, "loadList");
  var body = { page: page, limit: 24 };
  if (bg != null) body.background = bg;
  var d = await apiPost(c, "/api/theater/exploreList", body);
  return listFromPayload(c, d.data);
}

async function loadBySetting(params, setting) {
  params = params || {};
  var c = cfg(params);
  var page = normPage(params, "loadList");
  var body = { page: page, limit: 24, setting: setting };
  var d = await apiPost(c, "/api/theater/exploreList", body);
  return listFromPayload(c, d.data);
}

async function loadDushi(params) { return loadByBackground(params, 40); }
async function loadXiandai(params) { return loadByBackground(params, 39); }
async function loadXiaoyuan(params) { return loadByBackground(params, 47); }
async function loadGudai(params) { return loadByBackground(params, 41); }
async function loadXiangcun(params) { return loadByBackground(params, 42); }
async function loadZhichang(params) { return loadByBackground(params, 44); }
async function loadChongsheng(params) { return loadBySetting(params, 26); }
async function loadChuanyue(params) { return loadBySetting(params, 27); }
async function loadXitong(params) { return loadBySetting(params, 28); }
async function loadNixi(params) { return loadBySetting(params, 53); }
async function loadMogai(params) { return loadBySetting(params, 56); }

async function search(params) {
  params = params || {};
  var c = cfg(params);
  // 宿主强制写入 keyword/query/wd/search 四个别名，任取其一
  var kw = t(
    params.keyword || params.query || params.wd || params.search || ""
  );
  if (!kw) return [];
  var page = normPage(params, "search");
  var d = await apiPost(c, "/api/search/result", {
    keyword: kw,
    page: page
  });
  return listFromPayload(c, d.data);
}

function parseLink(link) {
  var s = t(link).replace(/^yeguodj:/, "yeguo:");
  if (s.indexOf("yeguo:") === 0) s = s.slice(6);
  var parts = s.split(":");
  return { id: t(parts[0]), ep: t(parts[1] || "") };
}

async function loadDetail(link, extraParams) {
  var p = parseLink(link);
  if (!p.id) throw new Error("loadDetail: link 不能为空");
  // extraParams 由宿主注入全局参数默认值（apiBase/coverProxy/coverToken）
  var params = (extraParams && typeof extraParams === "object") ? extraParams : {};
  if (link && typeof link === "object") {
    params = Object.assign({}, link, params);
  }
  var c = cfg(params);

  var d = await apiPost(c, "/api/playlet/detail", { video_id: Number(p.id) || p.id });
  var info = unwrap(d);
  // detail 也可能再包一层
  if (info.video_id == null && info.data) info = info.data;
  var cover = proxiedCover(c, t(info.cover || info.cover_img || ""));
  var ph = playHeaders();
  var eps = Array.isArray(info.episodes) ? info.episodes : [];
  var episodeItems = [];
  if (eps.length) {
    for (var i = 0; i < eps.length; i++) {
      var ep = eps[i];
      var n = ep.sort || ep.episode || i + 1;
      var epLink = "yeguo:" + p.id + ":" + n;
      episodeItems.push({
        id: epLink,
        type: "url",
        title: t(ep.title || "第" + n + "集"),
        mediaType: "tv",
        seasonNumber: 1,
        episodeNumber: Number(n) || i + 1,
        link: epLink,
        videoUrl: "",
        headers: ph,
        playerType: "app"
      });
    }
  } else {
    episodeItems.push({
      id: "yeguo:" + p.id + ":1",
      type: "url",
      title: "第1集",
      mediaType: "tv",
      seasonNumber: 1,
      episodeNumber: 1,
      link: "yeguo:" + p.id + ":1",
      videoUrl: "",
      headers: ph,
      playerType: "app"
    });
  }

  // 预取第一集播放地址，确保详情页有可播放链接（详情测试要求 videoUrl 非空）
  var videoUrl = "";
  try {
    var firstEp = episodeItems.length ? (episodeItems[0].episodeNumber || 1) : 1;
    var playRes = await apiPost(c, "/api/playlet/play", {
      video_id: Number(p.id) || p.id,
      ep: Number(firstEp) || firstEp
    });
    var playInfo = unwrap(playRes);
    if (playInfo.video_url == null && playInfo.data) playInfo = playInfo.data;
    videoUrl = t(playInfo.video_url || "");
    if (!videoUrl && Array.isArray(playInfo.episodeAll)) {
      for (var j = 0; j < playInfo.episodeAll.length; j++) {
        var e = playInfo.episodeAll[j];
        if (String(e.sort || e.index) === String(firstEp) || String(e.id) === String(firstEp)) {
          videoUrl = t(e.video_url || "");
          break;
        }
      }
    }
  } catch (e) {}
  if (videoUrl && episodeItems.length) episodeItems[0].videoUrl = videoUrl;

  return {
    id: "yeguo:" + p.id,
    type: "url",
    title: t(info.title || p.id),
    coverUrl: cover,
    posterPath: cover,
    backdropPath: cover,
    description: t(info.description || info.intro || ""),
    mediaType: "tv",
    link: "yeguo:" + p.id,
    videoUrl: videoUrl,
    episodeItems: episodeItems,
    headers: ph
  };
}

async function loadResource(params) {
  params = params || {};
  var c = cfg(params);
  var p = parseLink(t(params.link || params.id || ""));
  if (!p.id) return [];
  var ep = p.ep || t(params.episode) || "1";
  var d = await apiPost(c, "/api/playlet/play", {
    video_id: Number(p.id) || p.id,
    ep: Number(ep) || ep
  });
  var info = unwrap(d);
  if (info.video_url == null && info.data) info = info.data;
  var url = t(info.video_url || "");
  if (!url && Array.isArray(info.episodeAll)) {
    for (var i = 0; i < info.episodeAll.length; i++) {
      var e = info.episodeAll[i];
      if (String(e.sort || e.index) === String(ep) || String(e.id) === String(ep)) {
        url = t(e.video_url || "");
        break;
      }
    }
  }
  if (!url) return [];
  // 播放源条目使用原生契约字段 headers
  return [
    {
      name: "野果",
      description: "第" + ep + "集",
      url: url,
      headers: playHeaders(),
      playerType: "app"
    }
  ];
}
