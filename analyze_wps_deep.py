"""Deep analysis of WPS docx structure."""
import zipfile, re

WPS = r"C:\Users\paz\Desktop\1212.docx"

with zipfile.ZipFile(WPS) as z:
    xml = z.read("word/document.xml").decode("utf-8", errors="replace")
    # List all embedded files
    names = z.namelist()

print("=== Embedded files ===")
media = [n for n in names if "media" in n]
print(f"  {len(media)} media files: {media[:8]}...")

print("\n=== Document stats ===")
paras = re.findall(r"<w:p[ >]", xml)
tables = re.findall(r"<w:tbl[ >]", xml)
drawings = re.findall(r"<w:drawing[ >]", xml)
sections = re.findall(r"<w:sectPr[ >]", xml)
page_breaks = re.findall(r'w:br w:type="page"', xml)
col_breaks = re.findall(r'w:br w:type="column"', xml)
text_runs = re.findall(r"<w:t[^>]*>([^<]*)</w:t>", xml)
total_text = "".join(text_runs)

print(f"  Paragraphs: {len(paras)}")
print(f"  Tables: {len(tables)}")
print(f"  Drawings/Images: {len(drawings)}")
print(f"  Section breaks: {len(sections)}")
print(f"  Page breaks: {len(page_breaks)}")
print(f"  Total text chars: {len(total_text)}")
print(f"  Text sample: {repr(total_text[:200])}")

print("\n=== Image sizes ===")
with zipfile.ZipFile(WPS) as z:
    for name in media[:5]:
        size = len(z.read(name))
        print(f"  {name}: {size//1024} KB")

print("\n=== Section properties (page size hints) ===")
sect_matches = re.findall(r"<w:sectPr[\s\S]*?</w:sectPr>", xml)
for i, s in enumerate(sect_matches[:3]):
    pgsize = re.search(r'w:pgSz[^/]*/>', s)
    pgmar = re.search(r'w:pgMar[^/]*/>', s)
    if pgsize:
        print(f"  Section {i}: {pgsize.group()[:100]}")

print("\n=== Drawing/image positioning (first 3) ===")
drawing_blocks = re.findall(r"<w:drawing>[\s\S]*?</w:drawing>", xml)
for i, d in enumerate(drawing_blocks[:3]):
    extent = re.search(r'a:ext cx="(\d+)" cy="(\d+)"', d)
    pos = re.search(r'wp:posOffset>(\d+)<', d)
    inline = "<wp:inline" in d
    anchor = "<wp:anchor" in d
    if extent:
        cx_emu, cy_emu = int(extent.group(1)), int(extent.group(2))
        cx_cm = cx_emu / 914400 * 2.54
        cy_cm = cy_emu / 914400 * 2.54
        print(f"  img[{i}]: {cx_cm:.1f}cm x {cy_cm:.1f}cm  inline={inline} anchor={anchor}")
