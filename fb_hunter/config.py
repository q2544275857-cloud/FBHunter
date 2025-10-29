import os, json
from dataclasses import dataclass
from PySide6.QtCore import QStandardPaths

APP_DIR = os.path.join(QStandardPaths.writableLocation(QStandardPaths.AppDataLocation), "FBHunter")
COOKIES_DIR = os.path.join(APP_DIR, "cookies")
LOGS_DIR = os.path.join(APP_DIR, "logs")
CFG_PATH = os.path.join(APP_DIR, "settings.json")

DEFAULT_COLUMNS = ["url","title","description","email","phone","website","address","business_summary","keyword","region"]

@dataclass
class ProxyConfig:
    mode: str  # none / http / socks5
    host: str
    port: int
    def server(self):
        if self.mode == "none" or not self.host or not self.port:
            return None
        scheme = "http" if self.mode == "http" else "socks5"
        return f"{scheme}://{self.host}:{self.port}"

def ensure_app_dirs():
    for d in (APP_DIR, COOKIES_DIR, LOGS_DIR):
        os.makedirs(d, exist_ok=True)

def load_settings():
    if not os.path.exists(CFG_PATH):
        return {}
    try:
        with open(CFG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def save_settings(data: dict):
    with open(CFG_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
