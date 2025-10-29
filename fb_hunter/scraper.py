import os, time, socket
from typing import List, Dict, Any, Optional, Callable
from ddgs import DDGS
from urllib.error import URLError
import requests
from playwright.sync_api import sync_playwright
from .config import ProxyConfig
from .extractors import extract_from_html, normalize_fb_url, analyze_website, is_profile_or_page, extract_poster_url_from_post
from .cache_store import FileCache

class Scraper:
    def __init__(self, proxy: ProxyConfig, wait_time: int = 8, logger: Optional[Callable[[str],None]] = None):
        self.proxy = proxy
        self.wait_time = wait_time
        self.log = logger or (lambda s: None)
        self.search_cache = FileCache("ddgs")
        self.html_cache = FileCache("html")

    def ddgs_search_one(self, keyword: str, max_results: int) -> List[str]:
        cache_key = f"ddgs::{keyword}::{max_results}"
        cached = self.search_cache.get(cache_key)
        if cached:
            return cached.decode("utf-8").split("\n") if cached else []

        if self.proxy.server():
            os.environ["HTTP_PROXY"] = self.proxy.server()
            os.environ["HTTPS_PROXY"] = self.proxy.server()
        else:
            os.environ.pop("HTTP_PROXY", None); os.environ.pop("HTTPS_PROXY", None)

        urls: List[str] = []
        for attempt in range(1,4):
            try:
                with DDGS() as ddgs:
                    results = ddgs.text(f"site:facebook.com {keyword}", max_results=max_results, region="us-en", safesearch="Off")
                    for r in results:
                        href = r.get("href")
                        if not href or "facebook.com" not in href: continue
                        u = normalize_fb_url(href)
                        if not is_profile_or_page(u):
                            alt = extract_poster_url_from_post(u)
                            if alt and is_profile_or_page(alt):
                                u = alt
                            else:
                                continue
                        urls.append(u)
                if urls:
                    break
                else:
                    self.log(f"[警告] {keyword} 无搜索结果 (DuckDuckGo 返回空)"); break
            except (requests.exceptions.ProxyError, URLError) as e:
                self.log(f"[搜索异常] 第 {attempt} 次: {keyword}\n    原因: 代理错误 ({e})")
            except (requests.exceptions.Timeout, socket.timeout) as e:
                self.log(f"[搜索异常] 第 {attempt} 次: {keyword}\n    原因: 网络连接超时 ({e})")
            except requests.exceptions.RequestException as e:
                self.log(f"[搜索异常] 第 {attempt} 次: {keyword}\n    原因: 请求失败 ({e})")
            except Exception as e:
                msg = str(e)
                if "No results found" in msg:
                    self.log(f"[警告] {keyword} 无搜索结果 (DuckDuckGo 无匹配内容)"); break
                elif "429" in msg:
                    self.log(f"[搜索异常] 第 {attempt} 次: {keyword}\n    原因: 请求频率过高 (DuckDuckGo 限制访问)")
                else:
                    self.log(f"[搜索异常] 第 {attempt} 次: {keyword}\n    原因: 未知错误 ({msg})")
            time.sleep(2)

        urls = list(dict.fromkeys(urls))
        self.search_cache.set(cache_key, "\n".join(urls).encode("utf-8"))
        return urls

    def fetch_html(self, url: str, cookies: List[Dict[str, Any]]) -> Optional[str]:
        cache_key = f"html::{url}"
        cached = self.html_cache.get(cache_key)
        if cached:
            return cached.decode("utf-8", errors="ignore")

        with sync_playwright() as p:
            launch_kwargs = {"headless": True}
            if self.proxy.server():
                launch_kwargs["proxy"] = {"server": self.proxy.server()}
            browser = p.chromium.launch(**launch_kwargs)
            context = browser.new_context()
            if cookies:
                context.add_cookies(cookies)
            page = context.new_page()
            try:
                page.goto(url, timeout=60000)
                page.wait_for_timeout(self.wait_time * 1000)
                html = page.content()
                if len(html) > 10000:
                    self.html_cache.set(cache_key, html.encode("utf-8"))
                    return html
                return None
            finally:
                try:
                    context.close(); browser.close()
                except Exception:
                    pass

    def extract_info(self, html: str, url: str, keyword: str, region: str) -> Dict[str, Any]:
        info = extract_from_html(html, url)
        info["keyword"] = keyword
        info["region"] = region
        if info.get("website"):
            info["business_summary"] = analyze_website(info["website"]) or None
        return info
