"""imagehosting.co + pixelhost upload functions for mk_scraper.
Imported by mk_scraper.py — imagehosting.co is primary upload host.
"""
import re, requests

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/125.0.0.0 Safari/537.36"

IMAGEHOSTING_HOME = "https://imagehosting.co/en"
IMAGEHOSTING_API = "https://imagehosting.co/api/upload.php"

PIXELHOST_API = "https://pixelhost.fun/api/upload"


def upload_to_imagehosting(data, filename, log=None):
    """Upload to imagehosting.co. Returns the i.imghos.co CDN URL or None.
    Needs CSRF token + PHPSESSID cookie from visiting homepage first.
    """
    try:
        s = requests.Session()
        s.headers["User-Agent"] = UA
        r = s.get(IMAGEHOSTING_HOME, timeout=15)
        m = re.search(r"csrfToken\s*=\s*['\"]([a-f0-9]+)['\"]", r.text)
        if not m:
            if log: log.warning("imagehosting.co: CSRF token not found")
            return None
        token = m.group(1)
        r = s.post(
            IMAGEHOSTING_API,
            headers={
                "X-CSRF-Token": token,
                "Referer": IMAGEHOSTING_HOME,
                "Origin": "https://imagehosting.co",
            },
            files={"images": (filename, data, "image/jpeg")},
            data={"csrf_token": token},
            timeout=60,
        )
        if r.status_code == 200:
            j = r.json()
            results = j.get("results", [])
            if results and results[0].get("success"):
                return results[0].get("url")
        return None
    except Exception as e:
        if log: log.warning("imagehosting.co error: " + str(e))
        return None


def upload_to_pixelhost(data, filename, log=None):
    """Upload to pixelhost.fun. Returns URL or None."""
    try:
        r = requests.post(
            PIXELHOST_API,
            headers={"User-Agent": UA, "Accept": "application/json"},
            files={"files": (filename, data, "image/jpeg")},
            timeout=60,
        )
        if r.status_code == 200:
            j = r.json()
            if j.get("success"):
                return j.get("url") or j.get("direct")
        return None
    except Exception as e:
        if log: log.warning("pixelhost.fun error: " + str(e))
        return None
