# LuffyTV Manga Pipeline — VPS Production Scripts

These are the LIVE production scripts running on the VPS (169.58.120.196) as of 2026-09-26.

## Files

| File | Purpose | Where it runs |
|------|---------|----------------|
| `mk_scraper.py` | MangaKatana scraper — v4 (parallel 4-host race + skip-done chapters) | `mk-scraper.service` on VPS |
| `skip_helper.py` | `chapter_already_uploaded()` helper — checks DB before downloading to skip already-done chapters | imported by mk_scraper |
| `upload_hosts.py` | `upload_to_imagehosting()` + `upload_to_pixelhost()` functions (CSRF flow for imagehosting.co) | imported by mk_scraper |
| `submitter.py` | Admin panel (Flask app on port 9000) — serves /api/manga/db with COALESCE(catbox_url, image_url) | `luffytv-submitter.service` |
| `manga_uploader.py` | Local sandbox uploader with same 4-host chain (catbox → imagehosting → imglink → pixelhost) | local dev only |
| `mangago_pipeline.py` | One-command scrape → upload pipeline for mangago.me manga | local dev only |
| `mangago_scraper.js` | Playwright-based mangago.me scraper (decrypts imgsrcs JS-encrypted image URLs) | local dev only |

## Upload Chain (production)

`mk_scraper.upload_image()` uses **PARALLEL race** via `ThreadPoolExecutor(max_workers=4)`:

```
4 pages uploaded concurrently
   ↓ each races 4 hosts simultaneously
   imagehosting.co → imglink.cc → catbox → pixelhost → 0x0.st
   ↓ first to return wins (others cancelled)
   ↓ catbox wins most races from VPS IP (~0.4s/page)
```

Total: 16 concurrent HTTP requests per batch. Speed: 0.4s/page (was 1.5s serial).

## Skip-Done Logic

`chapter_already_uploaded(manga_name, ch_num)` checks the DB before downloading.
Result: 140 chapters skipped in 0.006s (was 9+ hours of wasted re-processing
on every service restart).

## DB Schema

```sql
CREATE TABLE manga (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  manga_name TEXT NOT NULL,
  chapter_number TEXT NOT NULL,
  page_number INTEGER NOT NULL,
  image_url TEXT NOT NULL,        -- source URL (mangakatana)
  catbox_url TEXT,                -- uploaded URL (catbox/imghos/imglink/pixelhost)
  UNIQUE(manga_name, chapter_number, page_number)
);
```

Admin panel shows `COALESCE(NULLIF(catbox_url, ''), image_url)` — uploaded URL
when one exists, falls back to source URL otherwise.
