#!/usr/bin/env python3
"""
LuffyTV MangaGo Pipeline (scrape → upload, one command)
=======================================================
Runs the mangago_scraper.js to download all chapters of a manga,
then immediately uploads each page (catbox → imagehosting.co → imglink.cc → pixelhost.fun),
saves URLs to manga.db.

If catbox returns HTTP 412 (IP rate-limited), uploads fall through to the
3 user-specified hosts in order. To re-enable catbox as primary,
set CATBOX_USERHASH env var from a free catbox account.

Usage:
  python3 mangago_pipeline.py <manga_slug_or_url> [--max-chapters N] [--start N]

Examples:
  python3 mangago_pipeline.py crocodile
  python3 mangago_pipeline.py beyblade_burst --max-chapters 5
  python3 mangago_pipeline.py https://www.mangago.me/read-manga/one_piece/

Output:
  /root/downloads/manga/<slug>/<slug>_ch<NN>.zip   (downloaded chapters)
  manga.db                                         (uploaded page URLs)
"""
import os
import re
import sys
import json
import time
import sqlite3
import zipfile
import logging
import subprocess
import argparse
from pathlib import Path
from datetime import datetime, timezone

# Reuse uploader's config + functions
HERE = os.path.dirname(os.path.abspath(__file__))
UPLOAD_SCRIPT = os.path.join(HERE, "manga_uploader.py")
SCRAPE_SCRIPT = os.path.join(HERE, "mangago_scraper.js")

# Output dirs — match the uploader's expected watch dir
WATCH_DIR = os.environ.get("MANGA_WATCH_DIR", "/root/downloads/manga")
DB_FILE = os.environ.get("MANGA_DB_FILE", "/var/lib/luffytv/manga.db")
JSON_FILE = os.environ.get("MANGA_JSON_FILE", "/var/lib/luffytv/manga.json")
SEEN_FILE = os.environ.get("MANGA_SEEN_FILE", "/var/lib/luffytv/manga-seen.json")

os.makedirs(WATCH_DIR, exist_ok=True)
os.makedirs(os.path.dirname(DB_FILE), exist_ok=True) if os.path.dirname(DB_FILE) else None

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger("mangago-pipeline")


def slugify(name):
    s = re.sub(r'[^\w\s-]', '', name.lower())
    return re.sub(r'[\s_-]+', '-', s).strip('-')[:80] or "unknown-manga"


def slug_from_input(input_str):
    m = re.search(r'read-manga/([^/]+)/?', input_str)
    if m:
        return m.group(1)
    return input_str.replace('https://www.mangago.me/', '').replace('/', '').strip()


