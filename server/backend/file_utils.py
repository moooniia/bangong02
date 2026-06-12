"""文件文字提取与翻译输出。"""
import os
import subprocess
import tempfile

from docx import Document


def extract_text_from_file(path, ext, ocr_pdf_func):
    ext = ext.lower()
    if ext == 'txt':
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read().strip()
    if ext in ('doc', 'docx'):
        return _extract_docx(path)
    if ext == 'pdf':
        return _extract_pdf(path, ocr_pdf_func)
    raise ValueError('暂不支持该格式，请上传 TXT、Word 或 PDF')


def _extract_docx(path):
    doc = Document(path)
    parts = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
    if not parts:
        raise ValueError('文档里没有读到文字')
    return '\n\n'.join(parts)


def _extract_pdf(path, ocr_pdf_func):
    result = subprocess.run(
        ['pdftotext', path, '-'],
        capture_output=True, text=True, timeout=60,
    )
    text = result.stdout.strip()
    if len(text) > 30:
        return text
    return ocr_pdf_func(path)


def write_translated_docx(text, output_path):
    doc = Document()
    for block in text.split('\n\n'):
        if block.strip():
            doc.add_paragraph(block.strip())
    doc.save(output_path)


def write_ocr_docx(page_texts, output_path):
    """扫描件 OCR 结果写入 Word，保留换行，页间分页。"""
    doc = Document()
    for i, text in enumerate(page_texts):
        if i > 0:
            doc.add_page_break()
        if not text or not text.strip():
            continue
        for line in text.split('\n'):
            line = line.strip()
            if line:
                doc.add_paragraph(line)
    doc.save(output_path)


def translated_to_output(text, output_dir, uid, out_format='txt'):
    if out_format == 'docx':
        out = os.path.join(output_dir, f'{uid}.docx')
        write_translated_docx(text, out)
        return out, '译文.docx'
    out = os.path.join(output_dir, f'{uid}.txt')
    with open(out, 'w', encoding='utf-8') as f:
        f.write(text)
    return out, '译文.txt'