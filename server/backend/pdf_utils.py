"""轻量 PDF 处理 — 面向行政场景，优先稳定而非极致效果。"""
import os
import subprocess
import zipfile
from io import BytesIO

from docx import Document

MAX_PDF_PAGES = 50
MAX_PDF_WORD_PAGES = 80
MAX_MERGE_FILES = 20


def _open_reader(path):
    from pypdf import PdfReader
    reader = PdfReader(path)
    if reader.is_encrypted:
        try:
            reader.decrypt('')
        except Exception:
            raise ValueError('该 PDF 有密码保护，请先解密后再操作')
    return reader


def _page_count(path):
    return len(_open_reader(path).pages)


def pdf_page_count(path):
    return _page_count(path)


def check_pdf_convert_pages(path, limit=MAX_PDF_WORD_PAGES):
    n = _page_count(path)
    if n > limit:
        raise ValueError(f'PDF 共 {n} 页，请控制在 {limit} 页以内，可先拆分后再转')
    return n


def check_pdf_word_pages(path, limit=MAX_PDF_WORD_PAGES):
    return check_pdf_convert_pages(path, limit)


def check_pages(path, limit=MAX_PDF_PAGES):
    n = _page_count(path)
    if n > limit:
        raise ValueError(f'页数太多（{n} 页），请控制在 {limit} 页以内，或先拆分后再处理')
    return n


def merge_pdfs(input_paths, output_path):
    from pypdf import PdfWriter

    if len(input_paths) > MAX_MERGE_FILES:
        raise ValueError(f'一次最多合并 {MAX_MERGE_FILES} 个文件')
    if len(input_paths) < 2:
        raise ValueError('请至少选择 2 个 PDF 文件')

    writer = PdfWriter()
    for p in input_paths:
        reader = _open_reader(p)
        for page in reader.pages:
            writer.add_page(page)
    with open(output_path, 'wb') as f:
        writer.write(f)


def split_pdf(input_path, output_dir, unique_name, mode='each'):
    """mode: each=每页一个文件, half=一分为二"""
    from pypdf import PdfWriter

    reader = _open_reader(input_path)
    pages = reader.pages
    n = len(pages)
    check_pages(input_path, MAX_PDF_PAGES)

    outputs = []
    if mode == 'half':
        mid = n // 2 or 1
        ranges = [(0, mid), (mid, n)]
        for i, (start, end) in enumerate(ranges):
            writer = PdfWriter()
            for p in pages[start:end]:
                writer.add_page(p)
            out = os.path.join(output_dir, f'{unique_name}_part{i + 1}.pdf')
            with open(out, 'wb') as f:
                writer.write(f)
            outputs.append(out)
    else:
        for i, page in enumerate(pages):
            writer = PdfWriter()
            writer.add_page(page)
            out = os.path.join(output_dir, f'{unique_name}_page{i + 1}.pdf')
            with open(out, 'wb') as f:
                writer.write(f)
            outputs.append(out)

    zip_path = os.path.join(output_dir, f'{unique_name}.zip')
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for out in outputs:
            zf.write(out, os.path.basename(out))
            os.remove(out)
    return zip_path


def rotate_pdf(input_path, output_path, angle=90):
    reader = _open_reader(input_path)
    check_pages(input_path, MAX_PDF_PAGES)
    from pypdf import PdfWriter

    writer = PdfWriter()
    for page in reader.pages:
        page.rotate(angle)
        writer.add_page(page)
    with open(output_path, 'wb') as f:
        writer.write(f)


def compress_pdf(input_path, output_path):
    """轻度压缩 — 无 Ghostscript 时用 pypdf 流压缩，体积降幅有限但稳定。"""
    reader = _open_reader(input_path)
    check_pages(input_path, MAX_PDF_PAGES)
    from pypdf import PdfWriter

    writer = PdfWriter()
    writer.append(reader)
    for page in writer.pages:
        page.compress_content_streams()
    with open(output_path, 'wb') as f:
        writer.write(f)