def ensure_db():
    """Make sure manga.db schema exists."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS manga (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            manga_name TEXT NOT NULL,
            chapter_number TEXT NOT NULL,
            page_number INTEGER NOT NULL,
            image_url TEXT NOT NULL,
            anilist_id INTEGER,
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)
    conn.commit()
    conn.close()


def save_page(manga_name, chapter, page_num, image_url, anilist_id=None):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute(
        "INSERT INTO manga (manga_name, chapter_number, page_number, image_url, anilist_id) VALUES (?, ?, ?, ?, ?)",
        (manga_name, chapter, page_num, image_url, anilist_id),
    )
    conn.commit()
    conn.close()

    # Mirror to JSON
    try:
        with open(JSON_FILE, "r") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        data = {}
    entry = data.setdefault(manga_name, {}).setdefault(chapter, {})
    entry[f"page_{page_num:03d}"] = image_url
    with open(JSON_FILE, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def upload_one_zip(zip_path, manga_name, uploader_mod):
    """Extract ZIP, upload each page (catbox → imgur → freeimage → 8upload), save URLs to DB."""
    # Parse chapter number from filename (e.g. crocodile_ch01.zip → C01)
    fn = os.path.basename(zip_path)
    m = re.search(r'ch(\d+)', fn, re.IGNORECASE)
    chapter = f"C{int(m.group(1)):03d}" if m else "C001"

    log.info(f"  📦 Extracting {fn}...")
    extract_dir = os.path.join(os.path.dirname(zip_path), f".extract_{fn}")
    os.makedirs(extract_dir, exist_ok=True)
    try:
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(extract_dir)
    except Exception as e:
        log.error(f"  ✗ Failed to extract {fn}: {e}")
        return 0

    # Sort pages by name
    pages = sorted([os.path.join(extract_dir, p) for p in os.listdir(extract_dir)])
    pages = [p for p in pages if os.path.isfile(p)]

    if not pages:
        log.error(f"  ✗ No pages in {fn}")
        return 0

    log.info(f"  📤 Uploading {len(pages)} pages (catbox → imagehosting.co → imglink.cc → pixelhost.fun)...")
    uploaded = 0
    for i, page_path in enumerate(pages, 1):
        try:
            with open(page_path, "rb") as f:
                data = f.read()
            # Use the uploader's chain (catbox first)
            url = uploader_mod.upload_image(data, os.path.basename(page_path))
            if url:
                save_page(manga_name, chapter, i, url)
                uploaded += 1
                if i % 5 == 0 or i == len(pages):
                    log.info(f"    [{i}/{len(pages)}] → {url}")
            else:
                log.warning(f"    [{i}/{len(pages)}] ✗ all 4 hosts failed")
        except Exception as e:
            log.error(f"    [{i}/{len(pages)}] ✗ error: {e}")

    # Cleanup extracted files + the zip
    try:
        import shutil
        shutil.rmtree(extract_dir)
        os.remove(zip_path)
    except Exception:
        pass

    log.info(f"  ✓ {fn}: {uploaded}/{len(pages)} pages uploaded")
    return uploaded


def load_uploader_module():
    """Load manga_uploader.py as a module — set env defaults first so it doesn't try /root paths."""
    os.environ.setdefault("MANGA_WATCH_DIR", WATCH_DIR)
    os.environ.setdefault("MANGA_FAIL_DIR", os.path.join(WATCH_DIR, "failed"))
    os.environ.setdefault("MANGA_DB_FILE", DB_FILE)
    os.environ.setdefault("MANGA_JSON_FILE", JSON_FILE)
    os.environ.setdefault("MANGA_SEEN_FILE", SEEN_FILE)
    os.environ.setdefault("MANGA_LOG_FILE", os.path.join(WATCH_DIR, "uploader.log"))
    # Make sure fail dir + log dir exist before importer runs makedirs on them
    os.makedirs(os.environ["MANGA_FAIL_DIR"], exist_ok=True)
    os.makedirs(os.path.dirname(os.environ["MANGA_LOG_FILE"]), exist_ok=True)

    import importlib.util
    spec = importlib.util.spec_from_file_location("manga_uploader_mod", UPLOAD_SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("manga", help="mangago.me slug or URL")
    ap.add_argument("--max-chapters", type=int, default=None)
    ap.add_argument("--start", type=int, default=0)
    ap.add_argument("--out", default=WATCH_DIR, help="where to put downloaded ZIPs")
    args = ap.parse_args()

    slug = slug_from_input(args.manga)
    manga_name = slug.replace('_', ' ').title()
    out_dir = os.path.join(args.out, slug)
    os.makedirs(out_dir, exist_ok=True)

    ensure_db()

    # ---------- Step 1: Scrape ----------
    log.info(f"\n{'#'*60}")
    log.info(f"#  Scraping: {manga_name} ({slug})")
    log.info(f"{'#'*60}")
    cmd = ["node", SCRAPE_SCRIPT, args.manga, "--out", args.out]
    if args.max_chapters:
        cmd += ["--max-chapters", str(args.max_chapters)]
    if args.start:
        cmd += ["--start", str(args.start)]
    log.info(f"Run: {' '.join(cmd)}")
    r = subprocess.run(cmd, capture_output=False, timeout=7200)
    if r.returncode != 0:
        log.error(f"Scraper failed (exit {r.returncode})")
        sys.exit(1)

    # ---------- Step 2: Find all generated ZIPs ----------
    zips = sorted([os.path.join(out_dir, f) for f in os.listdir(out_dir)
                   if f.endswith(".zip")])
    if not zips:
        log.error("No ZIPs produced by scraper — nothing to upload")
        sys.exit(1)
    log.info(f"\n{'#'*60}")
    log.info(f"#  Uploading {len(zips)} chapters from {out_dir}")
    log.info(f"{'#'*60}")

    # ---------- Step 3: Upload each chapter immediately ----------
    uploader_mod = load_uploader_module()
    total_pages = 0
    for i, z in enumerate(zips, 1):
        log.info(f"\n[{i}/{len(zips)}] {os.path.basename(z)}")
        total_pages += upload_one_zip(z, manga_name, uploader_mod)

    log.info(f"\n{'='*60}")
    log.info(f"✅ Done. {len(zips)} chapters, {total_pages} pages uploaded.")
    log.info(f"   Manga: {manga_name}")
    log.info(f"   DB:    {DB_FILE}")
    log.info(f"   JSON:  {JSON_FILE}")
    log.info(f"{'='*60}")


if __name__ == "__main__":
    main()
