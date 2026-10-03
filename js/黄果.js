/**
 * 黄果 Streama Widget v1.5（原生契约）
 * API: https://huangguoai.com
 * 封面解密: https://huangguo.wulii.de5.net
 * 各分类独立模块，首页直接点选，无需在枚举里切换
 *
 * 按原生契约修订：
 * - 顶层 `var WidgetMetadata` 声明，列表模块显式 `type: "video"`、播放源 `type: "stream"`
 * - 媒体项 / 详情 / 剧集 / 播放源统一使用原生契约字段 `headers`（原 `customHeaders` 非标准）
 * - `loadDetail(link, extraParams)` 接收第二个参数，全局参数 apiBase/coverProxy/coverToken 在详情页生效；空链接抛带上下文短错误（不返回 null）
 * - `search` 兼容 keyword/query/wd/search 四别名，page 校验
 * - `Widget.http` 统一设置 timeout（毫秒）并按 ok/status 判定失败
 * - 列表 / 搜索 / 详情走 `Widget.storage` TTL 缓存（原生列表路径不消费 cacheDuration）
 * - 剧集项补 headers，播放请求带 UA/Referer
 */
var WidgetMetadata = {
  id: "streama.huangguoai",
  title: "黄果",
  version: "2.0.1",
  detailCacheDuration: 180,
  globalParams: [
    {
      name: "apiBase",
      title: "API 地址",
      type: "input",
      value: "https://huangguoai.com"
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
    { id: "hot", title: "热门", type: "video", functionName: "loadHot", cacheDuration: 300, params: [{ name: "page", title: "页码", type: "page", value: "1", startPage: 1 }] },
    { id: "new", title: "最新", type: "video", functionName: "loadNew", cacheDuration: 300, params: [{ name: "page", title: "页码", type: "page", value: "1", startPage: 1 }] },
    { id: "rank", title: "排行榜", type: "video", functionName: "loadRank", cacheDuration: 300, params: [{ name: "page", title: "页码", type: "page", value: "1", startPage: 1 }] },
    { id: "ai_huanlian", title: "AI换脸", type: "video", functionName: "loadAiHuanlian", cacheDuration: 300, params: [{ name: "page", title: "页码", type: "page", value: "1", startPage: 1 }] },
    { id: "ai_mogai", title: "AI魔改", type: "video", functionName: "loadAiMogai", cacheDuration: 300, params: [{ name: "page", title: "页码", type: "page", value: "1", startPage: 1 }] },
    { id: "duanju", title: "短剧", type: "video", functionName: "loadDuanju", cacheDuration: 300, params: [{ name: "page", title: "页码", type: "page", value: "1", startPage: 1 }] },
    { id: "manju", title: "漫剧", type: "video", functionName: "loadManju", cacheDuration: 300, params: [{ name: "page", title: "页码", type: "page", value: "1", startPage: 1 }] },
    { id: "dushi", title: "都市", type: "video", functionName: "loadDushi", cacheDuration: 300, params: [{ name: "page", title: "页码", type: "page", value: "1", startPage: 1 }] },
    { id: "xiandai", title: "现代", type: "video", functionName: "loadXiandai", cacheDuration: 300, params: [{ name: "page", title: "页码", type: "page", value: "1", startPage: 1 }] },
    { id: "xiaoyuan", title: "校园", type: "video", functionName: "loadXiaoyuan", cacheDuration: 300, params: [{ name: "page", title: "页码", type: "page", value: "1", startPage: 1 }] },
    { id: "xiangcun", title: "乡村", type: "video", functionName: "loadXiangcun", cacheDuration: 300, params: [{ name: "page", title: "页码", type: "page", value: "1", startPage: 1 }] },
    { id: "gufeng", title: "古风", type: "video", functionName: "loadGufeng", cacheDuration: 300, params: [{ name: "page", title: "页码", type: "page", value: "1", startPage: 1 }] },
    { id: "chuanyue", title: "穿越", type: "video", functionName: "loadChuanyue", cacheDuration: 300, params: [{ name: "page", title: "页码", type: "page", value: "1", startPage: 1 }] },
    { id: "chongsheng", title: "重生", type: "video", functionName: "loadChongsheng", cacheDuration: 300, params: [{ name: "page", title: "页码", type: "page", value: "1", startPage: 1 }] },
    { id: "xitong", title: "系统", type: "video", functionName: "loadXitong", cacheDuration: 300, params: [{ name: "page", title: "页码", type: "page", value: "1", startPage: 1 }] },
    { id: "xiuxian", title: "修仙", type: "video", functionName: "loadXiuxian", cacheDuration: 300, params: [{ name: "page", title: "页码", type: "page", value: "1", startPage: 1 }] },
    { id: "hougong", title: "后宫", type: "video", functionName: "loadHougong", cacheDuration: 300, params: [{ name: "page", title: "页码", type: "page", value: "1", startPage: 1 }] },
    { id: "zhuixu", title: "赘婿", type: "video", functionName: "loadZhuixu", cacheDuration: 300, params: [{ name: "page", title: "页码", type: "page", value: "1", startPage: 1 }] },
    { id: "nixi", title: "逆袭", type: "video", functionName: "loadNixi", cacheDuration: 300, params: [{ name: "page", title: "页码", type: "page", value: "1", startPage: 1 }] },
    { id: "bazong", title: "霸总", type: "video", functionName: "loadBazong", cacheDuration: 300, params: [{ name: "page", title: "页码", type: "page", value: "1", startPage: 1 }] },
    { id: "haomen", title: "豪门", type: "video", functionName: "loadHaomen", cacheDuration: 300, params: [{ name: "page", title: "页码", type: "page", value: "1", startPage: 1 }] },
    { id: "tianchong", title: "甜宠", type: "video", functionName: "loadTianchong", cacheDuration: 300, params: [{ name: "page", title: "页码", type: "page", value: "1", startPage: 1 }] },
    { id: "nuelian", title: "虐恋", type: "video", functionName: "loadNuelian", cacheDuration: 300, params: [{ name: "page", title: "页码", type: "page", value: "1", startPage: 1 }] },
    { id: "shunv", title: "熟女", type: "video", functionName: "loadShunv", cacheDuration: 300, params: [{ name: "page", title: "页码", type: "page", value: "1", startPage: 1 }] },
    { id: "luanlun", title: "乱伦", type: "video", functionName: "loadLuanlun", cacheDuration: 300, params: [{ name: "page", title: "页码", type: "page", value: "1", startPage: 1 }] },
    { id: "muzi", title: "母子", type: "video", functionName: "loadMuzi", cacheDuration: 300, params: [{ name: "page", title: "页码", type: "page", value: "1", startPage: 1 }] },
    { id: "renqi", title: "人妻", type: "video", functionName: "loadRenqi", cacheDuration: 300, params: [{ name: "page", title: "页码", type: "page", value: "1", startPage: 1 }] },
    { id: "juru", title: "巨乳", type: "video", functionName: "loadJuru", cacheDuration: 300, params: [{ name: "page", title: "页码", type: "page", value: "1", startPage: 1 }] },
    { id: "heisi", title: "黑丝", type: "video", functionName: "loadHeisi", cacheDuration: 300, params: [{ name: "page", title: "页码", type: "page", value: "1", startPage: 1 }] },
    { id: "bangongshi", title: "办公室", type: "video", functionName: "loadBangongshi", cacheDuration: 300, params: [{ name: "page", title: "页码", type: "page", value: "1", startPage: 1 }] },
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
    apiBase: t(params.apiBase || "https://huangguoai.com").replace(/\/+$/, ""),
    coverProxy: t(params.coverProxy || "https://huangguo.wulii.de5.net").replace(
      /\/+$/,
      ""
    ),
    coverToken: t(params.coverToken || "hg8f3a2c91b7e04d6a")
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
    if (obj[k] == null || obj[k] === "") return;
    parts.push(encodeURIComponent(k) + "=" + encodeURIComponent(String(obj[k])));
  });
  return parts.length ? "?" + parts.join("&") : "";
}

