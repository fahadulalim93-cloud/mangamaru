"""Helper to check if chapter already in DB — used by mk_scraper.py to skip done chapters."""
import sqlite3

DB_FILE = "/var/lib/luffytv/manga.db"

def chapter_already_uploaded(manga_name, ch_num):
    """Returns True if this chapter already has at least 1 page in DB."""
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute(
            "SELECT COUNT(DISTINCT page_number) FROM manga WHERE manga_name = ? AND chapter_number = ?",
            (manga_name, ch_num)
        )
        count = c.fetchone()[0]
        conn.close()
        return count > 0
    except Exception:
        return False
