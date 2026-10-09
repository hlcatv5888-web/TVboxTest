# coding=utf-8
"""
目标站: 点众短剧 (www.rainbowmetalwork.com)
动态分类、精准播放解析
"""
import re
import sys
import json
import urllib.parse
from bs4 import BeautifulSoup

sys.path.append('..')
from base.spider import Spider


class Spider(Spider):
    def init(self, extend=""):
        self.site_url = "https://www.rainbowmetalwork.com"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': self.site_url,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        # 动态获取分类（从导航栏解析）
        self.categories = self._fetch_categories()

    def _fetch_categories(self):
        """从首页导航栏解析分类标签"""
        try:
            resp = self.fetch(self.site_url, headers=self.headers)
            if not resp:
                return self._default_categories()
            soup = BeautifulSoup(resp.text, 'html.parser')
            # 导航菜单：ul.stui-header__menu li a (排除首页)
            nav_links = soup.select('ul.stui-header__menu li a')
            categories = []
            seen = set()
            for a in nav_links:
                href = a.get('href', '')
                name = a.get_text(strip=True)
                if name == '首页' or not href:
                    continue
                # 匹配多种分类URL格式
                match = re.search(r'/dztp/(\d+)\.html', href)
                if not match:
                    match = re.search(r'/dzsw/(\d+)-+\.html', href)
                if not match:
                    match = re.search(r'/dzsw/(\d+)\.html', href)
                if not match:
                    continue
                tid = match.group(1)
                if tid in seen:
                    continue
                seen.add(tid)
                categories.append({"type_id": tid, "type_name": name})
            if categories:
                return categories
        except Exception as e:
            print(f"[点众] 获取分类失败: {e}")
        return self._default_categories()

    def _default_categories(self):
        return [
            {"type_id": "5", "type_name": "短剧"},
            {"type_id": "1", "type_name": "女频恋爱"},
            {"type_id": "2", "type_name": "反转爽"},
            {"type_id": "3", "type_name": "脑洞悬疑"},
            {"type_id": "4", "type_name": "年代穿越"},
            {"type_id": "6", "type_name": "古装仙侠"},
            {"type_id": "7", "type_name": "现代都市"}
        ]

    def _parse_video_item(self, item):
        """解析单个视频条目"""
        link = item.select_one('a.stui-vodlist__thumb')
        if not link:
            return None
        
        href = link.get('href', '')
        vod_id = re.search(r'/(\d+)\.html', href)
        if not vod_id:
            return None
        vod_id = vod_id.group(1)
        
        # 获取标题
        title = link.get('title', '') or link.get('alt', '')
        if not title:
            title_elem = item.select_one('.stui-vodlist__detail h4 a')
            if title_elem:
                title = title_elem.get('title', '') or title_elem.get_text(strip=True)
        if not title:
            return None
        
        # 获取封面
        pic = link.get('data-original', '')
        if not pic:
            style = link.get('style', '')
            bg_match = re.search(r'url\(([^)]+)\)', style)
            if bg_match:
                pic = bg_match.group(1).strip('"\'')
        if pic and not pic.startswith('http'):
            pic = 'https:' + pic if pic.startswith('//') else self.site_url + pic
        
        # 获取备注（已完结/全集等）
        remark = ''
        remark_elem = item.select_one('.pic-text')
        if remark_elem:
            remark = remark_elem.get_text(strip=True)
        
        return {
            "vod_id": vod_id,
            "vod_name": title,
            "vod_pic": pic,
            "vod_remarks": remark
        }

    # ================= 首页推荐 =================
    def homeContent(self, filter):
        url = self.site_url + "/"
        resp = self.fetch(url, headers=self.headers)
        video_list = []
        if resp:
            soup = BeautifulSoup(resp.text, 'html.parser')
            # 首页所有视频卡片
            items = soup.select('ul.stui-vodlist li')
            for item in items:
                video = self._parse_video_item(item)
                if video:
                    video_list.append(video)
                if len(video_list) >= 40:
                    break
        return {"class": self.categories, "list": video_list, "filters": {}}

    def homeVideoContent(self):
        return self.homeContent(False)

    # ================= 分类列表 =================
    def categoryContent(self, tid, pg, filter, extend):
        page = int(pg) if pg else 1
        # 尝试多种URL格式
        urls_to_try = [
            f"{self.site_url}/dztp/{tid}.html",
            f"{self.site_url}/dzsw/{tid}-----------.html",
            f"{self.site_url}/dzsw/{tid}.html"
        ]
        
        resp = None
        for url in urls_to_try:
            if page > 1:
                test_url = f"{url}?page={page}"
                resp = self.fetch(test_url, headers=self.headers)
                if resp:
                    break
                test_url = f"{url}-{page}.html"
                resp = self.fetch(test_url, headers=self.headers)
                if resp:
                    break
            else:
                resp = self.fetch(url, headers=self.headers)
                if resp:
                    break
        
        if not resp:
            return {"list": [], "page": page, "pagecount": 1, "limit": 24, "total": 0}

        soup = BeautifulSoup(resp.text, 'html.parser')
        video_list = []
        items = soup.select('ul.stui-vodlist li')
        if not items:
            items = soup.select('.stui-vodlist li')
        
        for item in items:
            video = self._parse_video_item(item)
            if video:
                video_list.append(video)
        
        # 分页信息
        pagecount = page
        pagination = soup.select('.stui-page a')
        if pagination:
            for a in pagination:
                text = a.get_text(strip=True)
                if text.isdigit():
                    pagecount = max(pagecount, int(text))
        
        return {
            "list": video_list,
            "page": page,
            "pagecount": pagecount,
            "limit": 24,
            "total": len(video_list) * pagecount
        }

    # ================= 详情页 =================
    def detailContent(self, ids):
        if not ids:
            return {"list": []}
        vod_id = ids[0]
        url = f"{self.site_url}/dzdt/{vod_id}.html"
        resp = self.fetch(url, headers=self.headers)
        if not resp:
            return {"list": []}

        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # 标题
        title_elem = soup.select_one('.stui-content__title h1') or soup.select_one('h1')
        vod_name = title_elem.get_text(strip=True) if title_elem else vod_id
        
        # 封面
        vod_pic = ''
        img_elem = soup.select_one('.stui-content__thumb img')
        if img_elem:
            vod_pic = img_elem.get('data-original', '') or img_elem.get('src', '')
            if vod_pic and not vod_pic.startswith('http'):
                vod_pic = 'https:' + vod_pic if vod_pic.startswith('//') else self.site_url + vod_pic
        
        # 简介
        vod_content = ''
        content_elem = soup.select_one('.stui-content__desc') or soup.select_one('.stui-content__detail .desc')
        if content_elem:
            vod_content = content_elem.get_text(' ', strip=True)
        
        # 演员
        vod_actor = ''
        actor_elems = soup.select('.stui-content__detail .data a[rel="nofollow"]')
        if actor_elems:
            vod_actor = ','.join([a.get_text(strip=True) for a in actor_elems])
        
        # 年份
        vod_year = ''
        year_elem = soup.select_one('.stui-content__detail .data:contains("年份")')
        if year_elem:
            year_match = re.search(r'(\d{4})', year_elem.get_text())
            if year_match:
                vod_year = year_match.group(1)
        
        # ===== 播放链接解析 =====
        play_from_list = []
        play_url_list = []
        
        # 方法1: 查找播放列表块
        playlist_selectors = [
            '.stui-play__list',
            '.stui-content__playlist',
            '.playlist',
            '.play-source',
            '.source-list',
            '.episode-list',
            '.video-playlist'
        ]
        
        for selector in playlist_selectors:
            blocks = soup.select(selector)
            for block in blocks:
                line_name = self._extract_line_name(block)
                episodes = self._extract_episodes(block)
                if episodes:
                    play_from_list.append(line_name)
                    play_url_list.append('#'.join(episodes))
        
        # 方法2: 查找"查看全部"链接
        if not play_url_list:
            view_all = soup.select_one('a[href*="playlist"], a[href*="list"], a:contains("查看全部")')
            if view_all:
                href = view_all.get('href', '')
                if href:
                    if not href.startswith('http'):
                        href = self.site_url + href if href.startswith('/') else self.site_url + '/' + href
                    all_resp = self.fetch(href, headers=self.headers)
                    if all_resp:
                        all_soup = BeautifulSoup(all_resp.text, 'html.parser')
                        all_links = all_soup.select('a[href*="/play/"], a[href*="/dzdt/"]')
                        episodes = []
                        for a in all_links:
                            a_href = a.get('href', '')
                            if a_href and '/play/' in a_href:
                                ep_name = a.get_text(strip=True) or f"第{len(episodes)+1}集"
                                if not a_href.startswith('http'):
                                    a_href = self.site_url + a_href if a_href.startswith('/') else self.site_url + '/' + a_href
                                episodes.append(f"{ep_name}${a_href}")
                        if episodes:
                            play_from_list.append("线路1")
                            play_url_list.append('#'.join(episodes))
        
        # 方法3: 查找所有播放链接
        if not play_url_list:
            play_links = soup.select('a[href*="/play/"]')
            if play_links:
                episodes = []
                for a in play_links:
                    href = a.get('href', '')
                    ep_name = a.get_text(strip=True) or f"第{len(episodes)+1}集"
                    if not href.startswith('http'):
                        href = self.site_url + href if href.startswith('/') else self.site_url + '/' + href
                    episodes.append(f"{ep_name}${href}")
                if episodes:
                    play_from_list.append('默认线路')
                    play_url_list.append('#'.join(episodes))
        
        # 方法4: 从JavaScript中提取
        if not play_url_list:
            scripts = soup.select('script')
            for script in scripts:
                content = script.get_text() if script else ''
                # 匹配播放列表数据
                match = re.search(r'var\s+playlist\s*=\s*(\[[^\]]+\])', content)
                if match:
                    try:
                        data = json.loads(match.group(1))
                        episodes = []
                        for item in data:
                            if isinstance(item, dict):
                                name = item.get('name', '')
                                url = item.get('url', '')
                                if url:
                                    episodes.append(f"{name}${url}")
                        if episodes:
                            play_from_list.append('默认线路')
                            play_url_list.append('#'.join(episodes))
                    except:
                        pass

        vod_play_from = '$$$'.join(play_from_list) if play_from_list else '默认源'
        vod_play_url = '$$$'.join(play_url_list) if play_url_list else f"播放${vod_id}"

        result = [{
            "vod_id": vod_id,
            "vod_name": vod_name,
            "vod_pic": vod_pic,
            "vod_content": vod_content,
            "vod_actor": vod_actor,
            "vod_director": "",
            "vod_area": "",
            "vod_year": vod_year,
            "vod_play_from": vod_play_from,
            "vod_play_url": vod_play_url
        }]
        return {"list": result}

    def _extract_line_name(self, block):
        """提取线路名称"""
        name_elem = block.select_one('.stui-play__list-title, .play-title, .source-title, .line-name, .title')
        if name_elem:
            return name_elem.get_text(strip=True)
        # 检查父元素
        parent = block.parent
        if parent:
            name_elem = parent.select_one('.stui-play__list-title, .play-title')
            if name_elem:
                return name_elem.get_text(strip=True)
        return "线路1"

    def _extract_episodes(self, block):
        """提取剧集列表"""
        episodes = []
        for a in block.select('a'):
            href = a.get('href', '')
            if not href or 'javascript:' in href or href == '#':
                continue
            ep_name = a.get_text(strip=True)
            if not ep_name:
                # 尝试从href中提取
                ep_match = re.search(r'[-/](\d+)\.html', href)
                if ep_match:
                    ep_name = f"第{ep_match.group(1)}集"
                else:
                    ep_name = f"第{len(episodes)+1}集"
            if not href.startswith('http'):
                href = self.site_url + href if href.startswith('/') else self.site_url + '/' + href
            episodes.append(f"{ep_name}${href}")
        return episodes

    # ================= 搜索 =================
    def searchContent(self, key, quick, pg="1"):
        page = int(pg) if pg else 1
        encoded_key = urllib.parse.quote(key)
        url = f"{self.site_url}/search.php?searchword={encoded_key}"
        if page > 1:
            url += f"&page={page}"
        resp = self.fetch(url, headers=self.headers)
        if not resp:
            return {"list": [], "page": page, "pagecount": 1}
        
        soup = BeautifulSoup(resp.text, 'html.parser')
        video_list = []
        items = soup.select('ul.stui-vodlist li')
        for item in items:
            video = self._parse_video_item(item)
            if video:
                video_list.append(video)
        
        # 分页
        pagecount = page
        pagination = soup.select('.stui-page a')
        if pagination:
            for a in pagination:
                text = a.get_text(strip=True)
                if text.isdigit():
                    pagecount = max(pagecount, int(text))
        
        return {"list": video_list, "page": page, "pagecount": pagecount}

    # ================= 播放解析 =================
    def playerContent(self, flag, id, vipFlags):
        """解析播放地址"""
        # 构建完整URL
        if not id.startswith('http'):
            if id.startswith('/'):
                play_url = self.site_url + id
            else:
                play_url = f"{self.site_url}/dzdt/{id}.html"
        else:
            play_url = id

        # 获取页面内容
        resp = self.fetch(play_url, headers=self.headers)
        if not resp:
            return {"parse": 1, "url": play_url, "header": self.headers}

        html = resp.text
        soup = BeautifulSoup(html, 'html.parser')

        # ===== 方法1: 查找iframe =====
        iframe = soup.select_one('iframe')
        if iframe:
            src = iframe.get('src', '')
            if src:
                if not src.startswith('http'):
                    src = self.site_url + src if src.startswith('/') else self.site_url + '/' + src
                result = self._parse_iframe(src)
                if result.get('url') and result.get('parse') == 0:
                    return result

        # ===== 方法2: 查找video标签 =====
        video = soup.select_one('video')
        if video:
            src = video.get('src', '')
            if src:
                return {"parse": 0, "url": src, "header": self.headers}
            # 检查source子标签
            source = video.select_one('source')
            if source:
                src = source.get('src', '')
                if src:
                    return {"parse": 0, "url": src, "header": self.headers}

        # ===== 方法3: 从script中提取 =====
        scripts = soup.select('script')
        for script in scripts:
            content = script.get_text() if script else ''
            
            # 匹配各种播放器变量
            patterns = [
                r'var\s+player_aaaa\s*=\s*({[^;]+})',
                r'var\s+config\s*=\s*({[^;]+})',
                r'var\s+video\s*=\s*["\']([^"\']+)["\']',
                r'var\s+url\s*=\s*["\']([^"\']+)["\']',
                r'"url"\s*:\s*["\']([^"\']+)["\']',
                r'"video_url"\s*:\s*["\']([^"\']+)["\']',
                r'"src"\s*:\s*["\']([^"\']+)["\']',
                r'"source"\s*:\s*["\']([^"\']+)["\']',
                r'playUrl\s*[:=]\s*["\']([^"\']+)["\']',
                r'videoUrl\s*[:=]\s*["\']([^"\']+)["\']'
            ]
            
            for pattern in patterns:
                match = re.search(pattern, content)
                if match:
                    try:
                        data_str = match.group(1)
                        if data_str.startswith('{'):
                            data = json.loads(data_str)
                            if isinstance(data, dict):
                                for key in ['url', 'src', 'video_url', 'source', 'playUrl', 'videoUrl']:
                                    if data.get(key):
                                        video_url = data[key]
                                        if video_url.startswith('http'):
                                            return {"parse": 0, "url": video_url, "header": self.headers}
                        else:
                            video_url = data_str
                            if video_url.startswith('http'):
                                return {"parse": 0, "url": video_url, "header": self.headers}
                    except:
                        pass

        # ===== 方法4: 直接匹配视频地址 =====
        # m3u8
        m3u8 = re.search(r'(https?://[^\s"\']+\.m3u8[^\s"\']*)', html)
        if m3u8:
            return {"parse": 0, "url": m3u8.group(1), "header": self.headers}
        
        # mp4
        mp4 = re.search(r'(https?://[^\s"\']+\.mp4[^\s"\']*)', html)
        if mp4:
            return {"parse": 0, "url": mp4.group(1), "header": self.headers}
        
        # flv
        flv = re.search(r'(https?://[^\s"\']+\.flv[^\s"\']*)', html)
        if flv:
            return {"parse": 0, "url": flv.group(1), "header": self.headers}

        # ===== 方法5: 从接口获取 =====
        api_match = re.search(r'(/api/[^\s"\']+\.(?:php|json)[^\s"\']*)', html)
        if api_match:
            api_url = self.site_url + api_match.group(0)
            api_resp = self.fetch(api_url, headers=self.headers)
            if api_resp:
                try:
                    data = json.loads(api_resp.text)
                    if isinstance(data, dict):
                        for key in ['url', 'src', 'video_url', 'data']:
                            if data.get(key):
                                video_url = data[key]
                                if isinstance(video_url, str) and video_url.startswith('http'):
                                    return {"parse": 0, "url": video_url, "header": self.headers}
                except:
                    pass

        # ===== 方法6: 使用外部解析器 =====
        return {"parse": 1, "url": play_url, "header": self.headers}

    def _parse_iframe(self, iframe_url):
        """递归解析iframe中的视频地址"""
        resp = self.fetch(iframe_url, headers=self.headers)
        if not resp:
            return {"parse": 1, "url": iframe_url, "header": self.headers}
        
        html = resp.text
        soup = BeautifulSoup(html, 'html.parser')

        # 查找video
        video = soup.select_one('video')
        if video:
            src = video.get('src', '')
            if src:
                return {"parse": 0, "url": src, "header": self.headers}
            source = video.select_one('source')
            if source:
                src = source.get('src', '')
                if src:
                    return {"parse": 0, "url": src, "header": self.headers}

        # 查找iframe嵌套
        iframe = soup.select_one('iframe')
        if iframe:
            src = iframe.get('src', '')
            if src:
                if not src.startswith('http'):
                    src = self.site_url + src if src.startswith('/') else self.site_url + '/' + src
                return self._parse_iframe(src)

        # 查找播放器脚本
        scripts = soup.select('script')
        for script in scripts:
            content = script.get_text() if script else ''
            patterns = [
                r'var\s+player_aaaa\s*=\s*({[^;]+})',
                r'"url"\s*:\s*["\']([^"\']+)["\']',
                r'"src"\s*:\s*["\']([^"\']+)["\']',
                r'video\s*[:=]\s*["\']([^"\']+)["\']'
            ]
            for pattern in patterns:
                match = re.search(pattern, content)
                if match:
                    try:
                        data_str = match.group(1)
                        if data_str.startswith('{'):
                            data = json.loads(data_str)
                            if isinstance(data, dict):
                                for key in ['url', 'src', 'video_url', 'source']:
                                    if data.get(key):
                                        video_url = data[key]
                                        if video_url.startswith('http'):
                                            return {"parse": 0, "url": video_url, "header": self.headers}
                        else:
                            video_url = data_str
                            if video_url.startswith('http'):
                                return {"parse": 0, "url": video_url, "header": self.headers}
                    except:
                        pass

        # 直接匹配
        m3u8 = re.search(r'(https?://[^\s"\']+\.m3u8[^\s"\']*)', html)
        if m3u8:
            return {"parse": 0, "url": m3u8.group(1), "header": self.headers}
        
        mp4 = re.search(r'(https?://[^\s"\']+\.mp4[^\s"\']*)', html)
        if mp4:
            return {"parse": 0, "url": mp4.group(1), "header": self.headers}

        return {"parse": 1, "url": iframe_url, "header": self.headers}