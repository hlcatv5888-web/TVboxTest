/**
 * 57吃瓜网 Streama Widget（原生契约）
 * 站点: https://57cg4.com
 * 列表 /events/{id}/ ，详情提取 m3u8 / mp4
 *
 * 按 Streama 组件开发指南(2.md)与静态示例(1.js)修订：
 * - 顶层 `var WidgetMetadata` 声明，列表模块显式 `type: "video"`、播放源 `type: "stream"`
 * - 媒体项 / 详情 / 播放源统一使用原生契约字段 `headers`（原 `customHeaders` 非标准）
 * - `Widget.http` 的 `timeout` 单位为毫秒，统一 20000ms（原 `20` = 20ms 秒级超时 bug）
 * - `loadDetail(link, extraParams)` 接收第二个参数，全局参数 baseUrl/coverProxy 在详情页生效
 * - HTTP 失败按 `ok`/`status` 判定，错误文案短且不含凭据
 * - 列表 / 搜索 / 详情走 `Widget.storage` TTL 缓存（原生列表路径不消费 cacheDuration）
 * - 搜索关键词补全 keyword/query/wd/search 别名，page 非法抛带上下文短错误
 */
var WidgetMetadata = {
  id: "streama.57chigua",
  title: "57吃瓜",
  version: "2.0.0",
  detailCacheDuration: 300,
  globalParams: [
    {
      name: "baseUrl",
      title: "站点域名",
      type: "input",
      value: "https://57cg4.com"
    },
    {
      name: "coverProxy",
      title: "封面代理前缀(防盗链)",
      type: "input",
      value: "",
      description: "封面 CDN 需 Referer。若无图可填代理，如 https://images.weserv.nl/?url= 或自建 Worker"
    }
  ],
  modules: [
    {
      id: "hot",
      title: "热门",
      type: "video",
      functionName: "loadHot",
      cacheDuration: 300,
      params: [{ name: "page", title: "页码", type: "page", value: "1", startPage: 1 }]
    },
    {
      id: "home",
      title: "首页最新",
      type: "video",
      functionName: "loadHome",
      cacheDuration: 300,
      params: [{ name: "page", title: "页码", type: "page", value: "1", startPage: 1 }]
    },
    {
      id: "jrcg",
      title: "今日吃瓜",
      type: "video",
      functionName: "loadJrcg",
      cacheDuration: 300,
      params: [{ name: "page", title: "页码", type: "page", value: "1", startPage: 1 }]
    },
    {
      id: "aichengduanju",
      title: "成人AI短剧",
      type: "video",
      functionName: "loadAiDuanju",
      cacheDuration: 300,
      params: [{ name: "page", title: "页码", type: "page", value: "1", startPage: 1 }]
    },
    {
      id: "mrds",
      title: "每日大赛",
      type: "video",
      functionName: "loadMrds",
      cacheDuration: 300,
      params: [{ name: "page", title: "页码", type: "page", value: "1", startPage: 1 }]
    },
    {
      id: "wanghong",
      title: "网红黑料",
      type: "video",
      functionName: "loadWanghong",
      cacheDuration: 300,
      params: [{ name: "page", title: "页码", type: "page", value: "1", startPage: 1 }]
    },
    {
      id: "video",
      title: "网黄合集",
      type: "video",
      functionName: "loadVideo",
      cacheDuration: 300,
      params: [{ name: "page", title: "页码", type: "page", value: "1", startPage: 1 }]
    },
    {
      id: "cheating",
      title: "出轨劈腿",
      type: "video",
      functionName: "loadCheating",
      cacheDuration: 300,
      params: [{ name: "page", title: "页码", type: "page", value: "1", startPage: 1 }]
    },
    {
      id: "live",
      title: "直播擦边",
      type: "video",
      functionName: "loadLive",
      cacheDuration: 300,
      params: [{ name: "page", title: "页码", type: "page", value: "1", startPage: 1 }]
    },
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

/* 列表 / 详情 TTL 缓存时长（秒）；原生列表路径不消费 cacheDuration，按指南用 Widget.storage 自建 */
var LIST_CACHE_TTL = 300;
var DETAIL_CACHE_TTL = 300;

function t(v) {
  return String(v == null ? "" : v).trim();
}

function baseOf(params) {
  return t((params && params.baseUrl) || "https://57cg4.com").replace(/\/+$/, "");
}

/* 请求头构造（函数名避开媒体项字段名 headers） */
function reqHeaders(base) {
  return {
    "User-Agent": UA,
    Accept: "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    Referer: base + "/"
  };
}

/* TTL 缓存读写：失败静默降级，不影响主流程 */
function cacheGet(key) {
  try {
    return Widget.storage.get(key, null);
  } catch (e) {
    return null;
  }
}
function cacheSet(key, val, ttl) {
  try {
    Widget.storage.set(key, val, ttl);
  } catch (e) {}
}

async function fetchHtml(url, base) {
  // Widget.http 的 timeout 单位为毫秒，20 = 20ms 会秒超时，必须用 20000
  var resp = await Widget.http.get(url, {
    headers: reqHeaders(base),
    timeout: 20000
  });
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

/** 去掉标题前重复的分类/栏目前缀，只保留正常片名 */
function cleanTitle(title) {
  var raw = decodeHtml(title);
  if (!raw) return "";
  var prefixes = [
    "AI成人短剧",
    "成人AI短剧",
    "每日大赛",
    "今日吃瓜",
    "网红黑料",
    "网黄合集",
    "出轨劈腿",
    "直播擦边",
    "社会事件",
    "明星八卦",
    "热门事件",
    "热门",
    "每日大"
  ];
  var out = raw;
  var changed = true;
  while (changed) {
    changed = false;
    out = t(out);
    for (var i = 0; i < prefixes.length; i++) {
      var p = prefixes[i];
      if (out.indexOf(p) === 0) {
        out = out.slice(p.length).replace(/^[\s\-_|｜·:：]+/, "");
        changed = true;
        break;
      }
    }
  }
  out = t(out);
  return out || raw;
}

function listUrl(base, category, page) {
  page = Number(page || 1) || 1;
  category = t(category || "hot");
  if (category === "home" || category === "") {
    return page <= 1 ? base + "/" : base + "/page/" + page + "/";
  }
  var path = base + "/" + category + "/";
  if (page > 1) path += "?page=" + page;
  return path;
}

function searchUrl(base, keyword, page) {
  page = Number(page || 1) || 1;
  var u = base + "/search/?q=" + encodeURIComponent(keyword);
  if (page > 1) u += "&page=" + page;
  return u;
}

function wrapCover(url, base, proxy) {
  url = t(url);
  if (!url) return "";
  url = absUrl(base, url);
  proxy = t(proxy);
  if (!proxy) return url;
  // 支持两种写法：
  // 1) https://xxx/?url=   → 自动 encode 完整地址
  // 2) https://xxx/proxy?u= → 同上
  if (/[?&]url=$/.test(proxy) || /[?&]u=$/.test(proxy) || /[?&]src=$/.test(proxy)) {
    return proxy + encodeURIComponent(url);
  }
  if (proxy.charAt(proxy.length - 1) === "=") {
    return proxy + encodeURIComponent(url);
  }
  return proxy + (proxy.indexOf("?") >= 0 ? "&url=" : "?url=") + encodeURIComponent(url);
}

function cardHeaders(base) {
  return {
    "User-Agent": UA,
    Referer: base + "/",
    Origin: base
  };
}

/**
 * 解析列表页卡片：/events/{id}/
 * 封面在 <a> 内部的 img，CDN 需 Referer（无 Referer 会 403）
 * 卡片请求头统一写入原生契约字段 headers
 */
function parseList(html, base, proxy) {
  if (!html) return [];
  var out = [];
  var seen = {};
  // 优先按完整 <a>...</a> 卡片截取，避免切分丢图
  var re = /<a[^>]+href="\/events\/(\d+)\/"[^>]*>([\s\S]*?)<\/a>/gi;
  var m;
  while ((m = re.exec(html))) {
    var id = m[1];
    if (seen[id]) continue;
    var body = m[0]; // 含开标签，title/alt 都在这里
    // 只保留带图的主卡片，过滤页脚相关推荐纯文字链
    var im = body.match(
      /(?:src|data-src|data-original)=["'](https?:\/\/[^"']+\.(?:jpg|jpeg|png|webp)[^"']*)["']/i
    );
    if (!im) {
      im = body.match(
        /(?:src|data-src)=["'](\/[^"']+\.(?:jpg|jpeg|png|webp)[^"']*)["']/i
      );
    }
    if (!im) continue; // 无封面的链直接跳过，避免一堆空白卡片
    seen[id] = 1;

    var title = "";
    var tm = body.match(/alt=["']([^"']{2,200})["']/i);
    if (tm) title = tm[1];
    if (!title) {
      tm = body.match(/title=["']([^"']{2,200})["']/i);
      if (tm) title = tm[1];
    }
    if (!title) {
      tm = body.match(/<h[123][^>]*>([^<]{2,200})<\/h/i);
      if (tm) title = tm[1];
    }
    title = cleanTitle(title);
    if (!title) title = "事件 " + id;

    var cover = wrapCover(im[1], base, proxy);
    out.push({
      id: id,
      type: "url",
      title: title,
      coverUrl: cover,
      posterPath: cover,
      backdropPath: cover,
      description: "",
      mediaType: "movie",
      link: id,
      headers: cardHeaders(base)
    });
  }

  // 兜底：旧切分逻辑（若上面一个都没解析到）
  if (!out.length) {
    var parts = html.split(/(?=<a[^>]+href="\/events\/\d+\/")/i);
    for (var i = 0; i < parts.length; i++) {
      var p = parts[i];
      var mm = p.match(/href="\/events\/(\d+)\/"/i);
      if (!mm || seen[mm[1]]) continue;
      var id2 = mm[1];
      var im2 = p.match(
        /(?:src|data-src|data-original)="(https?:\/\/[^"]+\.(?:jpg|jpeg|png|webp)[^"]*)"/i
      );
      if (!im2) continue;
      seen[id2] = 1;
      var title2 = "";
      var t2 = p.match(/alt="([^"]{2,200})"/i) || p.match(/title="([^"]{2,200})"/i);
      if (t2) title2 = cleanTitle(t2[1]);
      if (!title2) title2 = "事件 " + id2;
      var cover2 = wrapCover(im2[1], base, proxy);
      out.push({
        id: id2,
        type: "url",
        title: title2,
        coverUrl: cover2,
        posterPath: cover2,
        backdropPath: cover2,
        description: "",
        mediaType: "movie",
        link: id2,
        headers: cardHeaders(base)
      });
    }
  }
  return out;
}

function extractPlay(html) {
  var sources = [];
  var seen = {};
  function add(url, name) {
    url = t(url);
    if (!url || seen[url]) return;
    if (!/^https?:\/\//i.test(url)) return;
    seen[url] = 1;
    sources.push({ name: name || "播放", url: url });
  }
  var m3 = html.match(/https?:\/\/[^"'\s<>]+\.m3u8[^"'\s<>]*/gi) || [];
  for (var i = 0; i < m3.length; i++) add(m3[i], "HLS");
  var mp = html.match(/https?:\/\/[^"'\s<>]+\.mp4[^"'\s<>]*/gi) || [];
  for (var j = 0; j < mp.length; j++) add(mp[j], "MP4");
  // 兜底：json 字段
  var fields = html.match(
    /["'](?:url|play_url|playUrl|src|file|video)["']\s*:\s*["'](https?:\/\/[^"']+)["']/gi
  );
  if (fields) {
    for (var k = 0; k < fields.length; k++) {
      var um = fields[k].match(/https?:\/\/[^"']+/);
      if (um) {
        var u = um[0];
        if (/\.m3u8/i.test(u)) add(u, "HLS");
        else if (/\.mp4/i.test(u)) add(u, "MP4");
      }
    }
  }
  return sources;
}

function extractTitle(html, fallback) {
  var m = html.match(/property=["']og:title["'][^>]*content=["']([^"']+)/i);
  if (m) return cleanTitle(m[1]);
  m = html.match(/content=["']([^"']+)["'][^>]*property=["']og:title["']/i);
  if (m) return cleanTitle(m[1]);
  m = html.match(/<h1[^>]*>([^<]{2,200})<\/h1>/i);
  if (m) return cleanTitle(m[1]);
  m = html.match(/<title>([^<]+)<\/title>/i);
  if (m) {
    return cleanTitle(m[1].replace(/\s*[-|_｜].*57.*/, "").trim());
  }
  return fallback || "";
}

function extractCover(html, base) {
  var m = html.match(/property=["']og:image["'][^>]*content=["']([^"']+)/i);
  if (m) return absUrl(base, m[1]);
  m = html.match(/content=["']([^"']+)["'][^>]*property=["']og:image["']/i);
  if (m) return absUrl(base, m[1]);
  m = html.match(
    /(?:src|data-src)="(https?:\/\/s\.chigua\.media\/media\/[^"]+\.(?:jpg|jpeg|png|webp)[^"]*)"/i
  );
  if (m) return m[1];
  return "";
}

function normPage(params) {
  var page = Number((params && params.page) || 1);
  if (!Number.isFinite(page) || page < 1) {
    throw new Error("page 必须是正整数");
  }
  return page;
}

async function loadByCat(params, category) {
  params = params || {};
  var base = baseOf(params);
  var proxy = t(params.coverProxy || "");
  var page = normPage(params);
  var url = listUrl(base, category, page);

  var cacheKey = "list:" + category + ":" + page + ":" + base;
  var cached = cacheGet(cacheKey);
  if (cached) return cached;

  var html = await fetchHtml(url, base);
  var list = parseList(html, base, proxy);
  cacheSet(cacheKey, list, LIST_CACHE_TTL);
  return list;
}

async function loadHot(params) {
  return loadByCat(params, "hot");
}
async function loadHome(params) {
  return loadByCat(params, "home");
}
async function loadJrcg(params) {
  return loadByCat(params, "jrcg");
}
async function loadAiDuanju(params) {
  return loadByCat(params, "aichengduanju");
}
async function loadMrds(params) {
  return loadByCat(params, "mrds");
}
async function loadWanghong(params) {
  return loadByCat(params, "wanghong");
}
async function loadVideo(params) {
  return loadByCat(params, "video");
}
async function loadCheating(params) {
  return loadByCat(params, "cheating");
}
async function loadLive(params) {
  return loadByCat(params, "live");
}

async function loadList(params) {
  // 兼容旧调用
  params = params || {};
  return loadByCat(params, t(params.category || "hot"));
}

async function search(params) {
  params = params || {};
  var page = normPage(params);
  var base = baseOf(params);
  var proxy = t(params.coverProxy || "");
  // 宿主强制写入 keyword/query/wd/search 四个别名，任取其一
  var kw = t(
    params.keyword || params.query || params.wd || params.search || params.q || ""
  );
  if (!kw) return [];
  var url = searchUrl(base, kw, page);

  var cacheKey = "search:" + kw + ":" + page + ":" + base;
  var cached = cacheGet(cacheKey);
  if (cached) return cached;

  var html = await fetchHtml(url, base);
  var list = parseList(html, base, proxy);
  cacheSet(cacheKey, list, LIST_CACHE_TTL);
  return list;
}

async function loadDetail(link, extraParams) {
  var id = t(link);
  // 兼容 params 对象
  if (id && typeof link === "object") {
    id = t(link.link || link.id || "");
  }
  if (!id) throw new Error("loadDetail: link 不能为空");
  // 去掉可能的前缀
  var mm = id.match(/events\/(\d+)/);
  if (mm) id = mm[1];
  id = id.replace(/[^0-9]/g, "");
  if (!id) throw new Error("loadDetail: 无法解析事件 id");

  // 第二个参数 extraParams 由宿主注入全局参数默认值（baseUrl/coverProxy）
  var params = (extraParams && typeof extraParams === "object") ? extraParams : {};
  if (link && typeof link === "object") {
    params = Object.assign({}, link, params);
  }
  var base = baseOf(params);
  var proxy = t(params.coverProxy || "");

  var cacheKey = "detail:" + id + ":" + base;
  var cached = cacheGet(cacheKey);
  if (cached) return cached;

  var pageUrl = base + "/events/" + id + "/";
  var html = await fetchHtml(pageUrl, base);
  var title = extractTitle(html, id);
  var cover = wrapCover(extractCover(html, base), base, proxy);
  var sources = extractPlay(html);
  var best = sources.length ? sources[0].url : "";

  // 简介：截一点正文
  var desc = "";
  var dm = html.match(
    /property=["']og:description["'][^>]*content=["']([^"']+)/i
  );
  if (dm) desc = decodeHtml(dm[1]);

  var detail = {
    id: id,
    type: "url",
    title: title,
    description: desc,
    coverUrl: cover,
    posterPath: cover,
    backdropPath: cover,
    videoUrl: best,
    mediaType: "movie",
    link: id,
    headers: {
      "User-Agent": UA,
      Referer: pageUrl,
      Origin: base
    }
  };
  cacheSet(cacheKey, detail, DETAIL_CACHE_TTL);
  return detail;
}

async function loadResource(params) {
  params = params || {};
  var id = t(params.link || params.id || "");
  var mm = id.match(/events\/(\d+)/);
  if (mm) id = mm[1];
  id = id.replace(/[^0-9]/g, "");
  if (!id) return [];

  var base = baseOf(params);
  var pageUrl = base + "/events/" + id + "/";
  var html = await fetchHtml(pageUrl, base);
  var sources = extractPlay(html);
  var hdrs = {
    "User-Agent": UA,
    Referer: pageUrl,
    Origin: base
  };
  // 播放源条目使用原生契约字段 headers；无结果返回空数组
  return sources.map(function (s, idx) {
    return {
      name: (s.name || "线路") + (sources.length > 1 ? " " + (idx + 1) : ""),
      description: s.name || "",
      url: s.url,
      headers: hdrs
    };
  });
}
