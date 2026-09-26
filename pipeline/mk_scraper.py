from skip_helper import chapter_already_uploaded
from upload_hosts import upload_to_imagehosting, upload_to_pixelhost
#!/usr/bin/env python3
"""
MangaKatana Manhwa Scraper v4 (PARALLEL 4-host race) — serial uploads + ImgLink (permanent) + catbox fallback
- Downloads ALL chapters of ONE manga → uploads ALL pages → then next manga
- Uploads are SERIAL (one page at a time, not parallel)
- Upload order: imagehosting.co (primary) → imglink → catbox → pixelhost → 0x0.st
"""
import os, sys, json, re, time, sqlite3, io, random, concurrent.futures, urllib.parse, http.cookiejar
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading as _threading
_db_lock = _threading.Lock()
from datetime import datetime, timezone
import logging

DB_FILE = "/var/lib/luffytv/manga.db"
QUEUE_FILE = "/var/lib/luffytv/xcomic-queue.json"
LOG_FILE = "/var/log/mk-scraper.log"
MK_BASE = "https://mangakatana.com"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36", "Accept": "text/html,*/*"}
PROXIES = [
    "http://tickets:proxyon145@104.160.17.116:12345",
    "http://tickets:proxyon145@196.196.23.136:12345",
    "http://tickets:proxyon145@162.212.170.77:12345",
    "http://tickets:proxyon145@107.150.71.197:12345",
    "http://tickets:proxyon145@107.150.71.30:12345",
]

os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s [%(levelname)s] %(message)s", handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler(sys.stdout)])
log = logging.getLogger("mk")
_db_lock = __import__("threading").Lock()

def slugify(s): return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:80]

def init_db():
    with _db_lock:
        conn = sqlite3.connect(DB_FILE, timeout=30)
        c = conn.cursor()
        c.execute("""CREATE TABLE IF NOT EXISTS manga (id INTEGER PRIMARY KEY AUTOINCREMENT, manga_name TEXT, chapter_number TEXT, page_number INTEGER, image_url TEXT, byse_url TEXT, catbox_url TEXT, vps_url TEXT, file_size INTEGER, slug TEXT, uploaded_at TEXT, UNIQUE(manga_name, chapter_number, page_number))""")
        for col, t in [("catbox_url","TEXT"),("vps_url","TEXT"),("slug","TEXT"),("byse_url","TEXT"),("file_size","INTEGER")]:
            try: c.execute(f"ALTER TABLE manga ADD COLUMN {col} {t}")
            except: pass
        conn.commit(); conn.close()

def save_to_db(manga_name, ch, page, img_url, catbox_url, size, slug):
    with _db_lock:
        conn = sqlite3.connect(DB_FILE, timeout=30)
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO manga (manga_name, chapter_number, page_number, image_url, catbox_url, file_size, slug, uploaded_at) VALUES (?,?,?,?,?,?,?,?)",
                  (manga_name, ch, page, img_url, catbox_url, size, slug, datetime.now(timezone.utc).isoformat()))
        conn.commit(); conn.close()

def get_db_count(manga_name):
    with _db_lock:
        conn = sqlite3.connect(DB_FILE, timeout=30)
        c = conn.cursor()
        c.execute("SELECT COUNT(DISTINCT chapter_number) FROM manga WHERE manga_name=?", (manga_name,))
        n = c.fetchone()[0]; conn.close(); return n

# === IMAGE UPLOADERS (serial — one at a time) ===
def upload_to_imglink(data, filename):
    """ImgLink — permanent links, no expiration"""
    try:
        r = requests.post("https://imglink.cc/api/upload", timeout=20,
            files={"file": (filename, io.BytesIO(data), "image/webp")})
        if r.ok:
            j = r.json()
            url = j.get("images", [{}])[0].get("url")
            if url and url.startswith("https://"):
                return url
    except: pass
    return None

def upload_to_catbox(data, filename):
    try:
        r = requests.post("https://catbox.moe/user/api.php", timeout=20,
            files={"fileToUpload": (filename, io.BytesIO(data), "image/webp")},
            data={"reqtype": "fileupload", "userhash": ""})
        if r.ok and r.text.startswith("https://"): return r.text.strip()
    except: pass
    return None

def upload_to_0x0(data, filename):
    try:
        r = requests.post("https://0x0.st", timeout=20,
            files={"file": (filename, io.BytesIO(data), "image/webp")})
        if r.ok and r.text.startswith("https://"): return r.text.strip()
    except: pass
    return None

def upload_image(data, filename):
    # PARALLEL chain: fire all 4 hosts simultaneously, return the FIRST winner.
    # Much faster than serial - total time = fastest host instead of sum of all hosts.
    hosts = [
        ("imagehosting", upload_to_imagehosting, (data, filename, log)),
        ("imglink",      upload_to_imglink,      (data, filename)),
        ("catbox",       upload_to_catbox,       (data, filename)),
        ("pixelhost",    upload_to_pixelhost,    (data, filename, log)),
    ]
    
    with ThreadPoolExecutor(max_workers=4) as ex:
        futures = {ex.submit(fn, *args): name for name, fn, args in hosts}
        for fut in as_completed(futures):
            name = futures[fut]
            try:
                url = fut.result()
                if url:
                    for f in futures:
                        f.cancel()
                    return url, name
            except Exception as e:
                if log: log.warning(name + " upload error: " + str(e))
                continue
    return None, None

def create_session():
    s = requests.Session()
    s.headers.update(HEADERS)
    s.cookies = http.cookiejar.LWPCookieJar()
    try: s.get(f"{MK_BASE}/", timeout=10)
    except: pass
    return s

# === SEARCH ===
def search_mk(session, title):
    try:
        proxy = random.choice(PROXIES)
        ps = {"http": proxy, "https": proxy}
        r = requests.get(f"{MK_BASE}/", params={"search": title}, timeout=15, headers=HEADERS, proxies=ps)
        if not r.ok or len(r.text) < 100:
            r = session.get(f"{MK_BASE}/", params={"search": title}, timeout=15)
        if not r.ok: return None, None
        matches = re.findall(r'mangakatana\.com/manga/([a-z0-9-]+\.\d+)', r.text)
        seen = set(); unique = []
        for m in matches:
            if m not in seen: seen.add(m); unique.append(m)
        if not unique: return None, None
        title_lower = title.lower().strip()
        title_slug = re.sub(r"[^a-z0-9]+", "-", title_lower).strip("-")
        best = None; best_score = 0
        for slug_id in unique:
            slug_part = slug_id.rsplit(".", 1)[0]
            title_words = set(title_lower.split())
            slug_words = set(slug_part.split("-"))
            overlap = len(title_words & slug_words)
            score = overlap / max(len(title_words), 1)
            if score > best_score: best_score = score; best = slug_id
        if best and best_score >= 0.4: return best, title
        for slug_id in unique:
            slug_part = slug_id.rsplit(".", 1)[0]
            if title_slug in slug_part or slug_part in title_slug: return slug_id, title
        return unique[0], title
    except Exception as e:
        log.error(f"   Search failed: {e}"); return None, None

# === CHAPTERS ===
def get_chapters(session, slug_id):
    try:
        proxy = random.choice(PROXIES)
        r = requests.get(f"{MK_BASE}/manga/{slug_id}", timeout=15, headers=HEADERS, proxies={"http": proxy, "https": proxy})
        if not r.ok or len(r.text) < 100:
            r = session.get(f"{MK_BASE}/manga/{slug_id}", timeout=15)
        if not r.ok: return []
        chapters = re.findall(r'/manga/[a-z0-9-]+\.\d+/(c\d+)', r.text)
        seen = set(); result = []
        for ch in chapters:
            if ch not in seen: seen.add(ch); result.append(ch)
        return result
    except Exception as e:
        log.error(f"   Chapter list failed: {e}"); return []

# === PAGE URLS (via proxy — token URLs need same IP as download) ===
def get_page_urls(session, slug_id, chapter):
    """Returns (page_urls, proxy_used) — same proxy needed for downloads"""
    try:
        url = f"{MK_BASE}/manga/{slug_id}/{chapter}"
        proxy = random.choice(PROXIES)
        ps = {"http": proxy, "https": proxy}
        r = requests.get(url, timeout=15, headers=HEADERS, proxies=ps)
        if not r.ok or len(r.text) < 100:
            r = session.get(url, timeout=15)
            proxy = None  # direct connection
        if not r.ok: return [], None
        urls = re.findall(r"https://i\d+\.mangakatana\.com/token/[^\"'\s,]+", r.text)
        seen = set(); result = []
        for u in urls:
            if u not in seen: seen.add(u); result.append(u)
        return result, proxy
    except Exception as e:
        log.error(f"   Page URLs failed: {e}"); return [], None

# === DOWNLOAD (via proxy — same IP that fetched chapter page) ===
def download_image(session, url, proxy=None, timeout=15):
    """Download image using the SAME proxy that fetched the chapter page"""
    ps = {"http": proxy, "https": proxy} if proxy else None
    try:
        r = requests.get(url, timeout=timeout, headers={"Referer": MK_BASE, "Accept": "image/*,*/*", "User-Agent": HEADERS["User-Agent"]}, proxies=ps, cookies=session.cookies)
        if r.ok and len(r.content) > 100:
            return r.content
        else:
            log.debug(f"      DL fail: {r.status_code} size={len(r.content)} url={url[:60]}")
    except Exception as e:
        log.debug(f"      DL error: {e} url={url[:60]}")
    # Try ALL proxies
    for alt_proxy in PROXIES:
        try:
            r = requests.get(url, timeout=10, headers={"Referer": MK_BASE, "Accept": "image/*,*/*", "User-Agent": HEADERS["User-Agent"]}, proxies={"http": alt_proxy, "https": alt_proxy}, cookies=session.cookies)
            if r.ok and len(r.content) > 100:
                return r.content
        except:
            pass
    return None

