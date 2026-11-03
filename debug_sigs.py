import json, sys, os, tempfile, shutil
sys.path.insert(0, '/home/toolbox/backend')
os.chdir('/home/toolbox/backend')
PDF='/home/toolbox/uploads/1212.pdf'
import cv2
from seal_utils import extract_red_seals_from_image, extract_signature_areas, SEAL_EXTRACT_DPI
from volc_ocr import _get_pdf_page_image
import json

details = json.load(open('/home/toolbox/1212_detail_300dpi.json', encoding='utf-8'))
cache_dir = tempfile.mkdtemp()

# Check p12 (index 11) - last page
pi = 11
page = details[pi]
hi = _get_pdf_page_image(PDF, pi, cache_dir, dpi=SEAL_EXTRACT_DPI)
print('p12 hi_res:', hi)
img = cv2.imread(hi)
print('image shape:', img.shape)

seal_dir = os.path.join(cache_dir, 'seals12')
seals = extract_red_seals_from_image(hi, seal_dir)
print('seals:', len(seals), [(s['x'],s['y'],s['w'],s['h']) for s in seals])

sig_dir = os.path.join(cache_dir, 'sigs12')
ocr_blocks = page.get('textblocks', [])
sigs = extract_signature_areas(img, ocr_blocks=ocr_blocks, out_dir=sig_dir)
print('signatures:', len(sigs), [(s['x'],s['y'],s['w'],s['h']) for s in sigs])

shutil.rmtree(cache_dir)
