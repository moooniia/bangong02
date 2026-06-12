import json

old = json.load(open('1212_detail_full.json', encoding='utf-8'))
new = json.load(open('1212_detail_fresh.json', encoding='utf-8'))

def summarize(pages):
    print(f"{'Page':>4}  {'Blocks':>6}  {'TextLen':>8}  {'HasTable':>9}")
    for i, p in enumerate(pages):
        blocks = p.get('textblocks', [])
        total_text = sum(len((b.get('text') or '').strip()) for b in blocks
                        if (b.get('label') or '') != 'foot')
        has_table = any('<table' in (b.get('text') or '').lower() for b in blocks)
        print(f"  p{i+1:02d}  {len(blocks):>6}  {total_text:>8}  {'YES' if has_table else '-':>9}")

print("=== OLD OCR (no preprocessing) ===")
summarize(old)
print()
print("=== NEW OCR (with preprocessing) ===")
summarize(new)

# Deep dive on changed pages
print("\n=== P04 new blocks ===")
for i, b in enumerate(new[3].get('textblocks', [])):
    label = b.get('label', '?')
    text = b.get('text') or ''
    has_tbl = '<table' in text.lower()
    print(f"  [{i}] {label:8s} len={len(text):4d}  table={has_tbl}  {text[:70]!r}")

print("\n=== P11 new blocks ===")
for i, b in enumerate(new[10].get('textblocks', [])):
    label = b.get('label', '?')
    text = b.get('text') or ''
    has_tbl = '<table' in text.lower()
    print(f"  [{i}] {label:8s} len={len(text):4d}  table={has_tbl}")

print("\n=== P11 old blocks ===")
for i, b in enumerate(old[10].get('textblocks', [])):
    label = b.get('label', '?')
    text = b.get('text') or ''
    has_tbl = '<table' in text.lower()
    print(f"  [{i}] {label:8s} len={len(text):4d}  table={has_tbl}")