def pdf_to_images_zip(input_path, output_dir, unique_name, dpi=150):
    """PDF 转图片 — 限制 DPI 和页数保护内存。"""
    import fitz

    check_pages(input_path, MAX_PDF_PAGES)
    doc = fitz.open(input_path)
    images = []
    zoom = dpi / 72
    mat = fitz.Matrix(zoom, zoom)

    for i in range(len(doc)):
        pix = doc[i].get_pixmap(matrix=mat, colorspace=fitz.csRGB)
        img_path = os.path.join(output_dir, f'{unique_name}_page{i + 1}.png')
        pix.save(img_path)
        images.append(img_path)
    doc.close()

    zip_path = os.path.join(output_dir, f'{unique_name}.zip')
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for img in images:
            zf.write(img, os.path.basename(img))
            os.remove(img)
    return zip_path


def parse_page_spec(spec, total):
    """解析页码如 1,3,5-7（1-based），返回 0-based 索引集合。"""
    if not spec or not spec.strip():
        raise ValueError('请填写要删除的页码，如 1,3,5-7')
    result = set()
    for part in spec.replace('，', ',').split(','):
        part = part.strip()
        if not part:
            continue
        if '-' in part:
            a, b = part.split('-', 1)
            start, end = int(a), int(b)
            if start > end:
                start, end = end, start
            for p in range(start, end + 1):
                if 1 <= p <= total:
                    result.add(p - 1)
        else:
            p = int(part)
            if 1 <= p <= total:
                result.add(p - 1)
    if not result:
        raise ValueError('页码无效，请检查输入')
    return result


def delete_pdf_pages(input_path, output_path, pages_spec):
    from pypdf import PdfWriter

    reader = _open_reader(input_path)
    n = len(reader.pages)
    check_pages(input_path, MAX_PDF_PAGES)
    to_delete = parse_page_spec(pages_spec, n)
    if len(to_delete) >= n:
        raise ValueError('不能删除全部页面，至少保留一页')

    writer = PdfWriter()
    for i, page in enumerate(reader.pages):
        if i not in to_delete:
            writer.add_page(page)
    with open(output_path, 'wb') as f:
        writer.write(f)


def _find_cn_font():
    import glob
    patterns = [
        '/usr/share/fonts/wqy-microhei/wqy-microhei.ttc',
        '/usr/share/fonts/google-droid/DroidSansFallback.ttf',
        '/usr/share/fonts/**/NotoSansCJK-Regular.ttc',
        '/usr/share/fonts/**/wqy-microhei.ttc',
        '/usr/share/fonts/**/DejaVuSans.ttf',
    ]
    for pat in patterns:
        hits = glob.glob(pat, recursive=True) if '**' in pat else ([pat] if os.path.isfile(pat) else [])
        if hits:
            return hits[0]
    return None


def _make_watermark_tile(text, font_path):
    import io
    from PIL import Image, ImageDraw, ImageFont

    tile = Image.new('RGBA', (420, 220), (0, 0, 0, 0))
    draw = ImageDraw.Draw(tile)
    try:
        font = ImageFont.truetype(font_path, 38, index=0) if font_path else ImageFont.load_default()
    except Exception:
        font = ImageFont.load_default()
    draw.text((36, 88), text, font=font, fill=(150, 150, 150, 110))
    rotated = tile.rotate(45, expand=True)
    buf = io.BytesIO()
    rotated.save(buf, format='PNG')
    return buf.getvalue(), rotated.size


def add_pdf_watermark(input_path, output_path, text):
    import fitz

    if not text.strip():
        raise ValueError('请输入水印文字')
    check_pages(input_path, MAX_PDF_PAGES)
    img_bytes, (tw, th) = _make_watermark_tile(text, _find_cn_font())
    doc = fitz.open(input_path)
    for page in doc:
        rect = page.rect
        w, h = rect.width, rect.height
        y = -th
        while y < h + th:
            x = -tw
            while x < w + tw:
                page.insert_image(
                    fitz.Rect(x, y, x + tw, y + th),
                    stream=img_bytes,
                    overlay=True,
                )
                x += int(tw * 0.82)
            y += int(th * 0.82)
    doc.save(output_path, garbage=4, deflate=True)
    doc.close()


def encrypt_pdf(input_path, output_path, password):
    from pypdf import PdfWriter

    if not password:
        raise ValueError('请设置密码')
    reader = _open_reader(input_path)
    check_pages(input_path, MAX_PDF_PAGES)
    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)
    writer.encrypt(password)
    with open(output_path, 'wb') as f:
        writer.write(f)


