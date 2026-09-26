#!/usr/bin/env python3
"""
LuffyTV Manga Uploader
======================
Watches /root/downloads/manga/ for new chapter ZIPs.
Extracts each ZIP, uploads each page image (catbox → imagehosting.co → imglink.cc → pixelhost.fun),
saves page URLs to manga.db (SQLite) + manga.json (mirror).
Deletes local file after upload.

To use catbox without 412 IP-block errors, set CATBOX_USERHASH env var
(free catbox account → https://catbox.moe/user/manage.php).
"""
import os
import re
import sys
import json
import time
import random
import sqlite3
import zipfile
import logging
import requests
import urllib.parse
from pathlib import Path
from datetime import datetime, timezone

# ============================================================
# CONFIG
# ============================================================
WATCH_DIR = os.environ.get("MANGA_WATCH_DIR", "/root/downloads/manga")
FAIL_DIR = os.environ.get("MANGA_FAIL_DIR", "/root/downloads/manga/failed")
LOG_FILE = os.environ.get("MANGA_LOG_FILE", "/var/log/luffytv-manga-uploader.log")
DB_FILE = os.environ.get("MANGA_DB_FILE", "/var/lib/luffytv/manga.db")
JSON_FILE = os.environ.get("MANGA_JSON_FILE", "/var/lib/luffytv/manga.json")
SEEN_FILE = os.environ.get("MANGA_SEEN_FILE", "/var/lib/luffytv/manga-seen.json")
POLL_INTERVAL = int(os.environ.get("MANGA_POLL_INTERVAL", "3"))
MIN_FILE_SIZE = 10 * 1024  # 10 KB
FILE_STABLE_TIME = 3       # seconds — reduced from 10 to 3 for faster processing

# Image host config — Catbox primary, Imgur/Freeimage/8upload as fallbacks
# (upload_image() always tries catbox first regardless of this setting)
IMAGE_HOST = os.environ.get("MANGA_IMAGE_HOST", "catbox")

# Imgur (anonymous — 12,500 uploads/hour, no bans)
IMGUR_API = "https://api.imgur.com/3/image"
IMGUR_CLIENT_ID = os.environ.get("IMGUR_CLIENT_ID", "546c25a59c58ad7")

# Freeimage.host (backup — unlimited, no signup, uses same key as imgbb)
FREEIMAGE_API = "https://freeimage.host/api/1/upload"
FREEIMAGE_KEY = "6d207e02198a847aa98d0a2a901485a5"

# 8upload (backup 2 — works sometimes)
UPLOAD8_API = "https://8upload.com/upload/mt/"
UPLOAD8_REFERER = "https://8upload.com/"

