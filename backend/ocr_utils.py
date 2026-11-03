"""OCR 优化 — 针对手机截图、扫描件，尽量让行政人员看得懂。"""
import difflib
import os
import re
import subprocess
import tempfile

import cv2
import numpy as np
import pytesseract
from PIL import Image

# 单块最大高度，超长截图切块识别
CHUNK_HEIGHT = 2000
OVERLAP = 120
MIN_SCALE_TARGET = 2000


def clean_ocr_text(text):
    """去掉中文之间的多余空格，合并空行。"""
    if not text:
        return ''
    text = re.sub(r'(?<=[\u4e00-\u9fff])\s+(?=[\u4e00-\u9fff])', '', text)
    text = re.sub(r'[ \t]+\n', '\n', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def _load_bgr(path):
    img = cv2.imread(path)
    if img is not None:
        return img
    pil = Image.open(path).convert('RGB')
    return cv2.cvtColor(np.array(pil), cv2.COLOR_RGB2BGR)


def _preprocess(bgr):
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape

    # 深色背景截图（暗色模式聊天/App截图）反色，统一转成深字浅底，
    # 否则下面针对"白底黑字"调的二值化参数会让暗色背景图识别全乱码
    if gray.mean() < 115:
        gray = 255 - gray

    # 表情符号/彩色图标饱和度明显高于普通文字，Tesseract认不出这些彩色字形，
    # 还会把它们旁边的文字一起带歪。涂成背景色直接抹掉，宁可丢表情也别带歪文字。
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    sat_mask = hsv[:, :, 1] > 90
    if sat_mask.any():
        gray[sat_mask] = 255  # 上面已统一转成浅底，背景色填白即可

    # 小图放大，提升小字识别率
    if max(h, w) < MIN_SCALE_TARGET:
        scale = MIN_SCALE_TARGET / max(h, w)
        gray = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)

    # 去噪很慢（大图尤其明显），原图已经够大/够清晰（手机截图，不是糊照片）时跳过，省时间
    if max(gray.shape) < 2400:
        gray = cv2.fastNlMeansDenoising(gray, None, 6, 7, 21)

    # 二值化（适合白底黑字截图）
    binary = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY, 31, 12,
    )
    return binary


def _score_text(text):
    """越高越好 — 用中文占比衡量可读性。"""
    if not text:
        return 0
    compact = re.sub(r'\s+', '', text)
    if not compact:
        return 0
    cjk = sum(1 for c in compact if '\u4e00' <= c <= '\u9fff')
    return cjk / len(compact)


LOW_CONF_WORD_THRESHOLD = 75  # 单词置信度低于这个值，大概率是认错的字


def _text_and_conf_from_data(data):
    """把 image_to_data 的逐词结果按行拼回文本，同时算出整体质量信号。

    光看平均置信度会被一大堆没问题的常见字拉高（被几个认错的字拖累不明显），
    实测发现真正认错的字置信度并不是低到离谱，但明显低于周围正常识别的字，
    所以额外算一个"低置信度词占比"，更容易揪出夹在一段好文字里的零星错字。
    """
    n = len(data.get('text', []))
    groups = {}
    order = []
    confs = []
    for i in range(n):
        word = (data['text'][i] or '').strip()
        if not word:
            continue
        key = (data['block_num'][i], data['par_num'][i], data['line_num'][i])
        if key not in groups:
            groups[key] = []
            order.append(key)
        groups[key].append(word)
        try:
            c = float(data['conf'][i])
            if c >= 0:
                confs.append(c)
        except (TypeError, ValueError):
            pass
    text = '\n'.join(' '.join(groups[k]) for k in order)
    mean_conf = sum(confs) / len(confs) if confs else 0.0
    low_conf_ratio = (
        sum(1 for c in confs if c < LOW_CONF_WORD_THRESHOLD) / len(confs) if confs else 0.0
    )
    return clean_ocr_text(text), mean_conf, low_conf_ratio


def _ocr_pil(pil_img, lang='chi_sim'):
    best_text = ''
    best_score = -1.0
    best_conf = 0.0
    best_low_ratio = 0.0
    for psm in (6, 4, 3, 11):
        config = f'--psm {psm} --oem 1'
        try:
            data = pytesseract.image_to_data(pil_img, lang=lang, config=config, output_type=pytesseract.Output.DICT)
            cleaned, conf, low_ratio = _text_and_conf_from_data(data)
            score = _score_text(cleaned)
            if score > best_score:
                best_score = score
                best_text = cleaned
                best_conf = conf
                best_low_ratio = low_ratio
            if best_score >= 0.45:
                break
        except Exception:
            continue
    return best_text, best_conf, best_low_ratio


def _ocr_array(binary, lang='chi_sim'):
    return _ocr_pil(Image.fromarray(binary), lang)


