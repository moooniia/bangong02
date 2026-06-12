"""Extract and show WPS images to understand their strategy."""
import zipfile, os, re

WPS = r"C:\Users\paz\Desktop\1212.docx"
OUT = r"C:\Users\paz\Desktop\wps_images"
os.makedirs(OUT, exist_ok=True)

with zipfile.ZipFile(WPS) as z:
    xml = z.read("word/document.xml").decode("utf-8", errors="replace")
    media = [n for n in z.namelist() if n.startswith("word/media/") and not n.endswith("/")]
    for name in media:
        data = z.read(name)
        fname = os.path.basename(name)
        with open(os.path.join(OUT, fname), "wb") as f:
            f.write(data)

# Summarize image sizes
print("Image inventory:")
files = sorted(os.listdir(OUT), key=lambda x: os.path.getsize(os.path.join(OUT, x)), reverse=True)
for fname in files:
    size = os.path.getsize(os.path.join(OUT, fname))
    print(f"  {fname:25s}  {size//1024:5d} KB")

# How many are large (likely full-page scans) vs small (stamps/icons)
sizes = [os.path.getsize(os.path.join(OUT, f)) for f in files]
large = sum(1 for s in sizes if s > 50*1024)
medium = sum(1 for s in sizes if 10*1024 < s <= 50*1024)
small = sum(1 for s in sizes if s <= 10*1024)
print(f"\n  Large (>50KB): {large}  Medium (10-50KB): {medium}  Small (<10KB): {small}")
print(f"  Saved to {OUT}")
