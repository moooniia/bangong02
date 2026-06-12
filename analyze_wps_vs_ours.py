"""Structural analysis: WPS docx vs our output."""
import zipfile, re, json, os

def extract_docx_structure(path, label):
    with zipfile.ZipFile(path) as z:
        xml = z.read("word/document.xml").decode("utf-8", errors="replace")

    # Page splits
    pages = xml.split('w:br w:type="page"')

    result = []
    for i, page_xml in enumerate(pages):
        tables = re.findall(r"<w:tbl[\s\S]*?</w:tbl>", page_xml)
        drawings = re.findall(r"<w:drawing", page_xml)
        paras = re.findall(r"<w:p[ >][\s\S]*?</w:p>", page_xml)
        texts = re.findall(r"<w:t[^>]*>([^<]*)</w:t>", page_xml)

        # Font sizes used
        sizes = re.findall(r'w:sz w:val="(\d+)"', page_xml)
        unique_sizes = sorted(set(int(s) for s in sizes))

        # Paragraph styles
        styles = re.findall(r'w:pStyle w:val="([^"]+)"', page_xml)
        unique_styles = list(dict.fromkeys(styles))[:5]

        result.append({
            "page": i + 1,
            "paragraphs": len(paras),
            "tables": len(tables),
            "images": len(drawings),
            "text_len": len("".join(texts)),
            "font_sizes": unique_sizes,
            "styles": unique_styles,
        })
    return result

WPS = r"C:\Users\paz\Desktop\1212.docx"
OURS = r"C:\Users\paz\Desktop\1212_v2.docx"

wps = extract_docx_structure(WPS, "WPS")
ours = extract_docx_structure(OURS, "OURS")

print(f"{'Page':>4} | {'WPS para/tbl/img/len':>22} | {'OURS para/tbl/img/len':>22} | WPS fonts")
print("-" * 80)
for i in range(max(len(wps), len(ours))):
    w = wps[i] if i < len(wps) else {}
    o = ours[i] if i < len(ours) else {}
    wf = str(w.get("font_sizes", []))[:20]
    print(
        f"  p{i+1:02d} | "
        f"{w.get('paragraphs',0):3d}p {w.get('tables',0):2d}t {w.get('images',0):2d}i {w.get('text_len',0):5d}c | "
        f"{o.get('paragraphs',0):3d}p {o.get('tables',0):2d}t {o.get('images',0):2d}i {o.get('text_len',0):5d}c | "
        f"{wf}"
    )

print(f"\nWPS total pages: {len(wps)}, OURS total pages: {len(ours)}")

# Specifically look at p3 (sign page) in both
print("\n=== WPS p3 styles & text sample ===")
if len(wps) >= 3:
    w3 = wps[2]
    print(f"  styles: {w3['styles']}")
    print(f"  fonts: {w3['font_sizes']}")

# Check if WPS uses text or images for signature areas
with zipfile.ZipFile(WPS) as z:
    xml = z.read("word/document.xml").decode("utf-8", errors="replace")
pages_wps = xml.split('w:br w:type="page"')
if len(pages_wps) >= 3:
    p3 = pages_wps[2]
    texts_p3 = re.findall(r"<w:t[^>]*>([^<]*)</w:t>", p3)
    drawings_p3 = re.findall(r"<w:drawing", p3)
    print(f"  WPS p3 text runs: {len(texts_p3)}, images: {len(drawings_p3)}")
    print(f"  WPS p3 text: {repr(' '.join(texts_p3)[:300])}")