def _dedupe_chunk_overlap(parts):
    """切块识别时 OVERLAP 区域会被两块各识别一次，相邻块衔接处去掉重复行。"""
    if not parts:
        return ''
    lines = [l for l in parts[0].split('\n') if l.strip()]
    for part in parts[1:]:
        cur = [l for l in part.split('\n') if l.strip()]
        max_check = min(4, len(lines), len(cur))
        overlap_n = 0
        for n in range(max_check, 0, -1):
            tail = ''.join(lines[-n:])
            head = ''.join(cur[:n])
            if tail and difflib.SequenceMatcher(None, tail, head).ratio() > 0.85:
                overlap_n = n
                break
        lines.extend(cur[overlap_n:])
    return '\n'.join(lines)


def ocr_image(image_path, lang='chi_sim'):
    """返回 (text, mean_confidence, low_conf_ratio)。"""
    binary = _preprocess(_load_bgr(image_path))
    h, w = binary.shape

    # 超长截图切块，避免 Tesseract 整图识别崩溃
    if h > CHUNK_HEIGHT:
        parts = []
        confs = []
        low_ratios = []
        y = 0
        while y < h:
            y2 = min(y + CHUNK_HEIGHT, h)
            chunk = binary[y:y2, 0:w]
            part, conf, low_ratio = _ocr_array(chunk, lang)
            if part:
                parts.append(part)
                confs.append(conf)
                low_ratios.append(low_ratio)
            if y2 >= h:
                break
            y = y2 - OVERLAP
        text = clean_ocr_text(_dedupe_chunk_overlap(parts))
        mean_conf = sum(confs) / len(confs) if confs else 0.0
        low_ratio = sum(low_ratios) / len(low_ratios) if low_ratios else 0.0
        return text, mean_conf, low_ratio

    return _ocr_array(binary, lang)


def _ocr_document_page(image_path, lang='chi_sim'):
    """合同/扫描页快速识别 — 不做多模式重试，适合批量 PDF。"""
    bgr = _load_bgr(image_path)
    if bgr is None:
        return ''
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape
    if max(h, w) > 2200:
        scale = 2200 / max(h, w)
        gray = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    config = '--psm 6 --oem 1'
    raw = pytesseract.image_to_string(gray, lang=lang, config=config)
    return clean_ocr_text(raw)


def _pdf_to_page_images(pdf_path, tmp, dpi=150, timeout=180):
    base = os.path.join(tmp, 'page')
    subprocess.run(
        ['pdftoppm', '-png', '-r', str(dpi), pdf_path, base],
        capture_output=True, text=True, timeout=timeout, check=True,
    )
    pages = sorted(
        f for f in os.listdir(tmp)
        if f.startswith('page') and f.endswith('.png')
    )
    if not pages:
        raise ValueError('PDF 转图片失败，请确认文件未损坏')
    return pages


def _cleanup_tmp(tmp):
    for f in os.listdir(tmp):
        try:
            os.remove(os.path.join(tmp, f))
        except OSError:
            pass
    try:
        os.rmdir(tmp)
    except OSError:
        pass


def ocr_pdf_for_word(pdf_path, max_pages=80, lang='chi_sim'):
    """扫描 PDF 转可编辑 Word — 按页 OCR，返回每页文字列表。"""
    tmp = tempfile.mkdtemp(prefix='ocr_word_')
    try:
        pages = _pdf_to_page_images(pdf_path, tmp, dpi=150, timeout=180)[:max_pages]
        texts = []
        for name in pages:
            text = _ocr_document_page(os.path.join(tmp, name), lang)
            texts.append(text or '')

        joined = '\n'.join(t for t in texts if t.strip())
        if len(joined.strip()) < 30:
            raise ValueError('未能识别出清晰文字，请确认扫描件清晰或页数是否过多')
        if _score_text(joined) < 0.15:
            raise ValueError('识别结果可读性较差，建议换更清晰的扫描件或先用「扫描件转文字」预览')
        return texts
    finally:
        _cleanup_tmp(tmp)


def ocr_pdf(pdf_path, lang='chi_sim'):
    """返回 (text, mean_confidence, low_conf_ratio)，逐页OCR结果取平均。"""
    tmp = tempfile.mkdtemp(prefix='ocr_pdf_')
    try:
        pages = _pdf_to_page_images(pdf_path, tmp, dpi=200, timeout=120)
        texts = []
        confs = []
        low_ratios = []
        for name in pages[:50]:
            text, conf, low_ratio = ocr_image(os.path.join(tmp, name), lang)
            if text:
                texts.append(text)
                confs.append(conf)
                low_ratios.append(low_ratio)

        if not texts:
            return '', 0.0, 0.0
        joined = '\n\n--- 下一页 ---\n\n'.join(texts)
        mean_conf = sum(confs) / len(confs) if confs else 0.0
        low_ratio = sum(low_ratios) / len(low_ratios) if low_ratios else 0.0
        return joined, mean_conf, low_ratio
    finally:
        _cleanup_tmp(tmp)