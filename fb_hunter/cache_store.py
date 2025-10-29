import os, hashlib
from typing import Optional
from .core.paths import CACHE_DIR

class FileCache:
    def __init__(self, subdir: str):
        self.root = os.path.join(CACHE_DIR, f"_runtime_{subdir}")
        os.makedirs(self.root, exist_ok=True)
    def _path(self, key: str) -> str:
        h = hashlib.sha1(key.encode("utf-8")).hexdigest()
        return os.path.join(self.root, h + ".cache")
    def get(self, key: str) -> Optional[bytes]:
        p = self._path(key)
        if os.path.exists(p):
            with open(p, "rb") as f:
                return f.read()
        return None
    def set(self, key: str, data: bytes):
        with open(self._path(key), "wb") as f:
            f.write(data)