# Proxy rotation — cycle through these to avoid 429 bans
PROXIES = [
    "http://tickets:proxyon145@196.196.23.136:12345",
    "http://tickets:proxyon145@196.196.23.45:12345",
    "http://uncpjndo:w77Ebc0h2A@us4.cactussstp.com:3129",
    "http://hughmuir2:lisamarie11@us4.cactussstp.com:81",
    "http://uncpjndo:w77Ebc0h2A@us4.cactussstp.com:8080",
    "http://tickets:proxyon145@162.212.170.77:12345",
    "http://uncpjndo:w77Ebc0h2A@us6.cactussstp.com:3129",
    "http://tickets:proxyon145@104.160.17.116:12345",
    "http://tickets:proxyon145@162.212.170.252:12345",
    "http://hughmuir2:lisamarie11@us6.cactussstp.com:8080",
    "http://bvmbsmie:shibby2511@us6.cactussstp.com:8080",
    "http://tickets:proxyon145@107.150.71.197:12345",
    "http://tickets:proxyon145@107.150.71.30:12345",
    "http://tickets:proxyon145@161.0.1.13:12345",
    "http://hughmuir2:lisamarie11@us6.cactussstp.com:3129",
    "http://bvmbsmie:shibby2511@us6.cactussstp.com:81",
    "http://tickets:proxyon145@138.94.218.193:12345",
    "http://hughmuir2:lisamarie11@us6.cactussstp.com:81",
    "http://tickets:proxyon145@173.234.153.90:12345",
    "http://tickets:proxyon145@50.3.137.165:12345",
    "http://bvmbsmie:shibby2511@us4.cactussstp.com:81",
    "http://tickets:proxyon145@190.123.219.34:12345",
    "http://uncpjndo:w77Ebc0h2A@us6.cactussstp.com:3129",
    "http://tickets:proxyon145@181.177.102.240:12345",
    "http://tickets:proxyon145@107.158.118.94:12345",
    "http://tickets:proxyon145@107.175.37.77:12345",
    "http://hughmuir2:lisamarie11@us4.cactussstp.com:8080",
    "http://tickets:proxyon145@107.175.38.146:12345",
    "http://tickets:proxyon145@107.173.112.194:12345",
    "http://tickets:proxyon145@107.172.170.102:12345",
    "http://tickets:proxyon145@107.175.34.7:12345",
    "http://tickets:proxyon145@161.0.1.119:12345",
    "http://tickets:proxyon145@50.3.137.177:12345",
    "http://tickets:proxyon145@190.123.219.12:12345",
    "http://tickets:proxyon145@23.104.162.39:12345",
    "http://tickets:proxyon145@107.173.112.211:12345",
    "http://tickets:proxyon145@192.227.238.145:12345",
    "http://tickets:proxyon145@107.172.241.122:12345",
    "http://bvmbsmie:shibby2511@us6.cactussstp.com:3129",
    "http://uncpjndo:w77Ebc0h2A@us4.cactussstp.com:81",
    "http://bvmbsmie:shibby2511@us4.cactussstp.com:3129",
    "http://hughmuir2:lisamarie11@us4.cactussstp.com:3129",
    "http://uncpjndo:w77Ebc0h2A@us6.cactussstp.com:8080",
]
import threading as _threading
_proxy_lock = _threading.Lock()
_proxy_index = 0

def get_next_proxy():
    """Get the next proxy in rotation. Thread-safe round-robin."""
    global _proxy_index
    with _proxy_lock:
        proxy = PROXIES[_proxy_index % len(PROXIES)]
        _proxy_index += 1
    return {"http": proxy, "https": proxy}

def get_random_proxy():
    """Get a random proxy for variety. Thread-safe."""
    proxy = random.choice(PROXIES)
    return {"http": proxy, "https": proxy}

# Catbox (backup)
CATBOX_API = "https://catbox.moe/user/api.php"
# Delay between uploads (seconds)
UPLOAD_DELAY = 0.5

# Imgur (backup)
IMGUR_API = "https://api.imgur.com/3/image"
IMGUR_CLIENT_ID = os.environ.get("IMGUR_CLIENT_ID", "546c25a59c58ad7")

# imagehosting.co — needs CSRF token + session cookie (both obtained by visiting homepage)
IMAGEHOSTING_API = "https://imagehosting.co/api/upload.php"
IMAGEHOSTING_HOME = "https://imagehosting.co/en"

# imglink.cc — simple POST to /api/upload with field "images"
IMGLINK_API = "https://imglink.cc/api/upload"
IMGLINK_HOME = "https://imglink.cc/upload/free-image-hosting"

# pixelhost.fun — POST to /api/upload with field "files"
PIXELHOST_API = "https://pixelhost.fun/api/upload"
PIXELHOST_HOME = "https://pixelhost.fun/upload-image-get-link"

ARCHIVE_EXTENSIONS = {".zip", ".cbz", ".cbr"}
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp"}

os.makedirs(WATCH_DIR, exist_ok=True)
os.makedirs(FAIL_DIR, exist_ok=True)
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
os.makedirs(os.path.dirname(DB_FILE), exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout),
    ]
)
log = logging.getLogger("manga-uploader")