# === MAIN — SERIAL: one manga → all chapters → all pages → next manga ===
def process_one_manga(session, entry):
    title = entry.get("title"); slug = slugify(title)
    log.info("=" * 60)
    log.info(f"📚 Manhwa: {title} (AniList {entry.get('anilist_id')})")
    log.info("=" * 60)

    log.info("🔍 Step 1: Searching mangakatana...")
    slug_id, display_title = search_mk(session, title)
    if not slug_id:
        log.error("❌ Not found on mangakatana"); return False
    log.info(f"   ✅ Found: {display_title} ({slug_id})")

    chapters = get_chapters(session, slug_id)
    log.info(f"   📋 {len(chapters)} chapters available")
    if not chapters:
        log.error("❌ No chapters found"); return False

    consecutive_fail = 0; total_pages = 0
    for i, ch in enumerate(chapters, 1):
        ch_num = f"C{i:03d}"
        # SKIP if chapter already in DB — check BEFORE downloading to save time
        if chapter_already_uploaded(title, ch_num):
            log.info(f"      SKIP Chapter {i} ({ch_num}) already in DB")
            continue
        log.info(f"   [{i}/{len(chapters)}] {ch}")
        page_urls, chapter_proxy = get_page_urls(session, slug_id, ch)
        if not page_urls:
            log.warning("      ⚠️ No pages")
            consecutive_fail += 1
            if consecutive_fail >= 3: log.warning("      🚫 3 fails — skip manga"); break
            continue
        consecutive_fail = 0
        log.info(f"      ⬇️  Downloading {len(page_urls)} pages...")

        # DOWNLOAD all pages (3 parallel — same proxy needed for token match)
        pages_data = {}
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as ex:
            futures = {ex.submit(download_image, session, url, chapter_proxy): (idx, url) for idx, url in enumerate(page_urls)}
            for f in concurrent.futures.as_completed(futures):
                idx, url = futures[f]
                data = f.result()
                if data: pages_data[idx] = (data, url)

        if not pages_data:
            log.warning("      ⚠️ All downloads failed")
            consecutive_fail += 1
            if consecutive_fail >= 3: log.warning("      🚫 3 fails — skip manga"); break
            continue

        # UPLOAD all pages IN PARALLEL — 4 pages at once, each racing 4 hosts internally
        log.info(f"      📤 Uploading {len(pages_data)} pages PARALLEL (4 pages × 4 hosts race)...")
        uploaded = 0
        uploaded_lock = __import__("threading").Lock()
        
        def upload_one_page(idx_data_tuple):
            nonlocal uploaded
            idx, (data, orig_url) = idx_data_tuple
            filename = f"{slug}_{ch_num}_p{idx+1:03d}.webp"
            try:
                catbox_url, host = upload_image(data, filename)
                if catbox_url:
                    try:
                        with _db_lock:
                            save_to_db(title, ch_num, idx + 1, orig_url, catbox_url, len(data), slug)
                        with uploaded_lock:
                            uploaded += 1
                    except Exception as e:
                        log.warning(f"         DB save failed for page {idx+1}: {e}")
                else:
                    log.warning(f"         Upload failed for page {idx+1}")
            except Exception as e:
                log.warning(f"         Page {idx+1} error: {e}")
        
        # Sort by page index so uploads happen in order
        sorted_pages = sorted(pages_data.items())
        with ThreadPoolExecutor(max_workers=4) as ex:
            list(ex.map(upload_one_page, sorted_pages))

        total_pages += uploaded
        log.info(f"      ✅ Chapter {i}: {uploaded}/{len(pages_data)} pages uploaded")
        time.sleep(1)  # delay between chapters

    log.info(f"🎉 FINISHED: {title} — {get_db_count(title)} chapters in DB, {total_pages} pages uploaded")
    return True