/* 请求头构造（函数名避开媒体项字段名 headers） */
function reqHeaders(base) {
  return {
    Accept: "application/json, text/plain, */*",
    "User-Agent": UA,
    Referer: (base || "https://huangguoai.com") + "/"
  };
}

async function httpJson(url, base) {
  var res = await Widget.http.get(url, {
    headers: reqHeaders(base),
    timeout: HTTP_TIMEOUT
  });
  // 失败时 status === 0 且带 error；成功靠 ok / status 判定
  if (!res || !res.ok) {
    var code = res && res.status ? res.status : 0;
    throw new Error("请求失败(" + (code || "网络错误") + ")");
  }
  var d = res.data;
  if (typeof d === "string") {
    try { d = JSON.parse(d); } catch (e) {}
  }
  return d;
}

function absCover(base, cover) {
  cover = t(cover);
  if (!cover) return "";
  if (/^https?:\/\//i.test(cover)) return cover;
  if (cover.indexOf("//") === 0) return "https:" + cover;
  return base + (cover[0] === "/" ? "" : "/") + cover;
}

function proxiedCover(c, encUrl) {
  encUrl = t(encUrl);
  if (!encUrl) return "";
  // 封面 CDN 为 AES 密文，必须走解密代理，否则 App 无法显示
  if (!c.coverProxy) return encUrl;
  var base = c.coverProxy.replace(/\/+$/, "");
  var q = { url: encUrl };
  if (c.coverToken) q.token = c.coverToken;
  return base + "/" + qs(q); // https://host/?url=...&token=...
}

/* 播放请求头：播放器需要 UA/Referer */
function playHeaders(base) {
  return {
    "User-Agent": UA,
    Referer: (base || "https://huangguoai.com") + "/"
  };
}

function toItem(c, it) {
  if (!it) return null;
  var id = t(
    it.id != null ? it.id : it.video_id != null ? it.video_id : it.vod_id
  );
  if (!id) return null;
  var title = t(it.title || it.vod_name || it.name);
  var enc = absCover(c.apiBase, it.cover || it.vod_pic || it.pic || "");
  var cover = proxiedCover(c, enc);
  var ep = it.episode_count || it.total_episodes || "";
  var remark = "";
  if (it.is_finished) remark = "全" + (ep || "") + "集";
  else if (ep) remark = "更新至" + ep + "集";
  return {
    id: "hgai:" + id,
    type: "url",
    title: title || id,
    coverUrl: cover,
    posterPath: cover,
    backdropPath: cover,
    description: remark,
    mediaType: "tv",
    link: "hgai:" + id,
    headers: reqHeaders(c.apiBase)
  };
}

function extractItems(data) {
  if (!data) return [];
  var d = data.data != null ? data.data : data;
  if (Array.isArray(d)) return d;
  if (Array.isArray(d.items)) return d.items;
  if (Array.isArray(d.list)) return d.list;
  if (Array.isArray(d.results)) return d.results;
  return [];
}

async function fetchBySearch(c, keyword, page, strictTag) {
  keyword = t(keyword);
  page = Number(page || 1) || 1;
  var collected = [];
  var seen = {};
  var maxPage = strictTag ? page + 2 : page;
  for (var p = page; p <= maxPage; p++) {
    var data = await httpJson(
      c.apiBase + "/api/search" + qs({ q: keyword, page: p }),
      c.apiBase
    );
    var batch = extractItems(data);
    if (!batch.length) break;
    for (var i = 0; i < batch.length; i++) {
      var it = batch[i];
      var id = t(it.id != null ? it.id : it.video_id);
      if (!id || seen[id]) continue;
      if (strictTag) {
        var tags = it.tags || [];
        var hit = false;
        if (Array.isArray(tags)) {
          for (var j = 0; j < tags.length; j++) {
            if (String(tags[j]) === keyword) {
              hit = true;
              break;
            }
          }
        }
        var title = t(it.title || "");
        if (!hit && title.indexOf(keyword) === 0) hit = true;
        if (!hit) continue;
      }
      seen[id] = 1;
      collected.push(it);
    }
    if (collected.length >= 24) break;
  }
  return collected.slice(0, 24);
}

async function fetchList(c, tid, page) {
  page = Number(page || 1) || 1;
  tid = t(tid) || "hot";
  var items = [];

  if (tid === "rank" || tid === "ranks") {
    try {
      var rank = await httpJson(
        c.apiBase + "/api/ranks/hot" + qs({ page: page }),
        c.apiBase
      );
      items = extractItems(rank);
    } catch (e) {}
  }

  if (!items.length && (tid.indexOf("kw:") === 0 || tid.indexOf("tag:") === 0)) {
    var kw = tid.indexOf("kw:") === 0 ? tid.slice(3) : tid.slice(4);
    items = await fetchBySearch(c, kw, page, true);
  }

  if (!items.length && tid !== "hot" && tid !== "new" && tid !== "rank") {
    var q = tid;
    if (q && q !== "hot" && q !== "new") {
      items = await fetchBySearch(c, q, page, true);
    }
  }

  if (!items.length) {
    var sort = tid === "new" ? "new" : "hot";
    var data = await httpJson(
      c.apiBase + "/api/videos" + qs({ page: page, page_size: 24, sort: sort }),
      c.apiBase
    );
    items = extractItems(data);
  }

  var out = [];
  for (var i = 0; i < items.length; i++) {
    var item = toItem(c, items[i]);
    if (item) out.push(item);
  }
  return out;
}

async function loadByTid(params, tid) {
  params = params || {};
  var c = cfg(params);
  var page = normPage(params, "loadList");
  var cacheKey = "list:" + tid + ":" + page + ":" + c.apiBase;
  var cached = cacheGet(cacheKey);
  if (cached) return cached;
  var list = await fetchList(c, tid, page);
  cacheSet(cacheKey, list, LIST_CACHE_TTL);
  return list;
}

async function loadHot(params) { return loadByTid(params, "hot"); }
async function loadNew(params) { return loadByTid(params, "new"); }
async function loadRank(params) { return loadByTid(params, "rank"); }
async function loadAiHuanlian(params) { return loadByTid(params, "kw:AI换脸"); }
async function loadAiMogai(params) { return loadByTid(params, "kw:AI魔改"); }
async function loadDuanju(params) { return loadByTid(params, "kw:短剧"); }
async function loadManju(params) { return loadByTid(params, "kw:漫剧"); }
async function loadDushi(params) { return loadByTid(params, "kw:都市"); }
async function loadXiandai(params) { return loadByTid(params, "kw:现代"); }
async function loadXiaoyuan(params) { return loadByTid(params, "kw:校园"); }
async function loadXiangcun(params) { return loadByTid(params, "kw:乡村"); }
async function loadGufeng(params) { return loadByTid(params, "kw:古风"); }
async function loadChuanyue(params) { return loadByTid(params, "kw:穿越"); }
async function loadChongsheng(params) { return loadByTid(params, "kw:重生"); }
async function loadXitong(params) { return loadByTid(params, "kw:系统"); }
async function loadXiuxian(params) { return loadByTid(params, "kw:修仙"); }
async function loadHougong(params) { return loadByTid(params, "kw:后宫"); }
async function loadZhuixu(params) { return loadByTid(params, "kw:赘婿"); }
async function loadNixi(params) { return loadByTid(params, "kw:逆袭"); }
async function loadBazong(params) { return loadByTid(params, "kw:霸总"); }
async function loadHaomen(params) { return loadByTid(params, "kw:豪门"); }
async function loadTianchong(params) { return loadByTid(params, "kw:甜宠"); }
async function loadNuelian(params) { return loadByTid(params, "kw:虐恋"); }
async function loadShunv(params) { return loadByTid(params, "kw:熟女"); }
async function loadLuanlun(params) { return loadByTid(params, "kw:乱伦"); }
async function loadMuzi(params) { return loadByTid(params, "kw:母子"); }
async function loadRenqi(params) { return loadByTid(params, "kw:人妻"); }
async function loadJuru(params) { return loadByTid(params, "kw:巨乳"); }
async function loadHeisi(params) { return loadByTid(params, "kw:黑丝"); }
async function loadBangongshi(params) { return loadByTid(params, "kw:办公室"); }

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
  var items = await fetchBySearch(c, kw, page, false);
  var out = [];
  for (var i = 0; i < items.length; i++) {
    var item = toItem(c, items[i]);
    if (item) out.push(item);
  }
  cacheSet(cacheKey, out, SEARCH_CACHE_TTL);
  return out;
}

