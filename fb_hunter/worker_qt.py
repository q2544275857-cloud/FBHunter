from PySide6.QtCore import QThread, Signal
import threading, queue
from typing import List, Dict, Any
from .scraper import Scraper
from .cookies_manager import CookiesManager
from .keyword_cache import init_cache, exists as kw_exists, upsert as kw_upsert

class ScrapeWorker(QThread):
    log = Signal(str)
    progress = Signal(int, int)
    finished_all = Signal(list)

    def __init__(self, keywords: List[str], region: str, max_results: int, threads: int, proxy, wait_time: int, cookie_paths: List[str]):
        super().__init__()
        self.keywords = keywords
        self.region = region.strip()
        self.max_results = max_results
        self.threads = max(1, threads)
        self.scraper = Scraper(proxy, wait_time, logger=lambda s: self.log.emit(s))
        self.cookie_paths = cookie_paths
        self._stop = threading.Event()

    def stop(self):
        self._stop.set()

    def run(self):
        try:
            for kw in self.keywords:
                init_cache(kw, self.region)

            cookies_round: List[List[Dict[str, Any]]] = []
            for p in self.cookie_paths:
                try:
                    cookies_round.append(CookiesManager.parse_for_playwright(p))
                except Exception as e:
                    self.log.emit(f"[cookies错误] {p} -> {e}")

            tasks: List[Dict[str, Any]] = []
            for kw in self.keywords:
                if self._stop.is_set(): self.finished_all.emit([]); return
                disp = f"{kw} (地区: {self.region})" if self.region else kw
                self.log.emit(f"[搜索] {disp}")
                query = f"{kw} {self.region}" if self.region else kw
                urls = self.scraper.ddgs_search_one(query, self.max_results)
                new_urls = [u for u in urls if not kw_exists(kw, u, self.region)]
                for u in new_urls:
                    tasks.append({"url": u, "keyword": kw})
                self.log.emit(f"[搜索完成] {kw} -> 新链接 {len(new_urls)} (已过滤历史缓存)")

            seen = set(); uniq_tasks = []
            for it in tasks:
                if it["url"] not in seen: seen.add(it["url"]); uniq_tasks.append(it)

            total = len(uniq_tasks)
            self.log.emit(f"[队列] 总待抓取：{total} 个")
            if total == 0:
                self.finished_all.emit([]); return

            rows_all: List[Dict[str, Any]] = []
            url_q: "queue.Queue[Dict[str, Any]]" = queue.Queue()
            for it in uniq_tasks: url_q.put(it)

            lock = threading.Lock(); done = 0

            def worker_fn(tid: int):
                nonlocal done
                while not url_q.empty() and not self._stop.is_set():
                    try:
                        item = url_q.get_nowait()
                    except queue.Empty:
                        break
                    url = item["url"]; kw = item["keyword"]
                    cookies = cookies_round[(done + tid) % len(cookies_round)] if cookies_round else []
                    try:
                        self.log.emit(f"[{tid}] 打开: {url}")
                        html = self.scraper.fetch_html(url, cookies)
                        if not html:
                            self.log.emit(f"[{tid}] 空白/受限: {url}")
                            with lock:
                                done += 1; self.progress.emit(done, total)
                            continue
                        info = self.scraper.extract_info(html, url, kw, self.region)
                        kw_upsert(kw, {k: info.get(k) for k in [
                            "url","title","description","email","phone","website","address","business_summary"
                        ]}, self.region)
                        with lock:
                            rows_all.append(info)
                            done += 1
                            self.progress.emit(done, total)
                            self.log.emit(
                                f"[{tid}] OK: {url}\n"
                                f"    title={info.get('title')}\n"
                                f"    email={info.get('email')} phone={info.get('phone')}\n"
                                f"    website={info.get('website')} summary={info.get('business_summary')}"
                            )
                    except Exception as e:
                        self.log.emit(f"[{tid}] 抓取异常: {url} -> {e}")

            threads: List[threading.Thread] = []
            for i in range(self.threads):
                t = threading.Thread(target=worker_fn, args=(i+1,), daemon=True)
                threads.append(t); t.start()
            for t in threads: t.join()

            self.finished_all.emit(rows_all)
        except Exception as e:
            self.log.emit(f"[致命错误] {e}")
            self.finished_all.emit([])