def decrypt_pdf(input_path, output_path, password):
    from pypdf import PdfReader, PdfWriter

    reader = PdfReader(input_path)
    if not reader.is_encrypted:
        raise ValueError('该 PDF 没有密码，无需解密')
    if not reader.decrypt(password):
        raise ValueError('密码错误，请重试')
    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)
    with open(output_path, 'wb') as f:
        writer.write(f)


def pdf_to_grayscale(input_path, output_path):
    import fitz

    check_pages(input_path, MAX_PDF_PAGES)
    doc = fitz.open(input_path)
    for page in doc:
        pix = page.get_pixmap(colorspace=fitz.csGRAY)
        page.clean_contents()
        page.insert_image(page.rect, pixmap=pix)
    doc.save(output_path)
    doc.close()


def extract_pdf_images_zip(input_path, output_dir, unique_name):
    import fitz

    check_pages(input_path, MAX_PDF_PAGES)
    doc = fitz.open(input_path)
    images = []
    for i in range(len(doc)):
        for j, img in enumerate(doc.get_page_images(i)):
            xref = img[0]
            pix = fitz.Pixmap(doc, xref)
            if pix.n - pix.alpha > 3:
                pix = fitz.Pixmap(fitz.csRGB, pix)
            out = os.path.join(output_dir, f'{unique_name}_p{i + 1}_{j + 1}.png')
            pix.save(out)
            images.append(out)
    doc.close()
    if not images:
        raise ValueError('这个 PDF 里没有找到可提取的图片')
    zip_path = os.path.join(output_dir, f'{unique_name}.zip')
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for img in images:
            zf.write(img, os.path.basename(img))
            os.remove(img)
    return zip_path


def pdf_layout_to_docx(pdf_path, output_path):
    """优先 pdf2docx（电子版保留表格，扫描件按页嵌图），失败再降级纯文字。"""
    try:
        from pdf2docx import Converter

        cv = Converter(pdf_path)
        cv.convert(output_path, start=0, end=None)
        cv.close()
        if os.path.getsize(output_path) > 1024:
            return 'layout'
    except Exception:
        pass

    pdf_text_to_docx(pdf_path, output_path)
    return 'text'


def _clean_table_cell(value):
    if value is None:
        return ''
    return str(value).replace('\n', ' ').strip()


_TABLE_HEADER_SETS = [
    ['时间', '任务名称', '你需要做什么', '要准备的资料'],
    ['类别', '事项', '截止时间', '需准备的资料'],
    ['频率', '事项', '需准备的资料'],
]


def _fix_cn_spaces(text):
    import re
    if not text:
        return ''
    text = re.sub(r'(?<=[\u4e00-\u9fff])\s+(?=[\u4e00-\u9fff])', '', text)
    text = re.sub(r'([，、；：])\s+', r'\1', text)
    return re.sub(r'\s{2,}', ' ', text).strip()


def _join_line_words(words):
    ordered = sorted(words, key=lambda w: w['x0'])
    out = ''
    for w in ordered:
        t = w['text']
        if not out:
            out = t
        elif out[-1].isascii() and t.isascii():
            out += ' ' + t
        else:
            out += t
    return _fix_cn_spaces(out.strip())


def _cluster_page_words(page, y_tol=4):
    from collections import defaultdict

    lines = defaultdict(list)
    for w in page.extract_words(x_tolerance=2):
        lines[round(w['top'] / y_tol) * y_tol].append(w)
    return lines


def _detect_table_header(words):
    texts = {w['text'] for w in words}
    for labels in _TABLE_HEADER_SETS:
        if all(label in texts for label in labels):
            anchors = []
            for label in labels:
                for w in sorted(words, key=lambda x: x['x0']):
                    if w['text'] == label:
                        anchors.append(w['x0'])
                        break
            if len(anchors) == len(labels):
                bounds = [0]
                bounds.extend((anchors[i] + anchors[i + 1]) / 2 for i in range(len(anchors) - 1))
                bounds.append(9999)
                return labels, bounds
    return None, None


