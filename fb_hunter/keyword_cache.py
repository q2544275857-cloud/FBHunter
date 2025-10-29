import os, sqlite3
from typing import Dict, Any
from .core.paths import CACHE_DIR, safe_name

def kw_dir(keyword: str, region: str = "") -> str:
    tag = f"{(keyword or '').strip()}_{(region or '').strip()}" if region else (keyword or '').strip()
    d = os.path.join(CACHE_DIR, safe_name(tag))
    os.makedirs(d, exist_ok=True)
    return d

def db_path(keyword: str, region: str = "") -> str:
    return os.path.join(kw_dir(keyword, region), "cache.db")

def init_cache(keyword: str, region: str = ""):
    conn = sqlite3.connect(db_path(keyword, region))
    try:
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS pages (
                url TEXT PRIMARY KEY,
                title TEXT,
                description TEXT,
                email TEXT,
                phone TEXT,
                website TEXT,
                address TEXT,
                business_summary TEXT,
                keyword TEXT,
                region TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.commit()
    finally:
        conn.close()

def exists(keyword: str, url: str, region: str = "") -> bool:
    conn = sqlite3.connect(db_path(keyword, region))
    try:
        c = conn.cursor()
        c.execute("SELECT 1 FROM pages WHERE url=?", (url,))
        return c.fetchone() is not None
    finally:
        conn.close()

def upsert(keyword: str, row: Dict[str, Any], region: str = ""):
    conn = sqlite3.connect(db_path(keyword, region))
    try:
        c = conn.cursor()
        c.execute("""
            INSERT OR IGNORE INTO pages
            (url, title, description, email, phone, website, address, business_summary, keyword, region)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            row.get("url"), row.get("title"), row.get("description"), row.get("email"),
            row.get("phone"), row.get("website"), row.get("address"), row.get("business_summary"),
            keyword, region
        ))
        conn.commit()
    finally:
        conn.close()
