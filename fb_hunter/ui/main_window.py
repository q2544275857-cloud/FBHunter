import os, datetime
from typing import List, Dict
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QLineEdit, QPushButton,
    QTextEdit, QFileDialog, QListWidget, QSpinBox, QGroupBox, QGridLayout, QCheckBox, QMessageBox, QProgressBar
)
from PySide6.QtGui import QTextCursor
from ..config import DEFAULT_COLUMNS, save_settings, load_settings, ensure_app_dirs, COOKIES_DIR, ProxyConfig
from ..logging_config import setup_logging
from ..proxy_manager import ProxyManager
from ..cookies_manager import CookiesManager
from ..worker_qt import ScrapeWorker
from ..core.paths import DATA_DIR, CACHE_DIR, safe_name
import pandas as pd

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        ensure_app_dirs()
        self.logger = setup_logging()
        self.setWindowTitle("FB Hunter - Facebook 抓取 GUI")
        self.resize(1120, 840)

        self.cookies_files: List[str] = []
        self.worker: ScrapeWorker | None = None
        self._build_ui()
        self._load_settings()
        self._auto_detect_proxy()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        # 代理设置
        proxy_group = QGroupBox("代理设置")
        g = QGridLayout()
        self.proxy_mode = QComboBox(); self.proxy_mode.addItems(["none","http","socks5"])
        self.proxy_host = QLineEdit(); self.proxy_host.setPlaceholderText("127.0.0.1")
        self.proxy_port = QLineEdit(); self.proxy_port.setPlaceholderText("10808")
        self.btn_test_proxy = QPushButton("测试代理"); self.btn_test_proxy.clicked.connect(self.on_test_proxy)
        g.addWidget(QLabel("模式"),0,0); g.addWidget(self.proxy_mode,0,1)
        g.addWidget(QLabel("地址"),0,2); g.addWidget(self.proxy_host,0,3)
        g.addWidget(QLabel("端口"),0,4); g.addWidget(self.proxy_port,0,5)
        g.addWidget(self.btn_test_proxy,0,6)
        proxy_group.setLayout(g); layout.addWidget(proxy_group)

        # Cookies 管理
        ck_group = QGroupBox("Cookies 管理（可导入多个）")
        ck_layout = QHBoxLayout()
        self.cookie_list = QListWidget()
        btns = QVBoxLayout()
        self.btn_add_cookie = QPushButton("导入 cookies.json")
        self.btn_del_cookie = QPushButton("移除选中")
        self.btn_check_cookie = QPushButton("检测选中")
        self.btn_add_cookie.clicked.connect(self.on_add_cookie)
        self.btn_del_cookie.clicked.connect(self.on_del_cookie)
        self.btn_check_cookie.clicked.connect(self.on_check_cookie)
        btns.addWidget(self.btn_add_cookie); btns.addWidget(self.btn_del_cookie); btns.addWidget(self.btn_check_cookie); btns.addStretch(1)
        ck_layout.addWidget(self.cookie_list, 3); ck_layout.addLayout(btns, 1)
        ck_group.setLayout(ck_layout); layout.addWidget(ck_group)

        # 搜索与并发
        kw_group = QGroupBox("搜索与并发")
        k = QGridLayout()
        self.kw_edit = QTextEdit(); self.kw_edit.setPlaceholderText("每行一个关键词…")
        self.region_edit = QLineEdit(); self.region_edit.setPlaceholderText("地区（可选）：例如 United States / Japan / Germany")
        self.spin_max = QSpinBox(); self.spin_max.setRange(1, 100); self.spin_max.setValue(15)
        self.spin_threads = QSpinBox(); self.spin_threads.setRange(1, 16); self.spin_threads.setValue(4)
        self.spin_wait = QSpinBox(); self.spin_wait.setRange(3, 20); self.spin_wait.setValue(8)
        k.addWidget(QLabel("关键词"), 0, 0); k.addWidget(self.kw_edit, 0, 1, 3, 5)
        k.addWidget(QLabel("地区"), 3, 0); k.addWidget(self.region_edit, 3, 1, 1, 5)
        k.addWidget(QLabel("每词最大结果"), 4, 0); k.addWidget(self.spin_max, 4, 1)
        k.addWidget(QLabel("线程数"), 4, 2); k.addWidget(self.spin_threads, 4, 3)
        k.addWidget(QLabel("渲染等待(秒)"), 4, 4); k.addWidget(self.spin_wait, 4, 5)
        kw_group.setLayout(k); layout.addWidget(kw_group)

        # 导出（仅控制列）
        export_group = QGroupBox("导出字段（文件固定导出到 data/）")
        e = QGridLayout()
        self.chk_cols: Dict[str, QCheckBox] = {}
        col_row = 0; col_col = 0
        for col in DEFAULT_COLUMNS:
            cb = QCheckBox(col)
            cb.setChecked(col in ("url","title","email","phone","website","keyword","region"))
            self.chk_cols[col] = cb
            e.addWidget(cb, col_row, col_col)
            col_col = 0 if col_col > 2 else col_col + 1
            if col_col == 0: col_row += 1
        export_group.setLayout(e); layout.addWidget(export_group)

        # 控制+进度
        ctrl = QHBoxLayout()
        self.btn_start = QPushButton("开始抓取"); self.btn_stop = QPushButton("停止")
        self.btn_start.clicked.connect(self.on_start); self.btn_stop.clicked.connect(self.on_stop)
        self.btn_stop.setEnabled(False)
        ctrl.addWidget(self.btn_start); ctrl.addWidget(self.btn_stop); ctrl.addStretch(1)
        layout.addLayout(ctrl)

        self.progress = QProgressBar(); self.progress.setRange(0,1); self.progress.setValue(0)
        layout.addWidget(self.progress)

        # 日志
        self.log = QTextEdit(); self.log.setReadOnly(True)
        layout.addWidget(self.log, 2)

    def _load_settings(self):
        cfg = load_settings() or {}
        self.proxy_mode.setCurrentText(cfg.get("proxy_mode","none"))
        self.proxy_host.setText(cfg.get("proxy_host",""))
        self.proxy_port.setText(str(cfg.get("proxy_port","")))
        self.cookie_list.clear()
        files = cfg.get("cookies_files") or []
        auto = CookiesManager.list_cookie_files()
        merged = list(dict.fromkeys(files + auto))
        for p in merged:
            if os.path.exists(p): self.cookie_list.addItem(p)
        self.cookies_files = merged

    def _save_settings(self):
        cfg = {
            "proxy_mode": self.proxy_mode.currentText(),
            "proxy_host": self.proxy_host.text().strip(),
            "proxy_port": int(self.proxy_port.text() or 0),
            "cookies_files": self.cookies_files
        }
        from ..config import save_settings as _s; _s(cfg)

    def _auto_detect_proxy(self):
        from ..proxy_manager import ProxyManager as PM
        pm = PM.read_system_proxy()
        if pm.server():
            self.proxy_mode.setCurrentText(pm.mode); self.proxy_host.setText(pm.host); self.proxy_port.setText(str(pm.port))
            self.append_log(f"[代理] 自动检测：{pm.server()}")
        else:
            self.append_log("[代理] 未检测到系统代理，默认直连")

    def on_test_proxy(self):
        proxy = ProxyConfig(self.proxy_mode.currentText(), self.proxy_host.text().strip(), int(self.proxy_port.text() or 0))
        from ..proxy_manager import ProxyManager as PM
        ok, msg = PM.test_connectivity(proxy)
        QMessageBox.information(self, "代理测试", f"结果：{'可用' if ok else '不可用'}\n{msg}")

    def on_add_cookie(self):
        path, _ = QFileDialog.getOpenFileName(self, "选择 cookies.json", "", "JSON Files (*.json)")
        if not path: return
        try:
            from ..cookies_manager import CookiesManager as CM
            dst = CM.import_cookie_file(path)
            self.cookies_files.append(dst); self.cookie_list.addItem(dst)
            self._save_settings()
            QMessageBox.information(self, "完成", f"已导入：\n{dst}")
        except Exception as e:
            QMessageBox.warning(self, "错误", f"导入失败：{e}")

    def on_del_cookie(self):
        items = self.cookie_list.selectedItems()
        if not items: return
        for it in items:
            path = it.text()
            self.cookies_files = [p for p in self.cookies_files if p != path]
            idx = self.cookie_list.row(it); self.cookie_list.takeItem(idx)
        self._save_settings()

    def on_check_cookie(self):
        items = self.cookie_list.selectedItems() or []
        if not items:
            QMessageBox.information(self, "提示", "请选择要检测的 cookie 文件"); return
        it = items[0]
        from ..cookies_manager import CookiesManager as CM
        ok, msg = CM.validate_cookie_json(it.text())
        QMessageBox.information(self, "检测结果", f"{msg}" if ok else f"无效：{msg}")

    def on_start(self):
        if self.worker and self.worker.isRunning():
            QMessageBox.warning(self, "提示", "任务正在运行中"); return
        keywords = [s.strip() for s in self.kw_edit.toPlainText().splitlines() if s.strip()]
        if not keywords: QMessageBox.warning(self, "错误", "请填写至少一个关键词"); return
        region = self.region_edit.text().strip()
        try:
            port = int(self.proxy_port.text() or 0)
        except ValueError:
            QMessageBox.warning(self, "错误", "代理端口不是有效数字"); return
        cols = [c for c, cb in self.chk_cols.items() if cb.isChecked()]
        if "url" not in cols: cols = ["url"] + [c for c in cols if c != "url"]

        proxy = ProxyConfig(self.proxy_mode.currentText(), self.proxy_host.text().strip(), port)
        self.worker = ScrapeWorker(keywords, region, self.spin_max.value(), self.spin_threads.value(), proxy, self.spin_wait.value(), self.cookies_files)
        self.worker.log.connect(self.append_log)
        self.worker.progress.connect(self.on_progress)
        self.worker.finished_all.connect(lambda rows: self.on_finished(rows, cols, keywords, region))
        self.append_log("=== 任务开始 ===")
        self.btn_start.setEnabled(True); self.btn_stop.setEnabled(True)
        self.progress.reset(); self.progress.setMaximum(1); self.progress.setValue(0)
        self.worker.start()
        self._save_settings()

    def on_stop(self):
        if self.worker and self.worker.isRunning():
            self.worker.stop(); self.append_log("[命令] 停止中…")

    def on_progress(self, done: int, total: int):
        if self.progress.maximum() != max(1, total):
            self.progress.setMaximum(max(1, total))
        self.progress.setValue(done)
        self.append_log(f"[进度] {done}/{total}")

    def _export_csv(self, df: pd.DataFrame, path: str):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        df.to_csv(path, index=False, encoding="utf-8-sig")
        self.append_log(f"[导出] 已保存：{path}")

    def on_finished(self, rows: List[Dict], cols: List[str], keywords: List[str], region: str):
        count = len(rows)
        self.append_log(f"=== 任务结束：共新增 {count} 条 ===")
        self.progress.setValue(self.progress.maximum())

        if count == 0:
            QMessageBox.information(self, "完成", "没有新的数据"); 
            self.btn_start.setEnabled(True); self.btn_stop.setEnabled(False); self.worker=None; return

        df_all = pd.DataFrame(rows)
        if "url" in df_all.columns:
            df_all = df_all.drop_duplicates(subset=["url"], keep="first")
        for c in cols:
            if c not in df_all.columns: df_all[c] = None
        df_all = df_all[cols]

        today = datetime.datetime.now().strftime("%Y-%m-%d")
        if len(keywords) == 1:
            tag = f"{safe_name(keywords[0])}_{safe_name(region)}" if region else safe_name(keywords[0])
            export_path = os.path.join(DATA_DIR, f"{tag}_{today}.csv")
            self._export_csv(df_all, export_path)
        else:
            tag = f"multi_{safe_name(region)}" if region else "multi"
            export_path = os.path.join(DATA_DIR, f"{tag}_{today}.csv")
            self._export_csv(df_all, export_path)

            # 可选：按关键词分文件到 cache/<kw_region>/
            if "keyword" in df_all.columns:
                for kw, df_kw in df_all.groupby("keyword"):
                    kw_tag = f"{safe_name(kw)}_{safe_name(region)}" if region else safe_name(kw)
                    sub_dir = os.path.join(CACHE_DIR, kw_tag)
                    os.makedirs(sub_dir, exist_ok=True)
                    sub_path = os.path.join(sub_dir, f"{kw_tag}_{today}.csv")
                    self._export_csv(df_kw, sub_path)

        QMessageBox.information(self, "完成", f"任务完成，共导出 {len(df_all)} 条数据。")

        self.btn_start.setEnabled(True); self.btn_stop.setEnabled(False)
        self.worker = None

    def append_log(self, msg: str):
        self.log.append(msg)
        self.log.moveCursor(QTextCursor.End)
        self.logger.info(msg)