def _assign_row_columns(words, bounds, ncols):
    buckets = [[] for _ in range(ncols)]
    for w in sorted(words, key=lambda x: x['x0']):
        idx = ncols - 1
        for i in range(len(bounds) - 1):
            if bounds[i] <= w['x0'] < bounds[i + 1]:
                idx = min(i, ncols - 1)
                break
        buckets[idx].append(w)
    return [_join_line_words(bucket) for bucket in buckets]


def _is_noise_row(row):
    text = ''.join(row).strip()
    if not text:
        return True
    if text.startswith(('一、', '二、', '三、', '四、', '五、', '□', '注：')):
        return True
    if text.startswith(('安全类资料', '平安类资料', '项目级资料')):
        return True
    if 'F:\\' in text or 'F:/' in text:
        return True
    if row[0] and len(row[0]) > 35 and not any(row[1:]):
        return True
    return False


def _section_title_from_line(line):
    for prefix in ('一、', '二、', '三、', '四、', '五、'):
        if line.startswith(prefix):
            title = line.split('□')[0].strip()
            for ch in ('/', '\\', '*', '?', ':', '[', ']'):
                title = title.replace(ch, ' ')
            return title[:31] or '数据'
    return None


def _normalize_row(row, ncols=4):
    row = [_fix_cn_spaces(_clean_table_cell(c)) for c in row]
    while len(row) < ncols:
        row.append('')
    return row[:ncols]


def _extract_pdf_table_sections(pdf_path):
    """按表头/章节拆成多个表格块，便于分 sheet 输出。"""
    import pdfplumber

    sections = []
    current = None
    pending_title = None

    def start_section(title, labels, bounds, ncols):
        nonlocal current, pending_title
        if current and current['rows']:
            sections.append(current)
        use_title = (title or pending_title or '数据')[:31]
        pending_title = None
        current = {
            'title': use_title,
            'ncols': ncols,
            'bounds': bounds,
            'header': list(labels),
            'rows': [_normalize_row(labels, max(ncols, 4))],
        }

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            line_map = _cluster_page_words(page)
            for key in sorted(line_map):
                words = line_map[key]
                line = _join_line_words(words)
                section_title = _section_title_from_line(line)
                if section_title:
                    if current and len(current['rows']) > 1:
                        sections.append(current)
                        current = None
                    pending_title = section_title
                    continue

                labels, new_bounds = _detect_table_header(words)
                if labels:
                    title = (current['title'] if current else None) or pending_title or '数据'
                    start_section(title, labels, new_bounds, len(labels))
                    continue

                if current is None or current['bounds'] is None:
                    continue
                if line.startswith('□'):
                    continue

                row = _normalize_row(
                    _assign_row_columns(words, current['bounds'], current['ncols']),
                    max(current['ncols'], 4),
                )
                if _is_noise_row(row):
                    continue
                if current['rows'] and not row[0] and any(row[1:]):
                    prev = current['rows'][-1]
                    for i in range(len(row)):
                        if row[i]:
                            prev[i] = _fix_cn_spaces(f'{prev[i]} {row[i]}'.strip())
                elif any(row):
                    current['rows'].append(row)

    if current and current['rows']:
        sections.append(current)
    return sections


def _extract_pdf_table_rows(pdf_path):
    rows = []
    for sec in _extract_pdf_table_sections(pdf_path):
        if len(sec['rows']) > 1:
            rows.extend(sec['rows'])
        elif sec['rows']:
            rows.append(sec['rows'][0])
    return rows


def pdf_has_extractable_tables(pdf_path, min_rows=3):
    sections = _extract_pdf_table_sections(pdf_path)
    data_rows = sum(max(0, len(s['rows']) - 1) for s in sections)
    return data_rows >= min_rows


def _merge_same_cells(ws, col_idx, start_row, end_row):
    from openpyxl.styles import Alignment

    if end_row <= start_row:
        return
    val = ws.cell(start_row, col_idx).value
    if not val:
        return
    ws.merge_cells(
        start_row=start_row, start_column=col_idx,
        end_row=end_row, end_column=col_idx,
    )
    cell = ws.cell(start_row, col_idx)
    cell.alignment = Alignment(wrap_text=True, vertical='center')