# ============================================================
# DATABASE
# ============================================================
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS manga (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            manga_id TEXT,
            manga_name TEXT NOT NULL,
            chapter_id TEXT,
            chapter_number TEXT NOT NULL,
            page_number INTEGER NOT NULL,
            image_url TEXT NOT NULL,
            file_size INTEGER,
            source TEXT,
            anilist_id INTEGER,
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(manga_name, chapter_number, page_number)
        )
    """)
    conn.commit()
    conn.close()
    log.info(f"💾 Database: {DB_FILE}")


def save_to_db(manga_name, chapter_number, page_number, image_url, file_size,
               manga_id=None, chapter_id=None, source=None, anilist_id=None):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    try:
        c.execute("""
            INSERT OR REPLACE INTO manga
            (manga_id, manga_name, chapter_id, chapter_number, page_number,
             image_url, file_size, source, anilist_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (manga_id, manga_name, chapter_id, chapter_number, page_number,
              image_url, file_size, source, anilist_id))
        conn.commit()
        log.info(f"💾 Saved: {manga_name} {chapter_number} p{page_number} → {image_url}")
    except Exception as e:
        log.error(f"❌ DB save error: {e}")
    finally:
        conn.close()


def load_json_db():
    try:
        if os.path.exists(JSON_FILE):
            with open(JSON_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        log.warning(f"Could not load JSON DB: {e}")
    return {}


def save_to_json_db(manga_name, chapter_number, page_number, image_url, anilist_id=None):
    try:
        data = load_json_db()
        manga = data.setdefault(manga_name, {
            "title": manga_name,
            "anilist_id": anilist_id,
            "chapters": {},
        })
        if anilist_id and not manga.get("anilist_id"):
            manga["anilist_id"] = anilist_id
        chapters = manga["chapters"]
        chapter = chapters.setdefault(chapter_number, {
            "pages": {},
            "uploaded_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        })
        chapter["pages"][str(page_number)] = image_url
        tmp = JSON_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(tmp, JSON_FILE)
        log.info(f"📄 Updated JSON: {manga_name} {chapter_number} p{page_number}")
    except Exception as e:
        log.error(f"❌ JSON save error: {e}")


# ============================================================
# IMAGE UPLOADERS
# ============================================================
import base64
import re as _re

def upload_to_8upload(file_bytes, filename, timeout=30):
    """Upload image to 8upload.com via proxy rotation. Returns DIRECT image URL or None.
    Each request goes through a different proxy IP to avoid 429 bans.
    """
    # Try up to 3 different proxies
    for proxy_attempt in range(3):
        proxy = get_next_proxy()
        try:
            files = {"images[]": (filename, file_bytes, "image/jpeg")}
            r = requests.post(
                UPLOAD8_API,
                files=files,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/125.0.0.0 Safari/537.36",
                    "Referer": UPLOAD8_REFERER,
                    "Accept": "application/json, text/plain, */*",
                },
                proxies=proxy,
                timeout=timeout,
            )
            if r.status_code == 429:
                log.warning(f"8upload 429 via proxy, switching proxy (attempt {proxy_attempt+1}/3)...")
                continue
            if r.status_code != 200:
                log.warning(f"8upload HTTP {r.status_code} via proxy")
                continue
            # Parse response — format: "\/uploads\/{hash}"
            view_path = r.text.strip()
            view_path = view_path.strip('"').strip("'")
            view_path = view_path.replace("\\/", "/").replace("\\\\", "\\")
            view_path = view_path.strip('"').strip("'").strip()
            if not view_path or not view_path.startswith("/uploads/"):
                continue
            view_url = f"https://8upload.com{view_path}"
            # Fetch the view page to get the direct image URL (use a different proxy)
            proxy2 = get_next_proxy()
            r2 = requests.get(view_url, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/125.0.0.0 Safari/537.36",
            }, proxies=proxy2, timeout=timeout)
            if r2.status_code != 200:
                continue
            # Extract direct image URL
            matches = _re.findall(r'https://i\.8upload\.com/image/[a-zA-Z0-9]+/[a-zA-Z0-9._-]+\.(?:jpg|jpeg|png|webp|gif|bmp)', r2.text)
            if matches:
                return matches[0]
            matches = _re.findall(r'(https://i\.8upload\.com/image/[a-zA-Z0-9]+/[^"\'<\s\]]+)', r2.text)
            if matches:
                return matches[0]
        except Exception as e:
            log.warning(f"8upload proxy error (attempt {proxy_attempt+1}): {e}")
            continue
    log.warning(f"8upload: all 3 proxy attempts failed")
    return None


def upload_to_imgur(file_bytes, filename, timeout=30):
    """Upload image bytes to Imgur (anonymous). Returns URL or None."""
    try:
        b64 = base64.b64encode(file_bytes).decode()
        r = requests.post(
            IMGUR_API,
            headers={
                "Authorization": f"Client-ID {IMGUR_CLIENT_ID}",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/125.0.0.0 Safari/537.36",
            },
            data={"image": b64, "type": "base64"},
            timeout=timeout,
        )
        if r.status_code == 200:
            data = r.json().get("data", {})
            url = data.get("link")
            if url:
                return url
            return None
        return None
    except Exception as e:
        log.warning(f"Imgur upload error: {e}")
        return None


def upload_to_catbox(file_bytes, filename, timeout=120, max_retries=3):
    """Upload bytes to catbox.moe (primary). Returns URL or None.
    Catbox now returns HTTP 412 "Invalid uploader" if too many anonymous uploads
    come from the same IP. Set CATBOX_USERHASH env var (from a free catbox account)
    to bypass this rate-limit and upload as that user.
    """
    catbox_userhash = os.environ.get("CATBOX_USERHASH", "")
    catbox_headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/125.0.0.0 Safari/537.36",
    }
    for attempt in range(max_retries):
        try:
            files = {
                "reqtype": (None, "fileupload"),
                "fileToUpload": (filename, file_bytes, "application/octet-stream"),
            }
            if catbox_userhash:
                files["userhash"] = (None, catbox_userhash)
            r = requests.post(CATBOX_API, files=files, headers=catbox_headers, timeout=timeout)
            if r.status_code == 200 and r.text.startswith("https://"):
                return r.text.strip()
            # 412 = "Invalid uploader" — IP blocked, no point retrying
            if r.status_code == 412:
                log.warning(f"catbox: 412 Invalid uploader (IP rate-limited) — set CATBOX_USERHASH to bypass")
                return None
            if r.status_code == 200 and not r.text.strip():
                time.sleep(3 * (attempt + 1))
                continue
            return None
        except Exception:
            if attempt < max_retries - 1:
                time.sleep(3)
                continue
            return None
    return None


