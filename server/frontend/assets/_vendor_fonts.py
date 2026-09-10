"""Download Playfair Display, Noto Sans SC, and Tabler Icons webfont for self-hosting."""
import os
import re
import urllib.request

ROOT = os.path.dirname(os.path.abspath(__file__))
FONT_DIR = os.path.join(ROOT, "fonts")
ICON_DIR = os.path.join(ROOT, "icons")
os.makedirs(FONT_DIR, exist_ok=True)
os.makedirs(ICON_DIR, exist_ok=True)

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
)
proxy = os.environ.get("HTTPS_PROXY") or "http://127.0.0.1:7892"
opener = urllib.request.build_opener(
    urllib.request.ProxyHandler({"http": proxy, "https": proxy})
)


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    last = None
    for attempt in range(5):
        try:
            with opener.open(req, timeout=60) as r:
                return r.read()
        except Exception as e:
            last = e
            import time
            time.sleep(1.5 * (attempt + 1))
    raise last


def vendor_google_fonts():
    css_url = (
        "https://fonts.googleapis.com/css2"
        "?family=Playfair+Display:wght@700;900"
        "&family=Noto+Sans+SC:wght@400;500;700"
        "&display=swap"
    )
    css = get(css_url).decode("utf-8")
    urls = sorted(set(re.findall(r"url\((https://[^)]+)\)", css)))
    print("google font files", len(urls))
    mapping = {}
    for i, url in enumerate(urls, 1):
        ext = url.split(".")[-1].split("?")[0]
        name = "gf-%03d.%s" % (i, ext)
        dest = os.path.join(FONT_DIR, name)
        if not os.path.isfile(dest):
            open(dest, "wb").write(get(url))
        mapping[url] = "/assets/fonts/" + name
        print(" ", name, os.path.getsize(dest))
    for old, new in mapping.items():
        css = css.replace(old, new)
    css = re.sub(r"https://fonts\.gstatic\.com[^)]*", "", css)
    out = os.path.join(FONT_DIR, "fonts.css")
    open(out, "w", encoding="utf-8").write(css)
    print("wrote", out, "bytes", os.path.getsize(out))


def vendor_tabler():
    css_url = "https://cdn.jsdelivr.net/npm/@tabler/icons-webfont@latest/dist/tabler-icons.min.css"
    # also try non-dist path used by the site
    tried = [
        "https://cdn.jsdelivr.net/npm/@tabler/icons-webfont@latest/tabler-icons.min.css",
        css_url,
    ]
    css = None
    base = None
    for u in tried:
        try:
            css = get(u).decode("utf-8")
            base = u.rsplit("/", 1)[0] + "/"
            print("tabler css from", u)
            break
        except Exception as e:
            print("fail", u, e)
    if css is None:
        raise SystemExit("could not fetch tabler css")
    urls = sorted(set(re.findall(r"url\((?:['\"]?)([^)'\"]+)(?:['\"]?)\)", css)))
    print("tabler refs", urls)
    for ref in urls:
        if ref.startswith("data:"):
            continue
        abs_url = ref if ref.startswith("http") else urllib.request.urljoin(base, ref)
        fname = os.path.basename(ref.split("?")[0])
        dest = os.path.join(ICON_DIR, fname)
        if not os.path.isfile(dest):
            open(dest, "wb").write(get(abs_url))
        print(" ", fname, os.path.getsize(dest))
        css = css.replace(ref, fname)
    out = os.path.join(ICON_DIR, "tabler-icons.min.css")
    open(out, "w", encoding="utf-8").write(css)
    print("wrote", out)


if __name__ == "__main__":
    vendor_google_fonts()
    vendor_tabler()
    print("done")