def main():
    log.info("=" * 60)
    log.info("🔥 MangaKatana Manhwa Scraper v4 (PARALLEL 4-host race) — Serial Uploads + ImgLink")
    log.info("=" * 60)
    init_db()

    if not os.path.exists(QUEUE_FILE):
        log.error("No queue file"); return
    with open(QUEUE_FILE) as f:
        data = json.load(f)
    queue = data.get("queue", [])
    current_index = data.get("current_index", 0)
    if not queue:
        log.error("Queue empty"); return

    log.info(f"📚 Queue: {len(queue)} manhwa, starting at index {current_index}")
    session = create_session()

    while current_index < len(queue):
        entry = queue[current_index]
        log.info(f"\n{'='*60}\n📖 STARTING MANGA {current_index + 1}/{len(queue)}: {entry.get('title')}\n{'='*60}")
        ok = process_one_manga(session, entry)
        current_index += 1
        with open(QUEUE_FILE, "w") as f:
            json.dump({"queue": queue, "current_index": current_index, "total": len(queue)}, f, indent=2, ensure_ascii=False)
        log.info(f"📊 Progress: {current_index}/{len(queue)} manga done")
        if not ok: log.warning("⚠️ Failed — moving to next manga")
        if current_index % 10 == 0: session = create_session()
        time.sleep(2)

    log.info("🏁 All manga done!")

if __name__ == "__main__":
    main()
