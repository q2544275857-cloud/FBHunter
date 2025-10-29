import os, json
from typing import List, Dict, Any, Tuple
from .config import COOKIES_DIR

REQUIRED_FIELDS = {"name","value"}

class CookiesManager:
    @staticmethod
    def import_cookie_file(src_path: str) -> str:
        os.makedirs(COOKIES_DIR, exist_ok=True)
        base = os.path.basename(src_path)
        name, ext = os.path.splitext(base)
        dst = os.path.join(COOKIES_DIR, base)
        i = 1
        while os.path.exists(dst):
            dst = os.path.join(COOKIES_DIR, f"{name}_{i}{ext}"); i += 1
        with open(src_path, "r", encoding="utf-8") as f: _ = json.load(f)
        with open(src_path, "rb") as rf, open(dst, "wb") as wf: wf.write(rf.read())
        return dst

    @staticmethod
    def list_cookie_files() -> List[str]:
        if not os.path.exists(COOKIES_DIR): return []
        return [os.path.join(COOKIES_DIR, f) for f in os.listdir(COOKIES_DIR) if f.lower().endswith(".json")]

    @staticmethod
    def parse_for_playwright(path: str) -> List[Dict[str,Any]]:
        with open(path, "r", encoding="utf-8") as f: raw = json.load(f)
        cookies = []
        for c in raw:
            if not REQUIRED_FIELDS.issubset(c.keys()): continue
            cookies.append({
                "name": c["name"], "value": c["value"],
                "domain": c.get("domain",".facebook.com"), "path": c.get("path","/"),
                "secure": c.get("secure", True), "httpOnly": c.get("httpOnly", False)
            })
        return cookies

    @staticmethod
    def validate_cookie_json(path: str) -> Tuple[bool,str]:
        try:
            data = CookiesManager.parse_for_playwright(path)
            if not data: return False, "没有有效 cookie 项"
            names = {c["name"] for c in data}
            if not ("c_user" in names or "sb" in names):
                return True, "格式正确，但未检测到典型登录标记（可能未登录）"
            return True, "通过"
        except Exception as e:
            return False, str(e)