def _write_table_sheet(ws, rows, ncols):
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

    header_labels = set()
    for labels in _TABLE_HEADER_SETS:
        header_labels.update(labels)

    thin = Side(style='thin', color='B0B0B0')
    border = Border(left=thin, right=thin, top=thin, bottom=thin)
    header_fill = PatternFill('solid', fgColor='E8EEF4')
    body_font = Font(size=11)
    header_font = Font(size=11, bold=True)
    widths = [10, 28, 32, 28]

    merge_ranges = []
    merge_start = None
    merge_val = None

    for r_idx, row in enumerate(rows, 1):
        is_header = bool(row and row[0] in header_labels)
        for c_idx in range(ncols):
            val = row[c_idx] if c_idx < len(row) else ''
            cell = ws.cell(r_idx, c_idx + 1, val or None)
            cell.border = border
            cell.alignment = Alignment(wrap_text=True, vertical='top')
            cell.font = header_font if is_header else body_font
            if is_header:
                cell.fill = header_fill

        if not is_header and row and row[0]:
            if row[0] == merge_val:
                if merge_start is None:
                    merge_start = r_idx - 1
            else:
                if merge_start and r_idx - 1 > merge_start:
                    merge_ranges.append((merge_start, r_idx - 1))
                merge_val = row[0]
                merge_start = r_idx
        elif merge_start and r_idx - 1 > merge_start:
            merge_ranges.append((merge_start, r_idx - 1))
            merge_start = None
            merge_val = None

    if merge_start and len(rows) > merge_start:
        merge_ranges.append((merge_start, len(rows)))

    for start, end in merge_ranges:
        _merge_same_cells(ws, 1, start, end)

    if len(rows) > 1:
        ws.freeze_panes = 'A2'
    for i, w in enumerate(widths[:ncols], 1):
        ws.column_dimensions[chr(ord('A') + i - 1)].width = w


def pdf_tables_to_xlsx(pdf_path, output_path):
    """按文字坐标提取表格列，分 sheet、合并首列，并加上边框/表头样式。"""
    from openpyxl import Workbook

    sections = _extract_pdf_table_sections(pdf_path)
    if not sections:
        result = subprocess.run(
            ['pdftotext', pdf_path, '-'],
            capture_output=True, text=True, timeout=60,
        )
        text = result.stdout.strip()
        if len(text) < 10:
            raise ValueError('未能从 PDF 提取表格或文字，请确认文件内容清晰')
        raise ValueError('未能识别表格结构，请换电子版 PDF 或先在 Word 中整理后再转 Excel')

    wb = Workbook()
    wb.remove(wb.active)
    used_titles = set()

    for sec in sections:
        title = sec['title'] or '数据'
        base = title
        n = 2
        while title in used_titles:
            suffix = f'_{n}'
            title = (base[:31 - len(suffix)] + suffix) if len(base) + len(suffix) > 31 else base + suffix
            n += 1
        used_titles.add(title)
        ws = wb.create_sheet(title=title)
        ncols = max(sec['ncols'], 4)
        _write_table_sheet(ws, sec['rows'], ncols)

    if not wb.sheetnames:
        raise ValueError('未能识别表格结构，请换电子版 PDF 或先在 Word 中整理后再转 Excel')

    wb.save(output_path)


def pdf_text_to_docx(pdf_path, output_path):
    """pdftotext + python-docx，版式会简化，但文字可保留。"""
    result = subprocess.run(
        ['pdftotext', pdf_path, '-'],
        capture_output=True, text=True, timeout=60,
    )
    text = result.stdout.strip()
    if len(text) < 30:
        raise ValueError('无法从 PDF 提取文字，可能是扫描件或加密文件')

    doc = Document()
    for line in text.split('\n'):
        line = line.strip()
        if line:
            doc.add_paragraph(line)
    doc.save(output_path)


def images_to_pdf(image_paths, output_path):
    if not image_paths:
        raise ValueError('请至少上传 1 张图片')
    if len(image_paths) > MAX_MERGE_FILES:
        raise ValueError(f'一次最多 {MAX_MERGE_FILES} 张图片')

    import img2pdf

    with open(output_path, 'wb') as f:
        f.write(img2pdf.convert(image_paths))