def upload_to_freeimage(file_bytes, filename, timeout=30):
    """Upload to Freeimage.host. Returns URL or None.
    Unlimited uploads, no signup, no bans.
    """
    try:
        r = requests.post(
            FREEIMAGE_API,
            params={"key": FREEIMAGE_KEY},
            files={"source": (filename, file_bytes, "image/jpeg")},
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/125.0.0.0 Safari/537.36"},
            timeout=timeout,
        )
        if r.status_code == 200:
            data = r.json()
            if data.get("status_code") == 200:
                url = data.get("image", {}).get("display_url") or data.get("image", {}).get("url")
                if url:
                    return url
        return None
    except Exception:
        return None


def upload_to_imagehosting(file_bytes, filename, timeout=60):
    """Upload to imagehosting.co. Needs CSRF token + PHPSESSID cookie.
    Returns the direct CDN URL (i.imghos.co) or None.
    """
    try:
        s = requests.Session()
        s.headers["User-Agent"] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/125.0.0.0 Safari/537.36"
        # 1) Visit homepage to get PHPSESSID cookie + CSRF token
        r = s.get(IMAGEHOSTING_HOME, timeout=15)
        m = _re.search(r"csrfToken\s*=\s*['\"]([a-f0-9]+)['\"]", r.text)
        if not m:
            log.warning("imagehosting.co: CSRF token not found")
            return None
        token = m.group(1)
        # 2) Upload with token in both header AND form field
        r = s.post(
            IMAGEHOSTING_API,
            headers={
                "X-CSRF-Token": token,
                "Referer": IMAGEHOSTING_HOME,
                "Origin": "https://imagehosting.co",
            },
            files={"images": (filename, file_bytes, "image/jpeg")},
            data={"csrf_token": token},
            timeout=timeout,
        )
        if r.status_code == 200:
            j = r.json()
            results = j.get("results", [])
            if results and results[0].get("success"):
                return results[0].get("url")
        return None
    except Exception as e:
        log.warning(f"imagehosting.co error: {e}")
        return None