function parseLink(link) {
  var s = t(link).replace(/^huangguoai:/, "hgai:");
  if (s.indexOf("hgai:") === 0) s = s.slice(5);
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

  var cacheKey = "detail:" + p.id + ":" + c.apiBase;
  var cached = cacheGet(cacheKey);
  if (cached) return cached;

  var data = await httpJson(
    c.apiBase + "/api/videos/" + encodeURIComponent(p.id),
    c.apiBase
  );
  var d = (data && data.data) || {};
  var enc = absCover(c.apiBase, d.cover || "");
  var cover = proxiedCover(c, enc);
  var ph = playHeaders(c.apiBase);
  var eps = Array.isArray(d.episodes) ? d.episodes : [];
  var episodeItems = [];
  if (eps.length) {
    for (var i = 0; i < eps.length; i++) {
      var ep = eps[i];
      var n = ep.ep_num || ep.episode || i + 1;
      var epLink = "hgai:" + p.id + ":" + n;
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
      id: "hgai:" + p.id + ":1",
      type: "url",
      title: "第1集",
      mediaType: "tv",
      seasonNumber: 1,
      episodeNumber: 1,
      link: "hgai:" + p.id + ":1",
      videoUrl: "",
      headers: ph,
      playerType: "app"
    });
  }
  // 预取第一集播放地址，确保详情页有可播放链接（详情测试要求 videoUrl 非空）
  var firstEpNo = episodeItems.length ? (episodeItems[0].episodeNumber || 1) : 1;
  var videoUrl = "";
  try {
    var playData = await httpJson(
      c.apiBase + "/api/videos/" + encodeURIComponent(p.id) + "/play" + qs({ ep: String(firstEpNo) }),
      c.apiBase
    );
    videoUrl = t(
      (playData && playData.data && playData.data.video_url) ||
        (playData && playData.video_url) || ""
    );
  } catch (e) {}
  if (videoUrl && episodeItems.length) episodeItems[0].videoUrl = videoUrl;

  var result = {
    id: "hgai:" + p.id,
    type: "url",
    title: t(d.title || p.id),
    coverUrl: cover,
    posterPath: cover,
    backdropPath: cover,
    description: t(d.description || ""),
    mediaType: "tv",
    link: "hgai:" + p.id,
    videoUrl: videoUrl,
    episodeItems: episodeItems,
    headers: ph
  };
  cacheSet(cacheKey, result, DETAIL_CACHE_TTL);
  return result;
}

async function loadResource(params) {
  params = params || {};
  var c = cfg(params);
  var p = parseLink(t(params.link || params.id || ""));
  if (!p.id) return [];
  var ep = p.ep || t(params.episode) || "1";
  var data = await httpJson(
    c.apiBase +
      "/api/videos/" +
      encodeURIComponent(p.id) +
      "/play" +
      qs({ ep: ep }),
    c.apiBase
  );
  var url = t(
    (data && data.data && data.data.video_url) ||
      (data && data.video_url) ||
      ""
  );
  if (!url) return [];
  // 播放源条目使用原生契约字段 headers
  return [
    {
      name: "黄果",
      description: "第" + ep + "集",
      url: url,
      headers: playHeaders(c.apiBase),
      playerType: "app"
    }
  ];
}
