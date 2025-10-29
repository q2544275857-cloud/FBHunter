import re, requests
from typing import Dict, Any, Optional
from urllib.parse import urlparse
from bs4 import BeautifulSoup

def extract_from_html(html: str, url: str) -> Dict[str, Any]:
    soup = BeautifulSoup(html, "html.parser")
    d = {"url": url, "title": None, "description": None, "email": None,
         "phone": None, "website": None, "address": None, "business_summary": None}

    ogt = soup.find("meta", property="og:title")
    if ogt and ogt.get("content"): d["title"] = ogt["content"].strip()
    if not d["title"]:
        t = soup.find("title")
        if t and t.text.strip(): d["title"] = t.text.strip()
    if not d["title"]:
        h = soup.find(["h1","h2"])
        if h and h.text.strip(): d["title"] = h.text.strip()
    if not d["title"]:
        parsed = urlparse(url)
        d["title"] = parsed.path.strip("/").split("/")[0].replace("-"," ").replace("_"," ").title()
    if d["title"]:
        d["title"] = re.sub(r"\s*\|\s*Facebook$", "", d["title"]).strip()

    ogd = soup.find("meta", property="og:description")
    if ogd and ogd.get("content"): d["description"] = ogd["content"]

    text = soup.get_text(" ", strip=True)
    email = re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text)
    phone = re.search(r"(\+\d{1,3}[-\s]?)?\(?\d{2,4}\)?[-\s]?\d{3,4}[-\s]?\d{3,4}", text)
    website = re.search(r"((?:https?://)?(?:www\.)?[A-Za-z0-9-]+\.[A-Za-z]{2,}(?:/[^\s]*)?)", text)
    address = re.search(r"\d{1,4}\s+\w+(?:\s\w+){1,4},?\s+\w+", text)

    if email: d["email"] = email.group()
    if phone: d["phone"] = phone.group()
    if website:
        w = website.group(1)
        if not w.startswith("http"): w = "https://" + w
        d["website"] = w
    if address: d["address"] = address.group()
    return d

def analyze_website(website_url: str) -> Optional[str]:
    try:
        resp = requests.get(website_url, headers={"User-Agent":"Mozilla/5.0"}, timeout=12)
        if resp.status_code != 200 or len(resp.text) < 500: return None
        soup = BeautifulSoup(resp.text, "html.parser")
        t = soup.get_text(" ", strip=True); snippet = " ".join(t.split()[:220])
        rules = {
            "christmas": "Christmas/holiday decorations or lighting",
            "lighting": "Lighting products or installation",
            "import": "Importer/wholesaler",
            "wholesale": "Wholesale trader",
            "retail": "Retail/shop",
            "manufacturer": "Manufacturer or factory",
            "decor": "Decorations/design"
        }
        for k,v in rules.items():
            if k in snippet.lower(): return f"Likely engaged in {v}."
        return "General business website."
    except Exception:
        return None

def normalize_fb_url(u: str) -> str:
    if u.startswith("https://facebook.com/"): return u.replace("https://facebook.com/","https://www.facebook.com/")
    if u.startswith("http://facebook.com/"): return u.replace("http://facebook.com/","https://www.facebook.com/")
    if u.startswith("http://www.facebook.com/"): return u.replace("http://","https://")
    return u

def is_profile_or_page(url: str) -> bool:
    parsed = urlparse(url); netloc = parsed.netloc.lower()
    if netloc not in ("facebook.com","www.facebook.com"): return False
    path = parsed.path.strip("/"); 
    if not path: return False
    bad = (
        r"^groups?/|^events?/|^marketplace/|^gaming/|^reel/|^reels?/|^videos?/|"
        r"^photo|^photos?/|^watch/|^story|^stories?|^people/|^pages/|"
        r"^media/|^profile\.php|^permalink\.php|^share\.php|^post|"
        r".*/posts?/|.*fbid=|.*story_fbid="
    )
    if re.search(bad, path) or re.search(bad, parsed.query or ""): return False
    if ".php" in path or re.match(r"^\d+$", path): return False
    if any(x in url for x in ("/posts/","/reel/","/reels/","/video","/photo","/story")): return False
    return True

def extract_poster_url_from_post(url: str) -> Optional[str]:
    m = re.search(r"facebook\.com/([^/?#]+)/posts", url)
    if m:
        username = m.group(1)
        if username.lower() not in ("groups","pages","events"):
            return f"https://www.facebook.com/{username}/"
    return None