def upload_to_imglink(file_bytes, filename, timeout=60):
    """Upload to imglink.cc /api/upload. Field name: 'images'.
    Returns the CDN URL (imglink.cc/cdn/...) or None.
    """
    try:
        r = requests.post(
            IMGLINK_API,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/125.0.0.0 Safari/537.36",
                "Accept": "application/json",
                "Origin": "https://imglink.cc",
                "Referer": IMGLINK_HOME,
            },
            files={"images": (filename, file_bytes, "image/jpeg")},
            timeout=timeout,
        )
        if r.status_code == 200:
            j = r.json()
            imgs = j.get("images", [])
            if imgs:
                return imgs[0].get("url")
        return None
    except Exception as e:
        log.warning(f"imglink.cc error: {e}")
        return None


def upload_to_pixelhost(file_bytes, filename, timeout=60):
    """Upload to pixelhost.fun /api/upload. Field name: 'files'.
    Returns the direct image URL (pixelhost.fun/uploads/...) or None.
    Note: pixelhost API has been returning 500 errors as of 2026-09-25;
    when that happens the chain silently moves to the next host.
    """
    try:
        r = requests.post(
            PIXELHOST_API,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/125.0.0.0 Safari/537.36",
                "Accept": "application/json",
                "Origin": "https://pixelhost.fun",
                "Referer": PIXELHOST_HOME,
            },
            files={"files": (filename, file_bytes, "image/jpeg")},
            timeout=timeout,
        )
        if r.status_code == 200:
            j = r.json()
            if j.get("success"):
                return j.get("url") or j.get("direct")
        return None
    except Exception as e:
        log.warning(f"pixelhost.fun error: {e}")
        return None


def upload_image(file_bytes, filename):
    """Upload image — chain order: catbox → imagehosting.co → imglink.cc → pixelhost.fun.
    Returns the first successful URL or None.
    Each host is independent; if one fails (banned, broken, timed out) we move on.
    """
    # 1. Catbox (primary)
    url = upload_to_catbox(file_bytes, filename)
    if url:
        return url
    # 2. imagehosting.co (user-requested fallback #1)
    url = upload_to_imagehosting(file_bytes, filename)
    if url:
        return url
    # 3. imglink.cc (user-requested fallback #2)
    url = upload_to_imglink(file_bytes, filename)
    if url:
        return url
    # 4. pixelhost.fun (user-requested fallback #3 — currently returning 500,
    #    kept in chain so when pixelhost comes back online it's used automatically)
    url = upload_to_pixelhost(file_bytes, filename)
    if url:
        return url
    return None


# ============================================================
# FILE PARSING
# ============================================================
def parse_manga_info(filepath):
    """Parse manga name + chapter number + anilist_id from filepath.
    Reads _meta.json from the manga folder (created by the scraper) to get the AniList ID.
    """
    # Resolve symlink to get the real path
    real_path = os.path.realpath(filepath)
    filename = os.path.basename(real_path)
    stem = os.path.splitext(filename)[0]
    manga_dir = os.path.dirname(real_path)
    parent_dir = os.path.basename(manga_dir)

    # Read _meta.json for AniList ID + proper manga name
    anilist_id = None
    manga_name = None
    meta_path = os.path.join(manga_dir, "_meta.json")
    try:
        if os.path.exists(meta_path):
            with open(meta_path, "r") as f:
                meta = json.load(f)
                anilist_id = meta.get("anilist_id")
                manga_name = meta.get("manga_name")
    except Exception:
        pass

    # Fallback: use parent folder name as manga name
    if not manga_name:
        if parent_dir and parent_dir not in ("manga", "downloads", "downloads/manga"):
            manga_name = parent_dir.replace("-", " ").title()
        else:
            manga_name = stem

    # Parse chapter number from filename
    m = re.search(r'[Cc](\d{1,4})', stem)
    if m:
        chapter = f"C{int(m.group(1)):03d}"
        return manga_name, chapter, anilist_id
    m = re.search(r'[Cc]hapter\s*(\d+)', stem, re.IGNORECASE)
    if m:
        chapter = f"Chapter {m.group(1)}"
        return manga_name, chapter, anilist_id
    return manga_name, stem, anilist_id


