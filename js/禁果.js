/**
 * 禁果短剧 Streama（原生契约）
 * 站点: https://jinguoduanju.app
 * 分类：navigationId（官方剧场导航）+ 本地 tags 过滤
 * 宣传: https://t.me/nostremby
 *
 * 按原生契约修订：
 * - 顶层 `var WidgetMetadata` 声明，列表模块显式 `type: "video"`、播放源 `type: "stream"`
 * - 媒体项 / 详情 / 剧集 / 播放源统一使用原生契约字段 `headers`（原 `customHeaders` 非标准）
 * - `loadDetail(link, extraParams)` 接收第二个参数，全局参数 apiBase 在详情页生效；空链接抛带上下文短错误（不返回 null）
 * - 【详情页 videoUrl 修复】详情测试要求 videoUrl 非空，loadDetail 预取第一集播放地址填入 videoUrl
 * - `search` 兼容 keyword/query/wd/search 四别名，page 校验
 * - `Widget.http` 统一设置 timeout（毫秒）并按 ok/status 判定失败
 * - 列表 / 搜索 / 详情走 `Widget.storage` TTL 缓存（原生列表路径不消费 cacheDuration）
 */
var WidgetMetadata = {
  id: "Streama.jinguoduanju",
  title: "禁果短剧",
  version: "2.0.0",
  detailCacheDuration: 180,
  globalParams: [
    {
      name: "apiBase",
      title: "API 地址",
      type: "input",
      value: "https://jinguoduanju.app"
    }
  ],
  modules: [
    { id: "heat", title: "热度", type: "video", functionName: "loadHeat", cacheDuration: 300, params: [{ name: "page", title: "页码", type: "page", value: "1", startPage: 1 }] },
    { id: "latest", title: "最新", type: "video", functionName: "loadLatest", cacheDuration: 300, params: [{ name: "page", title: "页码", type: "page", value: "1", startPage: 1 }] },
    { id: "landing", title: "首页推荐", type: "video", functionName: "loadLanding", cacheDuration: 300, params: [{ name: "page", title: "页码", type: "page", value: "1", startPage: 1 }] },
    { id: "nav_all", title: "全部", type: "video", functionName: "loadNavAll", cacheDuration: 300, params: [{ name: "page", title: "页码", type: "page", value: "1", startPage: 1 }] },
    { id: "nav_original", title: "原创精品", type: "video", functionName: "loadNavOriginal", cacheDuration: 300, params: [{ name: "page", title: "页码", type: "page", value: "1", startPage: 1 }] },
    { id: "nav_single", title: "单体作品", type: "video", functionName: "loadNavSingle", cacheDuration: 300, params: [{ name: "page", title: "页码", type: "page", value: "1", startPage: 1 }] },
    { id: "nav_anime", title: "动漫改编", type: "video", functionName: "loadNavAnime", cacheDuration: 300, params: [{ name: "page", title: "页码", type: "page", value: "1", startPage: 1 }] },
    { id: "nav_movie", title: "影视改编", type: "video", functionName: "loadNavMovie", cacheDuration: 300, params: [{ name: "page", title: "页码", type: "page", value: "1", startPage: 1 }] },
    { id: "len_multi", title: "多集", type: "video", functionName: "loadLenMulti", cacheDuration: 300, params: [{ name: "page", title: "页码", type: "page", value: "1", startPage: 1 }] },
    { id: "len_single", title: "单集", type: "video", functionName: "loadLenSingle", cacheDuration: 300, params: [{ name: "page", title: "页码", type: "page", value: "1", startPage: 1 }] },
    { id: "tag_mogai", title: "魔改", type: "video", functionName: "loadTagMogai", cacheDuration: 300, params: [{ name: "page", title: "页码", type: "page", value: "1", startPage: 1 }] },
    { id: "tag_dushi", title: "都市", type: "video", functionName: "loadTagDushi", cacheDuration: 300, params: [{ name: "page", title: "页码", type: "page", value: "1", startPage: 1 }] },
    { id: "tag_zhichang", title: "职场", type: "video", functionName: "loadTagZhichang", cacheDuration: 300, params: [{ name: "page", title: "页码", type: "page", value: "1", startPage: 1 }] },
    { id: "tag_qihuan", title: "奇幻", type: "video", functionName: "loadTagQihuan", cacheDuration: 300, params: [{ name: "page", title: "页码", type: "page", value: "1", startPage: 1 }] },
    { id: "tag_guzhuang", title: "古装", type: "video", functionName: "loadTagGuzhuang", cacheDuration: 300, params: [{ name: "page", title: "页码", type: "page", value: "1", startPage: 1 }] },
    { id: "tag_dongman", title: "动漫", type: "video", functionName: "loadTagDongman", cacheDuration: 300, params: [{ name: "page", title: "页码", type: "page", value: "1", startPage: 1 }] },
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
  "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15";
var _token = "";
var _deviceId = "";
var PAGE_SIZE = 24;
/* 列表 / 搜索 / 详情 TTL 缓存时长（秒）；原生列表路径不消费 cacheDuration，用 Widget.storage 自建 */
var LIST_CACHE_TTL = 300;
var SEARCH_CACHE_TTL = 300;
var DETAIL_CACHE_TTL = 180;
/* Widget.http 超时（毫秒） */
var HTTP_TIMEOUT = 20000;

function t(v) {
  return String(v == null ? "" : v).trim();
}

function cfg(params) {
  params = params || {};
  return {
    apiBase: t(params.apiBase || "https://jinguoduanju.app").replace(/\/+$/, "")
  };
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

function qs(obj) {
  var parts = [];
  Object.keys(obj || {}).forEach(function (k) {
    var v = obj[k];
    if (v == null || v === "") return;
    if (Array.isArray(v)) {
      for (var i = 0; i < v.length; i++) {
        parts.push(encodeURIComponent(k) + "=" + encodeURIComponent(String(v[i])));
      }
    } else {
      parts.push(encodeURIComponent(k) + "=" + encodeURIComponent(String(v)));
    }
  });
  return parts.length ? "?" + parts.join("&") : "";
}

function absUrl(base, u) {
  u = t(u);
  if (!u) return "";
  if (/^https?:\/\//i.test(u)) return u;
  if (u.indexOf("//") === 0) return "https:" + u;
  return base + (u.charAt(0) === "/" ? "" : "/") + u;
}

function randDevice() {
  var s = "";
  var hex = "0123456789abcdef";
  for (var i = 0; i < 32; i++) s += hex.charAt((Math.random() * 16) | 0);
  return s;
}

/* 播放请求头：播放器需要 UA/Referer/Origin */
function playHeaders(c) {
  return {
    "User-Agent": UA,
    Referer: c.apiBase + "/",
    Origin: c.apiBase,
    "X-Forward-Skip-Redirect-Probe": "1"
  };
}

async function ensureToken(c) {
  if (_token) return _token;
  if (!_deviceId) _deviceId = randDevice();
  var url = c.apiBase + "/api/v1/auth/device";
  var body = {
    deviceId: "h5:" + _deviceId,
    channelCode: "",
    attributionToken: ""
  };
  var headers = {
    Accept: "application/json",
    "Content-Type": "application/json",
    "User-Agent": UA,
    Referer: c.apiBase + "/",
    Origin: c.apiBase
  };
  var res = null;
  var d = null;
  if (Widget.http.post) {
    try {
      res = await Widget.http.post(url, body, { headers: headers, timeout: HTTP_TIMEOUT });
      d = res && res.data;
    } catch (e) {}
  }
  if ((!d || !d.token) && Widget.http.request) {
    res = await Widget.http.request({
      url: url,
      method: "POST",
      headers: headers,
      body: JSON.stringify(body),
      timeout: HTTP_TIMEOUT
    });
    d = res && res.data;
  }
  if (typeof d === "string") {
    try { d = JSON.parse(d); } catch (e) {}
  }
  _token = t(d && d.token);
  if (!_token) throw new Error("设备登录失败");
  return _token;
}

async function apiGet(c, path, query, retry) {
  await ensureToken(c);
  var url = c.apiBase + "/api/v1" + path + qs(query || {});
  var headers = {
    Accept: "application/json",
    "User-Agent": UA,
    Referer: c.apiBase + "/",
    Origin: c.apiBase,
    Authorization: "Bearer " + _token
  };
  var res = await Widget.http.get(url, { headers: headers, timeout: HTTP_TIMEOUT });
  // 失败时 status === 0 且带 error；成功靠 ok / status 判定
  if (!res || !res.ok) {
    var code = res && res.status ? res.status : 0;
    throw new Error("请求失败(" + (code || "网络错误") + "): " + path);
  }
  var d = res.data;
  if (typeof d === "string") {
    try { d = JSON.parse(d); } catch (e) {}
  }
  if (d && d.status === 401 && !retry) {
    _token = "";
    return apiGet(c, path, query, true);
  }
  return d;
}

function pageSlice(arr, page) {
  page = Number(page || 1) || 1;
  if (!Array.isArray(arr)) return [];
  var start = (page - 1) * PAGE_SIZE;
  return arr.slice(start, start + PAGE_SIZE);
}

function toItem(c, it) {
  if (!it) return null;
  var id = t(it.id);
  if (!id) return null;
  var cover = absUrl(c.apiBase, it.coverUrl || it.cover || "");
  var ep = it.episodeCount || "";
  var remark = ep ? "全" + ep + "集" : "";
  var tags = Array.isArray(it.tags) ? it.tags.join(" · ") : "";
  if (tags) remark = remark ? remark + " · " + tags : tags;
  return {
    id: "jgdj:" + id,
    type: "url",
    title: t(it.title) || id,
    coverUrl: cover,
    posterPath: cover,
    backdropPath: cover,
    description: remark,
    mediaType: "tv",
    link: "jgdj:" + id,
    headers: { "User-Agent": UA, Referer: c.apiBase + "/" }
  };
}

function mapList(c, arr) {
  var out = [];
  for (var i = 0; i < (arr || []).length; i++) {
    var it = toItem(c, arr[i]);
    if (it) out.push(it);
  }
  return out;
}

/**
 * query:
 *  sort, navigationId, length
 *  _tagFilter: 本地 tags 精确匹配（服务端 tags 参数会 400）
 */
async function loadDramas(params, query) {
  params = params || {};
  var c = cfg(params);
  var page = normPage(params, "loadList");
  var q = Object.assign({ sort: "latest" }, query || {});
  var tagFilter = q._tagFilter || "";
  var cacheKey = "list:" + JSON.stringify(q) + ":" + page + ":" + c.apiBase;
  var cached = cacheGet(cacheKey);
  if (cached) return cached;
  delete q._tagFilter;
  var list = await apiGet(c, "/dramas", q);
  if (!Array.isArray(list)) list = [];
  if (tagFilter) {
    var filtered = [];
    for (var i = 0; i < list.length; i++) {
      var tags = list[i].tags || [];
      var hit = false;
      if (Array.isArray(tags)) {
        for (var j = 0; j < tags.length; j++) {
          if (String(tags[j]) === tagFilter) {
            hit = true;
            break;
          }
        }
      }
      if (hit) filtered.push(list[i]);
    }
    list = filtered;
  }
  var out = mapList(c, pageSlice(list, page));
  cacheSet(cacheKey, out, LIST_CACHE_TTL);
  return out;
}

async function loadHeat(params) {
  return loadDramas(params, { sort: "heat" });
}
async function loadLatest(params) {
  return loadDramas(params, { sort: "latest" });
}

async function loadLanding(params) {
  params = params || {};
  var c = cfg(params);
  var page = normPage(params, "loadLanding");
  var cacheKey = "list:landing:" + page + ":" + c.apiBase;
  var cached = cacheGet(cacheKey);
  if (cached) return cached;
  var data = await apiGet(c, "/landing");
  var list = (data && data.dramas) || [];
  var out = mapList(c, pageSlice(list, page));
  cacheSet(cacheKey, out, LIST_CACHE_TTL);
  return out;
}

// 官方剧场导航 navigationId（实测内容不同）
async function loadNavAll(params) {
  return loadDramas(params, { sort: "latest", navigationId: 2 });
}
async function loadNavOriginal(params) {
  return loadDramas(params, { sort: "latest", navigationId: 7 });
}
async function loadNavSingle(params) {
  return loadDramas(params, { sort: "latest", navigationId: 3 });
}
async function loadNavAnime(params) {
  return loadDramas(params, { sort: "latest", navigationId: 6 });
}
async function loadNavMovie(params) {
  return loadDramas(params, { sort: "latest", navigationId: 5 });
}

// 长度
async function loadLenMulti(params) {
  return loadDramas(params, { sort: "latest", length: "multi" });
}
async function loadLenSingle(params) {
  return loadDramas(params, { sort: "latest", length: "single" });
}

// 标签（本地过滤）
async function loadTagMogai(params) {
  return loadDramas(params, { sort: "latest", _tagFilter: "魔改" });
}
async function loadTagDushi(params) {
  return loadDramas(params, { sort: "latest", _tagFilter: "都市" });
}
async function loadTagZhichang(params) {
  return loadDramas(params, { sort: "latest", _tagFilter: "职场" });
}
async function loadTagQihuan(params) {
  return loadDramas(params, { sort: "latest", _tagFilter: "奇幻" });
}
async function loadTagGuzhuang(params) {
  return loadDramas(params, { sort: "latest", _tagFilter: "古装" });
}
async function loadTagDongman(params) {
  return loadDramas(params, { sort: "latest", _tagFilter: "动漫" });
}

async function search(params) {
  params = params || {};
  var c = cfg(params);
  // 宿主强制写入 keyword/query/wd/search 四个别名，任取其一
  var kw = t(
    params.keyword || params.query || params.wd || params.search || ""
  );
  if (!kw) return [];
  var page = normPage(params, "search");
  var cacheKey = "search:" + kw + ":" + page + ":" + c.apiBase;
  var cached = cacheGet(cacheKey);
  if (cached) return cached;
  var list = await apiGet(c, "/dramas", { sort: "latest", q: kw });
  if (!Array.isArray(list)) list = [];
  var out = mapList(c, pageSlice(list, page));
  cacheSet(cacheKey, out, SEARCH_CACHE_TTL);
  return out;
}

function parseLink(link) {
  var s = t(link).replace(/^jinguo:/, "jgdj:");
  if (s.indexOf("jgdj:") === 0) s = s.slice(5);
  var parts = s.split(":");
  return { id: t(parts[0]), ep: t(parts[1] || "") };
}

async function loadDetail(link, extraParams) {
  var p = parseLink(link);
  if (!p.id) throw new Error("loadDetail: link 不能为空");
  // extraParams 由宿主注入全局参数默认值（apiBase）
  var params = (extraParams && typeof extraParams === "object") ? extraParams : {};
  if (link && typeof link === "object") {
    params = Object.assign({}, link, params);
  }
  var c = cfg(params);

  var cacheKey = "detail:" + p.id + ":" + c.apiBase;
  var cached = cacheGet(cacheKey);
  if (cached) return cached;

  var data = await apiGet(c, "/dramas/" + encodeURIComponent(p.id));
  var drama = (data && data.drama) || {};
  var eps = (data && data.episodes) || [];
  var cover = absUrl(c.apiBase, drama.coverUrl || "");
  var ph = playHeaders(c);
  var episodeItems = [];
  for (var i = 0; i < eps.length; i++) {
    var ep = eps[i];
    var n = ep.number || i + 1;
    var epLink = "jgdj:" + p.id + ":" + n + ":" + t(ep.id);
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
  if (!episodeItems.length) {
    episodeItems.push({
      id: "jgdj:" + p.id + ":1",
      type: "url",
      title: "第1集",
      mediaType: "tv",
      seasonNumber: 1,
      episodeNumber: 1,
      link: "jgdj:" + p.id + ":1",
      videoUrl: "",
      headers: ph,
      playerType: "app"
    });
  }

  // 预取第一集播放地址，确保详情页有可播放链接（详情测试要求 videoUrl 非空）
  var videoUrl = "";
  try {
    var firstEpId = eps.length ? t(eps[0].id) : "";
    if (firstEpId) {
      var play = await apiGet(c, "/episodes/" + encodeURIComponent(firstEpId) + "/play");
      videoUrl = t((play && play.videoUrl) || "");
    }
  } catch (e) {}
  if (videoUrl && episodeItems.length) episodeItems[0].videoUrl = videoUrl;

  var tags = Array.isArray(drama.tags) ? drama.tags.join(" · ") : "";
  var result = {
    id: "jgdj:" + p.id,
    type: "url",
    title: t(drama.title || p.id),
    coverUrl: cover,
    posterPath: cover,
    backdropPath: cover,
    description: t(data.description || tags || ""),
    mediaType: "tv",
    link: "jgdj:" + p.id,
    videoUrl: videoUrl,
    episodeItems: episodeItems,
    headers: ph
  };
  cacheSet(cacheKey, result, DETAIL_CACHE_TTL);
  return result;
}

async function resolveEpisodeId(c, dramaId, epNum) {
  var data = await apiGet(c, "/dramas/" + encodeURIComponent(dramaId));
  var eps = (data && data.episodes) || [];
  for (var i = 0; i < eps.length; i++) {
    if (String(eps[i].number) === String(epNum) || String(eps[i].id) === String(epNum)) {
      return t(eps[i].id);
    }
  }
  return eps.length ? t(eps[0].id) : "";
}

async function loadResource(params) {
  params = params || {};
  var c = cfg(params);
  var raw = t(params.link || params.id || "");
  var s = raw.replace(/^jinguo:/, "jgdj:");
  if (s.indexOf("jgdj:") === 0) s = s.slice(5);
  var parts = s.split(":");
  var dramaId = t(parts[0]);
  var epNum = t(parts[1] || "1") || "1";
  var episodeId = t(parts[2] || "");
  if (!dramaId) return [];
  if (!episodeId) {
    episodeId = await resolveEpisodeId(c, dramaId, epNum);
  }
  if (!episodeId) return [];
  var play = await apiGet(c, "/episodes/" + encodeURIComponent(episodeId) + "/play");
  var url = t((play && play.videoUrl) || "");
  if (!url) return [];
  // 播放源条目使用原生契约字段 headers
  return [
    {
      name: "禁果",
      description: "第" + epNum + "集",
      url: url,
      headers: playHeaders(c),
      playerType: "app"
    }
  ];
}
