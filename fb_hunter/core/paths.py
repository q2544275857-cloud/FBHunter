import os

APP_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DATA_DIR = os.path.join(APP_ROOT, "data")
CACHE_DIR = os.path.join(APP_ROOT, "cache")

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(CACHE_DIR, exist_ok=True)

def safe_name(s: str) -> str:
    return "".join(ch if ch.isalnum() or ch in "-_." or ch == " " else "_" for ch in (s or "")).strip().replace(" ", "_")
