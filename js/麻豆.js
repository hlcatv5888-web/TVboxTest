/**
 * 麻豆 Streama（原生契约）
 * 站点: https://madou.club
 *
 * 按原生契约修订：
 * - 顶层 `var WidgetMetadata` 声明，列表模块显式 `type: "video"`、播放源 `type: "stream"`
 * - 媒体项 / 详情 / 播放源统一使用原生契约字段 `headers`（原 `customHeaders` 非标准）
 * - `loadDetail(link, extraParams)` 接收第二个参数，全局参数 baseUrl 在详情页生效；空链接抛带上下文短错误（不返回 null）
 * - 【详情页 videoUrl】loadDetail 本身即预取播放地址（share→m3u8→最高画质）填入 videoUrl，详情测试可过
 * - `search` 兼容 keyword/query/wd/search 四别名，page 校验
 * - `Widget.http` 的 `timeout` 单位为毫秒，统一 20000ms（原 `20` = 20ms 秒级超时 bug）；按 ok/status 判定失败
 * - 列表 / 搜索 / 详情走 `Widget.storage` TTL 缓存（原生列表路径不消费 cacheDuration）
 */
var WidgetMetadata = {
  id: "Streama.madou",
  title: "麻豆",
  version: "2.0.0",
  detailCacheDuration: 300,
  globalParams: [
    {
      name: "baseUrl",
      title: "站点域名",
      type: "input",
      value: "https://madou.club"
    }
  ],
  modules: [
    { id: "home", title: "最新", type: "video", functionName: "loadHome", cacheDuration: 300, params: [{ name: "page", title: "页码", type: "page", value: "1", startPage: 1 }] },
    { id: "madou", title: "麻豆传媒", type: "video", functionName: "loadMadou", cacheDuration: 300, params: [{ name: "page", title: "页码", type: "page", value: "1", startPage: 1 }] },
    { id: "hkd", title: "HongKongDoll", type: "video", functionName: "loadHkd", cacheDuration: 300, params: [{ name: "page", title: "页码", type: "page", value: "1", startPage: 1 }] },
    { id: "guodong", title: "果冻传媒", type: "video", functionName: "loadGuodong", cacheDuration: 300, params: [{ name: "page", title: "页码", type: "page", value: "1", startPage: 1 }] },
    { id: "mitao", title: "蜜桃影像", type: "video", functionName: "loadMitao", cacheDuration: 300, params: [{ name: "page", title: "页码", type: "page", value: "1", startPage: 1 }] },
    { id: "tianmei", title: "天美传媒", type: "video", functionName: "loadTianmei", cacheDuration: 300, params: [{ name: "page", title: "页码", type: "page", value: "1", startPage: 1 }] },
    { id: "jingdong", title: "精东影业", type: "video", functionName: "loadJingdong", cacheDuration: 300, params: [{ name: "page", title: "页码", type: "page", value: "1", startPage: 1 }] },
    { id: "jy91", title: "91制片厂", type: "video", functionName: "load91", cacheDuration: 300, params: [{ name: "page", title: "页码", type: "page", value: "1", startPage: 1 }] },
    { id: "huangjia", title: "皇家华人", type: "video", functionName: "loadHuangjia", cacheDuration: 300, params: [{ name: "page", title: "页码", type: "page", value: "1", startPage: 1 }] },
    { id: "tuzi", title: "兔子先生", type: "video", functionName: "loadTuzi", cacheDuration: 300, params: [{ name: "page", title: "页码", type: "page", value: "1", startPage: 1 }] },
    { id: "xingkong", title: "星空无限", type: "video", functionName: "loadXingkong", cacheDuration: 300, params: [{ name: "page", title: "页码", type: "page", value: "1", startPage: 1 }] },
    { id: "aidou", title: "爱豆", type: "video", functionName: "loadAidou", cacheDuration: 300, params: [{ name: "page", title: "页码", type: "page", value: "1", startPage: 1 }] },
    { id: "daoyan", title: "导演系列", type: "video", functionName: "loadDaoyan", cacheDuration: 300, params: [{ name: "page", title: "页码", type: "page", value: "1", startPage: 1 }] },
    { id: "daxiang", title: "大象传媒", type: "video", functionName: "loadDaxiang", cacheDuration: 300, params: [{ name: "page", title: "页码", type: "page", value: "1", startPage: 1 }] },
    { id: "maozhua", title: "猫爪影像", type: "video", functionName: "loadMaozhua", cacheDuration: 300, params: [{ name: "page", title: "页码", type: "page", value: "1", startPage: 1 }] },
    { id: "xingba", title: "杏吧", type: "video", functionName: "loadXingba", cacheDuration: 300, params: [{ name: "page", title: "页码", type: "page", value: "1", startPage: 1 }] },
    { id: "lebo", title: "乐播传媒", type: "video", functionName: "loadLebo", cacheDuration: 300, params: [{ name: "page", title: "页码", type: "page", value: "1", startPage: 1 }] },
    { id: "psycho", title: "PsychoPorn", type: "video", functionName: "loadPsycho", cacheDuration: 300, params: [{ name: "page", title: "页码", type: "page", value: "1", startPage: 1 }] },
    { id: "fanwai", title: "番外篇", type: "video", functionName: "loadFanwai", cacheDuration: 300, params: [{ name: "page", title: "页码", type: "page", value: "1", startPage: 1 }] },
    { id: "huaxu", title: "花絮", type: "video", functionName: "loadHuaxu", cacheDuration: 300, params: [{ name: "page", title: "页码", type: "page", value: "1", startPage: 1 }] },
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

var UA =
  "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36";
/* 列表 / 搜索 / 详情 TTL 缓存时长（秒）；原生列表路径不消费 cacheDuration，用 Widget.storage 自建 */
var LIST_CACHE_TTL = 300;
var SEARCH_CACHE_TTL = 300;
var DETAIL_CACHE_TTL = 300;
/* Widget.http 超时（毫秒）；原 `20` = 20ms 秒级超时 bug */
var HTTP_TIMEOUT = 20000;

function t(v) {
  return String(v == null ? "" : v).trim();
}

function baseOf(params) {
  return t((params && params.baseUrl) || "https://madou.club").replace(/\/+$/, "");
}

/* page 参数校验：非法抛带上下文短错误 */
function normPage(params, fnName) {
  var page = Number((params && params.page) || 1);
  if (!Number.isFinite(page) || page < 1) {
    throw new Error((fnName || "loadList") + ": page 必须是正整数");
  }
  return page;
}

/* TTL 缓存读写：失败静默降级，不影响主流程 */
function cacheGet(key) {
  try { return Widget.storage.get(key, null); } catch (e) { return null; }
}
function cacheSet(key, val, ttl) {
  try { Widget.storage.set(key, val, ttl); } catch (e) {}
}

function hdr(base) {
  return {
    "User-Agent": UA,
    Accept: "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    Referer: base + "/"
  };
}

async function fetchHtml(url, base) {
  // Widget.http 的 timeout 单位为毫秒，20 = 20ms 会秒级超时，必须用 20000
  var resp = await Widget.http.get(url, { headers: hdr(base), timeout: HTTP_TIMEOUT });
  // 失败时 status === 0 且带 error；成功靠 ok / status 判定
  if (!resp || !resp.ok) {
    var code = resp && resp.status ? resp.status : 0;
    throw new Error("页面请求失败(" + (code || "网络错误") + ")");
  }
  if (typeof resp.data === "string" && resp.data.length > 0) return resp.data;
  if (resp.data != null) return String(resp.data);
  if (typeof resp.body === "string" && resp.body.length > 0) return resp.body;
  throw new Error("页面内容为空");
}

function absUrl(base, u) {
  u = t(u);
  if (!u) return "";
  if (/^https?:\/\//i.test(u)) return u;
  if (u.indexOf("//") === 0) return "https:" + u;
  if (u.charAt(0) === "/") return base + u;
  return base + "/" + u;
}

function decodeHtml(s) {
  return t(s)
    .replace(/&amp;/g, "&")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'")
    .replace(/&nbsp;/g, " ");
}

/** 封面：优先 data-src / data-original，去掉占位 thumb.png；尽量升到原图 */
function pickCover(chunk, base) {
  var candidates = [];
  var re = /(?:data-src|data-original|data-thumb|src)=["']([^"']+)["']/gi;
  var m;
  while ((m = re.exec(chunk))) {
    var u = m[1];
    if (!u) continue;
    if (/thumb\.png|logo\.png|avatar|loading|placeholder/i.test(u)) continue;
    candidates.push(u);
  }
  if (!candidates.length) return "";
  var cover = candidates[0];
  // -240x180.jpg → 尝试原图路径（去掉尺寸后缀）
  cover = cover.replace(/-\d+x\d+(\.(?:jpg|jpeg|png|webp))/i, "$1");
  return absUrl(base, cover);
}

function listUrl(base, cat, page) {
  page = Number(page || 1) || 1;
  cat = t(cat);
  if (!cat || cat === "home" || cat === "latest") {
    return page <= 1 ? base + "/" : base + "/page/" + page;
  }
  // 分类 slug：中文或英文路径
  var path = base + "/category/" + encodeURIComponent(cat);
  if (page > 1) path += "/page/" + page;
  return path;
}

function parseList(html, base) {
  if (!html) return [];
  var out = [];
  var seen = {};
  var re = /<article[^>]*class="[^"]*excerpt[^"]*"[\s\S]*?<\/article>/gi;
  var m;
  while ((m = re.exec(html))) {
    var chunk = m[0];
    var hm = chunk.match(
      /<a[^>]+class="[^"]*thumbnail[^"]*"[^>]+href=["']([^"']+)["']/i
    );
    if (!hm) hm = chunk.match(/<h2[^>]*>\s*<a[^>]+href=["']([^"']+)["']/i);
    if (!hm) hm = chunk.match(/href=["'](https?:\/\/[^"']+\.html)["']/i);
    if (!hm) continue;
    var link = absUrl(base, hm[1]);
    if (seen[link]) continue;
    seen[link] = 1;

    var title = "";
    var tm = chunk.match(/<h2[^>]*>\s*<a[^>]*>([^<]+)<\/a>/i);
    if (tm) title = decodeHtml(tm[1]);
    if (!title) {
      tm = chunk.match(/title=["']([^"']+)["']/i);
      if (tm) title = decodeHtml(tm[1]);
    }
    if (!title) title = link;

    var cover = pickCover(chunk, base);
    var id = link;
    var idm = link.match(/\/([^\/]+)\.html/i);
    if (idm) id = decodeURIComponent(idm[1]);

    out.push({
      id: id,
      type: "url",
      title: title,
      coverUrl: cover,
      posterPath: cover,
      backdropPath: cover,
      description: "",
      mediaType: "movie",
      link: link,
      headers: { "User-Agent": UA, Referer: base + "/" }
    });
  }
  return out;
}

async function loadByCat(params, cat) {
  params = params || {};
  var base = baseOf(params);
  var page = normPage(params, "loadList");
  var url = listUrl(base, cat, page);
  var cacheKey = "list:" + cat + ":" + page + ":" + base;
  var cached = cacheGet(cacheKey);
  if (cached) return cached;
  var html = await fetchHtml(url, base);
  var list = parseList(html, base);
  cacheSet(cacheKey, list, LIST_CACHE_TTL);
  return list;
}

async function loadHome(params) { return loadByCat(params, "home"); }
async function loadMadou(params) { return loadByCat(params, "麻豆传媒"); }
async function loadHkd(params) { return loadByCat(params, "hongkongdoll"); }
async function loadGuodong(params) { return loadByCat(params, "果冻传媒"); }
async function loadMitao(params) { return loadByCat(params, "蜜桃影像"); }
async function loadTianmei(params) { return loadByCat(params, "天美传媒"); }
async function loadJingdong(params) { return loadByCat(params, "精东影业"); }
async function load91(params) { return loadByCat(params, "91制片厂"); }
async function loadHuangjia(params) { return loadByCat(params, "皇家华人"); }
async function loadTuzi(params) { return loadByCat(params, "兔子先生"); }
async function loadXingkong(params) { return loadByCat(params, "星空无限传媒"); }
async function loadAidou(params) { return loadByCat(params, "爱豆"); }
async function loadDaoyan(params) { return loadByCat(params, "麻豆导演系列"); }
async function loadDaxiang(params) { return loadByCat(params, "大象传媒"); }
async function loadMaozhua(params) { return loadByCat(params, "猫爪影像"); }
async function loadXingba(params) { return loadByCat(params, "杏吧"); }
async function loadLebo(params) { return loadByCat(params, "乐播传媒"); }
async function loadPsycho(params) { return loadByCat(params, "psychoporntw"); }
async function loadFanwai(params) { return loadByCat(params, "麻豆番外篇"); }
async function loadHuaxu(params) { return loadByCat(params, "麻豆花絮"); }

async function search(params) {
  params = params || {};
  var base = baseOf(params);
  // 宿主强制写入 keyword/query/wd/search 四个别名，任取其一
  var kw = t(
    params.keyword || params.query || params.wd || params.search || ""
  );
  if (!kw) return [];
  var page = normPage(params, "search");
  var cacheKey = "search:" + kw + ":" + page + ":" + base;
  var cached = cacheGet(cacheKey);
  if (cached) return cached;
  var url = base + "/?s=" + encodeURIComponent(kw);
  if (page > 1) url = base + "/page/" + page + "/?s=" + encodeURIComponent(kw);
  var html = await fetchHtml(url, base);
  var list = parseList(html, base);
  cacheSet(cacheKey, list, SEARCH_CACHE_TTL);
  return list;
}

function extractShareUrl(html) {
  if (!html) return "";
  var m =
    html.match(
      /src\s*=\s*["']?(https?:\/\/dash\.madou\.club\/share\/[a-zA-Z0-9]+)["'\s>]/i
    ) ||
    html.match(
      /src\s*=\s*["']?(https?:\/\/[^"'\s>]+\.madou\.[^"'\s>]+\/share\/[a-zA-Z0-9]+)["'\s>]/i
    ) ||
    html.match(/https?:\/\/dash\.madou\.club\/share\/[a-zA-Z0-9]+/i);
  if (!m) return "";
  return m[1] || m[0];
}

async function resolvePlayFromShare(shareUrl, base) {
  shareUrl = t(shareUrl);
  if (!shareUrl) return null;
  var playerHtml = await fetchHtml(shareUrl, base);
  var tokenM = playerHtml.match(/var\s+token\s*=\s*["']([^"']*)["']/);
  var m3u8M = playerHtml.match(/var\s+m3u8\s*=\s*["']([^"']+)["']/);
  if (!m3u8M) return null;
  var path = m3u8M[1];
  var dashBase =
    (shareUrl.match(/^(https?:\/\/[^\/]+)/i) || [])[1] ||
    "https://dash.madou.club";
  if (path.indexOf("/") === 0) path = dashBase + path;
  else if (!/^https?:\/\//i.test(path))
    path = dashBase.replace(/\/+$/, "") + "/" + path.replace(/^\/+/, "");
  var token = (tokenM && tokenM[1]) || "";
  if (token) path += (path.indexOf("?") >= 0 ? "&" : "?") + "token=" + token;
  return { url: path, shareUrl: shareUrl };
}

/** master → 最高画质子流 */
async function pickBestHls(masterUrl, base) {
  try {
    var txt = await fetchHtml(masterUrl, base);
    if (!txt || txt.indexOf("#EXT-X-STREAM-INF") === -1) return masterUrl;
    var lines = txt.split(/\r?\n/);
    var best = null;
    var bestScore = -1;
    for (var i = 0; i < lines.length; i++) {
      if (!/#EXT-X-STREAM-INF/i.test(lines[i])) continue;
      var res = lines[i].match(/RESOLUTION=\d+x(\d+)/i);
      var bw = lines[i].match(/BANDWIDTH=(\d+)/i);
      var h = res ? parseInt(res[1], 10) : 0;
      var score = res ? h : bw ? parseInt(bw[1], 10) / 1000 : 0;
      var j = i + 1;
      while (
        j < lines.length &&
        (!lines[j].replace(/\s/g, "") || lines[j].charAt(0) === "#")
      )
        j++;
      var vurl = j < lines.length ? t(lines[j]) : "";
      if (!vurl) continue;
      try {
        // relative → absolute
        if (!/^https?:\/\//i.test(vurl)) {
          var basePath = masterUrl.replace(/\/[^\/]*$/, "/");
          vurl = vurl.indexOf("/") === 0
            ? masterUrl.match(/^https?:\/\/[^\/]+/)[0] + vurl
            : basePath + vurl;
        }
      } catch (e) {}
      if (score > bestScore) {
        bestScore = score;
        best = vurl;
      }
    }
    return best || masterUrl;
  } catch (e) {
    return masterUrl;
  }
}

function normalizeLink(link) {
  if (link && typeof link === "object") {
    return t(link.link || link.id || link.url || "");
  }
  return t(link);
}

/* 播放请求头：HLS 需要 UA/Referer/Origin */
function playHeaders(base) {
  return {
    "User-Agent": UA,
    Referer: base + "/",
    Origin: "https://dash.madou.club"
  };
}

async function loadDetail(link, extraParams) {
  var pageUrl = normalizeLink(link);
  if (!pageUrl) throw new Error("loadDetail: link 不能为空");
  // extraParams 由宿主注入全局参数默认值（baseUrl）
  var params = (extraParams && typeof extraParams === "object") ? extraParams : {};
  if (link && typeof link === "object") {
    params = Object.assign({}, link, params);
  }
  var base = baseOf(params);
  if (!/^https?:\/\//i.test(pageUrl)) {
    pageUrl = absUrl(base, pageUrl.indexOf("/") === 0 ? pageUrl : "/" + pageUrl);
  }

  var cacheKey = "detail:" + pageUrl;
  var cached = cacheGet(cacheKey);
  if (cached) return cached;

  var html = await fetchHtml(pageUrl, base);

  var title = "";
  var tm = html.match(/<h1[^>]*class="[^"]*article-title[^"]*"[^>]*>([^<]+)/i);
  if (tm) title = decodeHtml(tm[1]);
  if (!title) {
    tm = html.match(/<h1[^>]*>([^<]{2,200})<\/h1>/i);
    if (tm) title = decodeHtml(tm[1]);
  }
  if (!title) {
    tm = html.match(/<title>([^<]+)<\/title>/i);
    if (tm) title = decodeHtml(tm[1].replace(/\s*[-|_].*$/, ""));
  }

  var cover = pickCover(html, base);
  // 详情页优先 covers/ 下的图
  var cm = html.match(
    /(?:data-src|src)=["'](https?:\/\/[^"']*\/covers\/[^"']+\.(?:jpg|jpeg|png|webp)[^"']*)["']/i
  );
  if (cm) cover = absUrl(base, cm[1].replace(/-\d+x\d+(\.(?:jpg|jpeg|png|webp))/i, "$1"));

  var ph = playHeaders(base);
  // 详情页本身即预取播放地址：share → m3u8 → 最高画质，填入 videoUrl（详情测试要求非空）
  var share = extractShareUrl(html);
  var play = share ? await resolvePlayFromShare(share, base) : null;
  var videoUrl = "";
  if (play && play.url) {
    videoUrl = await pickBestHls(play.url, base);
  }

  var result = {
    id: pageUrl,
    type: "url",
    title: title || pageUrl,
    description: "",
    coverUrl: cover,
    posterPath: cover,
    backdropPath: cover,
    videoUrl: videoUrl,
    mediaType: "movie",
    link: pageUrl,
    headers: ph
  };
  cacheSet(cacheKey, result, DETAIL_CACHE_TTL);
  return result;
}

async function loadResource(params) {
  params = params || {};
  var pageUrl = t(params.link || params.id || "");
  if (!pageUrl) return [];
  var base = baseOf(params);
  if (!/^https?:\/\//i.test(pageUrl)) {
    pageUrl = absUrl(base, pageUrl);
  }
  var html = await fetchHtml(pageUrl, base);
  var share = extractShareUrl(html);
  if (!share) return [];
  var play = await resolvePlayFromShare(share, base);
  if (!play || !play.url) return [];
  var best = await pickBestHls(play.url, base);
  var headers = playHeaders(base);
  // 播放源条目使用原生契约字段 headers
  var list = [
    {
      name: "最高画质",
      description: "HLS",
      url: best,
      headers: headers
    }
  ];
  if (best !== play.url) {
    list.push({
      name: "原画(Master)",
      description: "HLS Master",
      url: play.url,
      headers: headers
    });
  }
  return list;
}