# ============================================================
# ZIP PROCESSING
# ============================================================
def process_chapter_zip(zip_path):
    """Extract ZIP, upload each page, save URLs to DB + JSON.
    Returns the number of pages uploaded.
    """
    filename = os.path.basename(zip_path)
    manga_name, chapter_number, anilist_id = parse_manga_info(zip_path)
    log.info(f"📖 Processing: {filename}")
    log.info(f"   Manga: {manga_name}")
    log.info(f"   Chapter: {chapter_number}")
    if anilist_id:
        log.info(f"   AniList ID: {anilist_id}")

    try:
        with zipfile.ZipFile(zip_path, 'r') as zf:
            # Get list of image files inside
            image_names = sorted([
                n for n in zf.namelist()
                if not n.startswith('__MACOSX') and not n.startswith('.')
                and os.path.splitext(n)[1].lower() in IMAGE_EXTENSIONS
            ])
            if not image_names:
                log.warning(f"   ⚠️  No images found in ZIP")
                return 0
            log.info(f"   Found {len(image_names)} pages")

            pages_uploaded = 0
            # Build list of pages to upload
            upload_tasks = []
            for i, img_name in enumerate(image_names, 1):
                try:
                    img_bytes = zf.read(img_name)
                except Exception as e:
                    log.warning(f"   ✗ Could not read {img_name}: {e}")
                    continue
                if len(img_bytes) < MIN_FILE_SIZE:
                    log.warning(f"   ⏭️  Skipping tiny page {i} ({len(img_bytes)} bytes)")
                    continue
                ext = os.path.splitext(img_name)[1].lower()
                page_filename = f"{manga_name.replace(' ', '_')}_{chapter_number}_p{i:03d}{ext}"
                upload_tasks.append((i, img_bytes, page_filename))

            log.info(f"   📤 Uploading {len(upload_tasks)} pages (5 parallel via proxy rotation)...")
            
            # Upload in parallel (5 at a time) — each uses a different proxy IP
            from concurrent.futures import ThreadPoolExecutor, as_completed
            
            def upload_one_page(task):
                """Upload a single page via proxy. Returns (page_num, url, size) or (page_num, None, size)."""
                page_num, img_bytes, filename = task
                for attempt in range(3):
                    url = upload_image(img_bytes, filename)
                    if url:
                        return (page_num, url, len(img_bytes))
                    time.sleep(1)  # short retry — different proxy next time
                return (page_num, None, len(img_bytes))
            
            results = []
            with ThreadPoolExecutor(max_workers=5) as executor:
                futures = {executor.submit(upload_one_page, task): task for task in upload_tasks}
                for future in as_completed(futures):
                    page_num, url, size = future.result()
                    results.append((page_num, url, size))
                    if url:
                        log.info(f"   ✅ page {page_num}/{len(image_names)} → {url[:60]}...")
                    else:
                        log.error(f"   ❌ page {page_num} failed after 3 attempts")
            
            # Sort results by page number and save to DB
            results.sort(key=lambda x: x[0])
            for page_num, url, size in results:
                if url:
                    save_to_db(
                        manga_name=manga_name,
                        chapter_number=chapter_number,
                        page_number=page_num,
                        image_url=url,
                        file_size=size,
                        anilist_id=anilist_id,
                    )
                    save_to_json_db(manga_name, chapter_number, page_num, url, anilist_id)
                    pages_uploaded += 1
            log.info(f"   ✅ Uploaded {pages_uploaded}/{len(image_names)} pages")
            return pages_uploaded
    except zipfile.BadZipFile as e:
        log.error(f"   ❌ Bad ZIP: {e}")
        return 0
    except Exception as e:
        log.error(f"   ❌ ZIP processing error: {e}")
        return 0


