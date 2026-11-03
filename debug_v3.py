import json, sys, os, tempfile, shutil
sys.path.insert(0, '/home/toolbox/backend')
os.chdir('/home/toolbox/backend')
PDF='/home/toolbox/uploads/1212.pdf'
CACHE='/home/toolbox/1212_detail_300dpi.json'

from volc_ocr import (
    _get_page_emu_size, _seal_extract_enabled, _get_pdf_page_image,
    _embed_extracted_seals, _embed_signatures, _embed_ocr_image_blocks,
    _page_has_image_blocks, _should_render_snapshot, _detect_dynamic_watermarks,
    _docx_mode, pdf_page_count
)
from seal_utils import is_signature_page, SEAL_EXTRACT_DPI

details = json.load(open(CACHE, encoding='utf-8'))
mode = _docx_mode(pdf_page_count(PDF))
watermarks = _detect_dynamic_watermarks(details)
total = len(details)
cache_dir = tempfile.mkdtemp()

print('mode=%s pages=%d' % (mode, total))
for pi, page in enumerate(details):
    is_sig = is_signature_page(page, pi, total)
    has_img = _page_has_image_blocks(page)
    snap = _should_render_snapshot(page, watermarks, is_sig, mode, PDF, pi)
    pg_w, pg_h = _get_page_emu_size(PDF, pi)
    print('p%02d: sig=%s img=%s snap=%s pg_emu=%dx%d' % (pi+1, is_sig, has_img, snap, pg_w, pg_h))
    if is_sig:
        hi = _get_pdf_page_image(PDF, pi, cache_dir, dpi=SEAL_EXTRACT_DPI)
        print('  hi_res=%s' % hi)
        if hi:
            import cv2
            img = cv2.imread(hi)
            print('  image shape=%s' % str(img.shape if img is not None else None))
            from seal_utils import extract_red_seals_from_image
            import os
            seal_dir = os.path.join(cache_dir, 'seals')
            seals = extract_red_seals_from_image(hi, seal_dir)
            print('  seals=%d' % len(seals))

shutil.rmtree(cache_dir)