def delete_local_file(filepath):
    """Delete file. If it's a symlink, just unlink. If real file, remove."""
    try:
        if os.path.islink(filepath):
            os.unlink(filepath)
        else:
            os.remove(filepath)
        log.info(f"🗑️  Deleted: {filepath}")
    except Exception as e:
        log.error(f"❌ Could not delete {filepath}: {e}")


def move_to_failed(filepath):
    """Move file to FAIL_DIR."""
    try:
        import shutil
        fname = os.path.basename(filepath)
        dest = os.path.join(FAIL_DIR, fname)
        # Handle name collision
        i = 1
        while os.path.exists(dest):
            stem, ext = os.path.splitext(fname)
            dest = os.path.join(FAIL_DIR, f"{stem}_{i}{ext}")
            i += 1
        if os.path.islink(filepath):
            # Copy the target file, then remove the symlink
            target = os.readlink(filepath)
            shutil.copy2(target, dest)
            os.unlink(filepath)
        else:
            shutil.move(filepath, dest)
        log.info(f"📦 Moved to failed/: {dest}")
    except Exception as e:
        log.error(f"❌ Could not move to failed/: {e}")
        delete_local_file(filepath)


# ============================================================
# WATCH LOOP
# ============================================================
file_size_history = {}
processing_files = set()


def is_file_stable(filepath):
    try:
        current_size = Path(filepath).stat().st_size
    except FileNotFoundError:
        return False
    key = str(filepath)
    now = time.time()
    if key not in file_size_history:
        file_size_history[key] = {"size": current_size, "first_seen": now}
        return False
    history = file_size_history[key]
    if history["size"] != current_size:
        history["size"] = current_size
        history["first_seen"] = now
        return False
    if now - history["first_seen"] >= FILE_STABLE_TIME:
        return True
    return False


def process_file(filepath):
    """Process a single ZIP file."""
    if filepath in processing_files:
        return
    processing_files.add(filepath)
    try:
        if not is_file_stable(filepath):
            return
        log.info(f"🎬 Processing: {filepath}")
        pages = process_chapter_zip(filepath)
        if pages > 0:
            delete_local_file(filepath)
            file_size_history.pop(str(filepath), None)
        else:
            log.warning(f"⚠️  No pages uploaded, moving to failed/: {filepath}")
            move_to_failed(filepath)
            file_size_history.pop(str(filepath), None)
    except Exception as e:
        log.error(f"❌ Process error: {e}")
    finally:
        processing_files.discard(filepath)


def scan_and_process():
    if not os.path.exists(WATCH_DIR):
        return
    for entry in os.scandir(WATCH_DIR):
        if not entry.is_file() and not entry.is_symlink():
            continue
        ext = os.path.splitext(entry.name)[1].lower()
        if ext not in ARCHIVE_EXTENSIONS:
            continue
        try:
            size = Path(entry.path).stat().st_size
        except FileNotFoundError:
            continue
        if size < MIN_FILE_SIZE:
            continue
        process_file(entry.path)


def main():
    log.info("=" * 60)
    log.info("📚  LuffyTV Manga Uploader Starting")
    log.info("=" * 60)
    log.info(f"Watch dir:    {WATCH_DIR}")
    log.info(f"DB file:      {DB_FILE}")
    log.info(f"JSON file:    {JSON_FILE}")
    log.info(f"Image host:   {IMAGE_HOST}")
    log.info(f"Poll interval: {POLL_INTERVAL}s")
    log.info("=" * 60)
    init_db()
    log.info("👀 Watching for chapter ZIPs...")
    while True:
        try:
            scan_and_process()
        except Exception as e:
            log.error(f"Scan error: {e}")
        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
