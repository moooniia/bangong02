import json
import os
import re
import subprocess
import traceback
import urllib.parse
import urllib.request
import uuid
from flask import Flask, request, jsonify, send_file
from werkzeug.utils import secure_filename

from pdf_utils import (
    merge_pdfs, split_pdf, rotate_pdf, compress_pdf,
    pdf_to_images_zip, images_to_pdf, images_to_pdf_export, delete_pdf_pages,
    add_pdf_watermark, encrypt_pdf, decrypt_pdf, pdf_to_grayscale,
    extract_pdf_images_zip, pdf_layout_to_docx, pdf_tables_to_xlsx,
    pdf_has_extractable_tables,
    check_pdf_word_pages, check_pdf_convert_pages,
)
from image_utils import (
    compress_image, resize_image, convert_image_format, rotate_image,
    add_image_watermark, add_image_timestamp, batch_process_images,
)
from file_utils import (
    extract_text_from_file, translated_to_output,
    write_translated_docx, write_ocr_docx,
)
from ocr_utils import ocr_pdf_for_word
from ocr_utils import ocr_image, ocr_pdf, clean_ocr_text
import usage_stats

app = Flask(__name__)

UPLOAD_FOLDER = '/home/toolbox/uploads'
OUTPUT_FOLDER = '/home/toolbox/outputs'

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024

CONVERT_FILTERS = {
    'docx': 'MS Word 2007 XML',
    'doc':  'MS Word 2007 XML',
    'xlsx': 'Calc MS Excel 2007 XML',
    'xls':  'Calc MS Excel 2007 XML',
    'pptx': 'Impress MS PowerPoint 2007 XML',
    'ppt':  'Impress MS PowerPoint 2007 XML',
    'pdf':  'writer_pdf_Export',
}

ALLOWED_INPUT = {'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'jpg', 'jpeg', 'png'}
IMAGE_EXTS = {'jpg', 'jpeg', 'png'}
OCR_EXTS = IMAGE_EXTS | {'pdf'}

LANG_MAP = {
    'zh': 'chi_sim',
    'en': 'eng',
    'auto': 'chi_sim',
}

TRANSLATE_LANG_MAP = {
    'auto': 'autodetect',
    'zh-CN': 'zh-CN',
    'zh': 'zh-CN',
    'en': 'en',
    'ja': 'ja',
    'ko': 'ko',
    'fr': 'fr',
    'de': 'de',
    'es': 'es',
}


def translate_text(text, source, target):
    fr = TRANSLATE_LANG_MAP.get(source, source)
    to = TRANSLATE_LANG_MAP.get(target, target)
    text = re.sub(r'[\r\n\t]+', ' ', text).strip()
    q = urllib.parse.quote(text, safe='')
    url = f'https://api.mymemory.translated.net/get?q={q}&langpair={fr}|{to}'
    with urllib.request.urlopen(url, timeout=20) as resp:
        data = json.loads(resp.read().decode())
    if data.get('responseStatus') != 200:
        raise ValueError('翻译服务暂时不可用，请稍后重试')
    return data['responseData']['translatedText']


def translate_long_text(text, source, target, chunk_size=400):
    """长文分段翻译，避免 API 长度限制。"""
    if len(text) <= chunk_size:
        return translate_text(text, source, target)
    parts = []
    buf = ''
    for line in text.split('\n'):
        if len(buf) + len(line) + 1 > chunk_size and buf:
            parts.append(translate_text(buf, source, target))
            buf = line
        else:
            buf = f'{buf}\n{line}' if buf else line
    if buf:
        parts.append(translate_text(buf, source, target))
    return '\n\n'.join(parts)


def get_ext(filename):
    if '.' in filename:
        return filename.rsplit('.', 1)[1].lower()
    return ''


def pdf_has_text(pdf_path):
    try:
        result = subprocess.run(
            ['pdftotext', pdf_path, '-'],
            capture_output=True, text=True, timeout=30
        )
        return len(result.stdout.strip()) > 50
    except Exception:
        return False


def analyze_pdf(pdf_path):
    """
    快速体检 PDF（采样前3页，2秒内完成），返回档位和各项指标。

    档位：
      0 — 普通 PDF（有文字层），LibreOffice 本地转
      1 — 简单扫描件，Tesseract 本地 OCR
      2 — 复杂扫描件（印章/水印/密集表格），火山 OCR API
    """
    result = {
        'tier': 0,
        'has_text_layer': False,
        'text_coverage': 0.0,
        'has_red_seal': False,
        'has_rotated_watermark': False,
        'has_dense_tables': False,
        'page_count': 0,
        'reason': '',
    }

    try:
        import fitz
        doc = fitz.open(pdf_path)
        result['page_count'] = len(doc)
        sample_pages = min(3, len(doc))

        # --- 1. 文字层检测（改进版）---
        text_pages = 0
        for i in range(sample_pages):
            page = doc[i]
            text = page.get_text().strip() if hasattr(page, 'get_text') else ''
            if not text:
                text = page.getText().strip() if hasattr(page, 'getText') else ''
            # 按页面面积加权：A4 约 595*842 pt，每页至少80字算有效
            if len(text) >= 80:
                text_pages += 1
        coverage = text_pages / sample_pages if sample_pages > 0 else 0
        result['text_coverage'] = round(coverage, 2)
        result['has_text_layer'] = coverage >= 0.6

        # --- 2. 视觉检测：印章对所有 PDF 均执行（含有文字层的混合 PDF）---
        # 渲染采样页缩略图（100dpi，省内存又能看清印章）
        mat = fitz.Matrix(100 / 72.0, 100 / 72.0)

        # 印章检测：扫描所有采样页，红色像素（R>150, G<80, B<80）
        for i in range(sample_pages):
            try:
                pix = doc[i].getPixmap(matrix=mat, alpha=False)
            except AttributeError:
                pix = doc[i].get_pixmap(matrix=mat, alpha=False)
            samples = pix.samples
            total_pixels = pix.width * pix.height
            red_count = 0
            for idx in range(total_pixels):
                r = samples[idx * 3]
                g = samples[idx * 3 + 1]
                b = samples[idx * 3 + 2]
                if r > 150 and g < 100 and b < 80:
                    red_count += 1
            if red_count / total_pixels > 0.0003:  # 0.03%，约100px@100dpi
                result['has_red_seal'] = True
                print(f'[analyze_pdf] 第{i}页检出红章: red_count={red_count}, ratio={red_count/total_pixels:.5f}', flush=True)
                break

        # 水印检测：两种策略并用
        # 策略A：文字块旋转角度（适用于数字 PDF 水印）
        for i in range(sample_pages):
            page = doc[i]
            try:
                blocks = page.get_text('rawdict')['blocks']
            except Exception:
                try:
                    blocks = page.getText('rawdict')['blocks']
                except Exception:
                    blocks = []
            for block in blocks:
                if block.get('type') != 0:
                    continue
                for line in block.get('lines', []):
                    angle = abs(line.get('dir', [1, 0])[1])
                    if angle > 0.26:  # sin(15°) ≈ 0.26
                        result['has_rotated_watermark'] = True
                        break
                if result['has_rotated_watermark']:
                    break
            if result['has_rotated_watermark']:
                break

        # 表格检测：首页线段数量（有文字层的 PDF 才有 drawings）
        first_page = doc[0]
        try:
            drawings = first_page.get_drawings()
        except AttributeError:
            try:
                drawings = first_page.getDrawings()
            except Exception:
                drawings = []
        line_count = sum(
            1 for d in drawings
            if d.get('type') == 'l' or (d.get('rect') and
               (d['rect'][2] - d['rect'][0] < 2 or d['rect'][3] - d['rect'][1] < 2))
        )
        result['has_dense_tables'] = line_count > 20

        doc.close()

        # --- 3. 定档 ---
        if result['has_text_layer']:
            if result['has_red_seal']:
                # 有文字层但含红章（如公文首页盖章）→ 火山 OCR，版式还原更完整
                result['tier'] = 2
                result['reason'] = '有文字层但含红章，走火山 OCR'
            else:
                result['tier'] = 0
                result['reason'] = '文字层覆盖率 %.0f%%，本地转换' % (coverage * 100)
        else:
            complex_flags = [
                result['has_red_seal'],
                result['has_rotated_watermark'],
                result['has_dense_tables'],
            ]
            if any(complex_flags):
                reasons = []
                if result['has_red_seal']:
                    reasons.append('红章')
                if result['has_rotated_watermark']:
                    reasons.append('旋转水印')
                if result['has_dense_tables']:
                    reasons.append('密集表格')
                result['reason'] = '扫描件（%s），走火山 OCR' % '、'.join(reasons)
            else:
                result['reason'] = '扫描件（无文字层），走火山 OCR'
            result['tier'] = 2

    except Exception as e:
        # fitz 不可用或解析失败，退回旧逻辑
        result['has_text_layer'] = pdf_has_text(pdf_path)
        result['tier'] = 0 if result['has_text_layer'] else 2
        result['reason'] = '体检异常(%s)，保守路由' % str(e)[:60]

    return result


def _tesseract_quality(page_texts):
    """评估 Tesseract 输出质量，返回 (score, avg_cjk_per_page)。"""
    from ocr_utils import _score_text
    combined = '\n'.join(t for t in page_texts if t.strip())
    score = _score_text(combined)
    total_cjk = sum(1 for c in combined if '一' <= c <= '鿿')
    avg_cjk = total_cjk / max(len(page_texts), 1)
    return score, avg_cjk


def convert_scanned_pdf_to_docx(pdf_path, unique_name, output_folder, diagnosis=None):
    """
    两阶段扫描件转换：
      Stage 1 — Tesseract 本地 OCR（免费，仅用于简单扫描件）
      Stage 2 — 火山 OCR API（有印章/水印/密集表格时直接跳到此步）

    成功时返回 {"route": str, "warning": str}；Tesseract 本地成功时 route=local-tesseract。
    """
    output_file = os.path.join(output_folder, f'{unique_name}.docx')

    # 扫描件（tier>=1）或含印章/水印/复杂表格时直接用火山 OCR，跳过 Tesseract
    needs_volc = diagnosis and (
        diagnosis.get('tier', 0) >= 1 or
        diagnosis.get('has_red_seal') or
        diagnosis.get('has_rotated_watermark') or
        diagnosis.get('has_dense_tables')
    )
    if needs_volc:
        app.logger.info(
            '扫描件/复杂件(tier=%s)，直接使用火山 OCR，跳过 Tesseract',
            diagnosis.get('tier'),
        )

    # Stage 1: Tesseract（仅简单扫描件）
    page_texts = None
    tesseract_ok = False
    if not needs_volc:
        try:
            app.logger.info('Stage1: Tesseract 本地 OCR')
            page_texts = ocr_pdf_for_word(pdf_path)
            score, avg_cjk = _tesseract_quality(page_texts)
            app.logger.info('Tesseract 质量: score=%.2f avg_cjk/page=%.0f', score, avg_cjk)
            if score >= 0.20 and avg_cjk >= 30:
                app.logger.info('Tesseract 质量合格，无需调用 API')
                write_ocr_docx(page_texts, output_file)
                tesseract_ok = True
                return {'route': 'local-tesseract', 'warning': ''}
            else:
                app.logger.info('Tesseract 质量不足(score=%.2f avg_cjk=%.0f)，升级火山 OCR', score, avg_cjk)
        except Exception as e:
            app.logger.info('Tesseract 未能完成(%.60s)，升级火山 OCR', str(e))

    # Stage 2: 火山 OCR
    try:
        from volc_ocr import volc_configured, volc_pdf_to_docx
        if volc_configured():
            app.logger.info('Stage2: 火山 OCR API')
            usage_stats.bump('volc_word')
            has_watermark = bool(diagnosis and diagnosis.get('has_rotated_watermark'))
            meta = volc_pdf_to_docx(pdf_path, output_file, skip_direct=has_watermark)
            if isinstance(meta, str):
                meta = {'route': meta, 'warning': ''}
            app.logger.info(
                '火山 OCR 完成 route=%s warning=%s',
                meta.get('route'), meta.get('warning') or '',
            )
            return meta
        app.logger.warning('火山 OCR 未配置，回退 Tesseract 结果')
    except Exception as e:
        app.logger.warning('火山 OCR 失败(%.60s)，回退 Tesseract 结果', str(e))

    # 兜底：保存 Tesseract 结果（哪怕质量差）
    if page_texts:
        write_ocr_docx(page_texts, output_file)
        return {'route': 'local-tesseract-fallback', 'warning': '已使用本地 OCR，版式可能不完整'}
    try:
        page_texts = ocr_pdf_for_word(pdf_path)
        write_ocr_docx(page_texts, output_file)
        return {'route': 'local-tesseract-fallback', 'warning': '已使用本地 OCR，版式可能不完整'}
    except Exception as e:
        app.logger.error('所有路径均失败: %s', e)
    return {'route': 'failed', 'warning': ''}


def extract_red_seal(image_path, output_path):
    from seal_utils import extract_red_seal as _extract_red_seal
    _extract_red_seal(image_path, output_path)


@app.route('/api/convert', methods=['POST'])
def convert():
    input_path = None
    try:
        if 'file' not in request.files:
            return jsonify({'error': '没有文件'}), 400

        file = request.files['file']
        target_format = request.form.get('format', 'docx')

        if file.filename == '' or '.' not in file.filename:
            return jsonify({'error': '未选择文件'}), 400

        ext = get_ext(file.filename)
        if ext not in ALLOWED_INPUT:
            return jsonify({'error': '不支持的文件格式'}), 400

        unique_name = str(uuid.uuid4())
        filename = unique_name + '.' + ext
        input_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(input_path)

        output_file = os.path.join(OUTPUT_FOLDER, f'{unique_name}.{target_format}')
        lo_filter = CONVERT_FILTERS.get(target_format, target_format)
        convert_meta = {}

        if ext == 'pdf' and target_format in ('xlsx', 'xls'):
            check_pdf_convert_pages(input_path)
            fb_xlsx = os.path.join(OUTPUT_FOLDER, f'{unique_name}.xlsx')
            if pdf_has_extractable_tables(input_path):
                app.logger.info('PDF 转 Excel，识别到表格，走坐标提取')
                pdf_tables_to_xlsx(input_path, fb_xlsx)
                output_file = fb_xlsx
                if target_format == 'xls' and os.path.exists(fb_xlsx):
                    subprocess.run([
                        'libreoffice', '--headless',
                        '--convert-to', 'xls:Calc MS Excel 2007 XML',
                        '--outdir', OUTPUT_FOLDER, fb_xlsx
                    ], capture_output=True, text=True, timeout=60)
                    if os.path.exists(fb_xlsx):
                        os.remove(fb_xlsx)
            else:
                app.logger.info('PDF 转 Excel，走 LibreOffice')
                subprocess.run([
                    'libreoffice', '--headless',
                    '--convert-to', f'{target_format}:{lo_filter}',
                    '--outdir', OUTPUT_FOLDER, input_path
                ], capture_output=True, text=True, timeout=120)
                if not os.path.exists(output_file):
                    app.logger.info('LibreOffice 失败，走表格提取回退')
                    pdf_tables_to_xlsx(input_path, fb_xlsx)
                    output_file = fb_xlsx
                    if target_format == 'xls' and os.path.exists(fb_xlsx):
                        subprocess.run([
                            'libreoffice', '--headless',
                            '--convert-to', 'xls:Calc MS Excel 2007 XML',
                            '--outdir', OUTPUT_FOLDER, fb_xlsx
                        ], capture_output=True, text=True, timeout=60)
                        if os.path.exists(fb_xlsx):
                            os.remove(fb_xlsx)
        elif ext == 'pdf' and target_format == 'pdf_ocr':
            # 可搜索 PDF：在扫描件上叠加 OCR 文字层，版面不变，能复制/搜索文字
            check_pdf_word_pages(input_path)
            out_pdf = os.path.join(OUTPUT_FOLDER, f'{unique_name}.pdf')
            app.logger.info('可搜索PDF：ocrmypdf 叠加文字层')
            r = subprocess.run(
                ['ocrmypdf', '--language', 'chi_sim+eng',
                 '--output-type', 'pdf',
                 '--skip-text',          # 已有文字层的页跳过，不重复处理
                 '--optimize', '1',
                 input_path, out_pdf],
                capture_output=True, text=True, timeout=300
            )
            if r.returncode != 0 and not os.path.exists(out_pdf):
                app.logger.error('ocrmypdf 失败: %s', r.stderr[-300:])
                return jsonify({'error': 'OCR 处理失败，请确认文件为有效 PDF'}), 500
            output_file = out_pdf
            original_base = file.filename.rsplit('.', 1)[0]
            return jsonify({
                'success': True,
                'filename': f'{unique_name}.pdf',
                'display_name': f'{original_base}_可搜索.pdf'
            })

        elif ext == 'pdf' and target_format in ('docx', 'doc'):
            check_pdf_word_pages(input_path)
            fb_docx = os.path.join(OUTPUT_FOLDER, f'{unique_name}.docx')

            diagnosis = analyze_pdf(input_path)
            print(
                f'[PDF体检] tier={diagnosis["tier"]} pages={diagnosis["page_count"]} '
                f'text={diagnosis["text_coverage"]*100:.0f}% red_seal={diagnosis["has_red_seal"]} '
                f'watermark={diagnosis["has_rotated_watermark"]} dense={diagnosis["has_dense_tables"]} | {diagnosis["reason"]}',
                flush=True,
            )

            if diagnosis['tier'] == 0:
                print('[PDF转换] 第0档：普通PDF，走LibreOffice本地转换', flush=True)
                convert_meta = {'route': 'local-libreoffice', 'warning': ''}
                subprocess.run([
                    'libreoffice', '--headless',
                    '--convert-to', f'{target_format}:{lo_filter}',
                    '--outdir', OUTPUT_FOLDER, input_path
                ], capture_output=True, text=True, timeout=120)
                if not os.path.exists(output_file):
                    app.logger.info('LibreOffice 失败，走版式/文字回退')
                    mode = pdf_layout_to_docx(input_path, fb_docx)
                    convert_meta = {'route': f'local-{mode}', 'warning': ''}
                    app.logger.info('PDF 回退模式: %s', mode)
            else:
                app.logger.info('扫描件：两阶段转换（Tesseract → 火山OCR）')
                meta = convert_scanned_pdf_to_docx(
                    input_path, unique_name, OUTPUT_FOLDER, diagnosis=diagnosis,
                )
                if isinstance(meta, dict):
                    convert_meta = meta

            if target_format == 'doc' and os.path.exists(fb_docx) and not os.path.exists(output_file):
                subprocess.run([
                    'libreoffice', '--headless',
                    '--convert-to', 'doc:MS Word 2007 XML',
                    '--outdir', OUTPUT_FOLDER, fb_docx
                ], capture_output=True, text=True, timeout=120)
                if os.path.exists(fb_docx):
                    os.remove(fb_docx)
        elif ext == 'pdf' and target_format in ('pptx', 'ppt'):
            from pdf_utils import pdf_to_pptx
            pptx_file = os.path.join(OUTPUT_FOLDER, f'{unique_name}.pptx')
            pdf_to_pptx(input_path, pptx_file)
            output_file = pptx_file
            if target_format == 'ppt':
                subprocess.run([
                    'libreoffice', '--headless',
                    '--convert-to', 'ppt:Impress MS PowerPoint 2007 XML',
                    '--outdir', OUTPUT_FOLDER, pptx_file,
                ], capture_output=True, text=True, timeout=60)
                if os.path.exists(os.path.join(OUTPUT_FOLDER, f'{unique_name}.ppt')):
                    output_file = os.path.join(OUTPUT_FOLDER, f'{unique_name}.ppt')
                    if os.path.exists(pptx_file):
                        os.remove(pptx_file)
                else:
                    output_file = pptx_file
        else:
            subprocess.run([
                'libreoffice', '--headless',
                '--convert-to', f'{target_format}:{lo_filter}',
                '--outdir', OUTPUT_FOLDER, input_path
            ], capture_output=True, text=True, timeout=120)

        if not os.path.exists(output_file):
            return jsonify({'error': '转换失败，请检查文件格式是否正确'}), 500

        original_base = file.filename.rsplit('.', 1)[0]
        payload = {
            'success': True,
            'filename': f'{unique_name}.{target_format}',
            'display_name': f'{original_base}.{target_format}',
        }
        if convert_meta.get('route'):
            payload['route'] = convert_meta['route']
        if convert_meta.get('warning'):
            payload['warning'] = convert_meta['warning']
        return jsonify(payload)

    except Exception as e:
        app.logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500
    finally:
        if input_path and os.path.exists(input_path):
            os.remove(input_path)


@app.route('/api/ocr', methods=['POST'])
def ocr():
    input_path = None
    try:
        if 'file' not in request.files:
            return jsonify({'error': '没有文件'}), 400

        file = request.files['file']
        if file.filename == '' or '.' not in file.filename:
            return jsonify({'error': '未选择文件'}), 400

        ext = get_ext(file.filename)
        if ext not in OCR_EXTS:
            return jsonify({'error': '不支持的文件格式，请上传图片或 PDF'}), 400

        lang_key = request.form.get('lang', 'auto')
        tesseract_lang = LANG_MAP.get(lang_key, 'chi_sim+eng')
        output_type = request.form.get('output', 'text')

        unique_name = str(uuid.uuid4())
        input_path = os.path.join(UPLOAD_FOLDER, unique_name + '.' + ext)
        file.save(input_path)

        if ext == 'pdf':
            text, confidence, low_conf_ratio = ocr_pdf(input_path, tesseract_lang)
        else:
            text, confidence, low_conf_ratio = ocr_image(input_path, tesseract_lang)

        text = clean_ocr_text(text)
        compact = re.sub(r'\s+', '', text)
        cjk = sum(1 for c in compact if '\u4e00' <= c <= '\u9fff')
        low_quality = (
            (not text)
            or (len(compact) > 20 and cjk / len(compact) < 0.35)
            or confidence < 70
            or low_conf_ratio > 0.04
        )
        print(
            f'[OCR] 本地Tesseract: conf={confidence:.1f} low_conf_ratio={low_conf_ratio:.3f} '
            f'len={len(compact)} low_quality={low_quality}',
            flush=True,
        )
        if low_quality:
            try:
                from volc_ocr import volc_configured, volc_ocr_image_text, volc_ocr_pdf_text
                if volc_configured():
                    print('[OCR] 质量不达标，改走火山OCR兜底', flush=True)
                    usage_stats.bump('volc_ocr_text')
                    fallback_text = (
                        volc_ocr_pdf_text(input_path) if ext == 'pdf'
                        else volc_ocr_image_text(input_path)
                    )
                    fallback_text = clean_ocr_text(fallback_text)
                    if fallback_text:
                        print('[OCR] 火山OCR兜底成功，已替换识别结果', flush=True)
                        text = fallback_text
                        low_quality = False
                    else:
                        print('[OCR] 火山OCR兜底没识别出文字，仍用本地结果', flush=True)
                else:
                    print('[OCR] 火山OCR未配置密钥，跳过兜底', flush=True)
            except Exception:
                app.logger.error(traceback.format_exc())

        if not text:
            return jsonify({'error': '\u672a\u8bc6\u522b\u5230\u6587\u5b57\uff0c\u8bf7\u6362\u4e00\u5f20\u66f4\u6e05\u6670\u7684\u56fe\u7247\u91cd\u8bd5'}), 400

        if low_quality:
            return jsonify({
                'error': '\u8bc6\u522b\u6548\u679c\u4e0d\u4f73\uff0c\u5efa\u8bae\uff1a\u2460 \u7528\u624b\u673a\u622a\u56fe\u65f6\u5c3d\u91cf\u653e\u5927\u6587\u5b57 \u2461 \u9009\u62e9\u5149\u7ebf\u597d\u3001\u4e0d\u6a21\u7cca\u7684\u56fe\u7247 \u2462 \u6216\u6362\u626b\u63cf\u4ef6\u8f6c\u6587\u5b57\u8bd5\u8bd5'
            }), 400

        if output_type == 'file':
            txt_filename = f'{unique_name}.txt'
            txt_path = os.path.join(OUTPUT_FOLDER, txt_filename)
            with open(txt_path, 'w', encoding='utf-8') as f:
                f.write(text)
            original_base = file.filename.rsplit('.', 1)[0]
            return jsonify({
                'success': True,
                'filename': txt_filename,
                'display_name': f'{original_base}.txt',
                'text': text
            })

        return jsonify({'success': True, 'text': text})

    except Exception as e:
        app.logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500
    finally:
        if input_path and os.path.exists(input_path):
            os.remove(input_path)


@app.route('/api/extract-seal', methods=['POST'])
def extract_seal():
    input_path = None
    try:
        if 'file' not in request.files:
            return jsonify({'error': '没有文件'}), 400

        file = request.files['file']
        if file.filename == '' or '.' not in file.filename:
            return jsonify({'error': '未选择文件'}), 400

        ext = get_ext(file.filename)
        if ext not in IMAGE_EXTS:
            return jsonify({'error': '请上传 JPG 或 PNG 图片'}), 400

        unique_name = str(uuid.uuid4())
        input_path = os.path.join(UPLOAD_FOLDER, unique_name + '.' + ext)
        file.save(input_path)

        output_filename = f'{unique_name}.png'
        output_path = os.path.join(OUTPUT_FOLDER, output_filename)
        extract_red_seal(input_path, output_path)

        if not os.path.exists(output_path):
            return jsonify({'error': '抠章失败，未检测到红色印章'}), 500

        original_base = file.filename.rsplit('.', 1)[0]
        return jsonify({
            'success': True,
            'filename': output_filename,
            'display_name': f'{original_base}_印章.png'
        })

    except Exception as e:
        app.logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500
    finally:
        if input_path and os.path.exists(input_path):
            os.remove(input_path)


@app.route('/api/feedback', methods=['POST'])
def feedback():
    try:
        data = request.get_json(silent=True) or {}
        message = (data.get('message') or request.form.get('message', '')).strip()
        contact = (data.get('contact') or request.form.get('contact', '')).strip()
        if not message:
            return jsonify({'error': '请填写反馈内容'}), 400
        if len(message) > 2000:
            return jsonify({'error': '内容太长，请控制在2000字以内'}), 400
        import feedback_utils
        feedback_utils.submit_feedback(message, contact)
        return jsonify({'success': True})
    except Exception as e:
        app.logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500


@app.route('/api/translate', methods=['POST'])
def translate():
    try:
        data = request.get_json(silent=True) or {}
        text = (data.get('text') or request.form.get('text', '')).strip()
        source = data.get('from') or request.form.get('from', 'auto')
        target = data.get('to') or request.form.get('to', 'en')

        if not text:
            return jsonify({'error': '请输入要翻译的文本'}), 400
        if len(text) > 5000:
            return jsonify({'error': '文本过长，请控制在 5000 字以内'}), 400

        result = translate_text(text, source, target)
        usage_stats.bump('translate_text')

        return jsonify({
            'success': True,
            'text': result,
            'from': source,
            'to': target
        })

    except Exception as e:
        app.logger.error(traceback.format_exc())
        return jsonify({'error': f'翻译失败：{str(e)}'}), 500


def _save_uploads(files, allowed_exts=None):
    paths = []
    for f in files:
        if not f or f.filename == '' or '.' not in f.filename:
            continue
        ext = get_ext(f.filename)
        if allowed_exts and ext not in allowed_exts:
            raise ValueError(f'不支持的文件格式：{f.filename}')
        uid = str(uuid.uuid4())
        path = os.path.join(UPLOAD_FOLDER, f'{uid}.{ext}')
        f.save(path)
        paths.append(path)
    return paths


def _cleanup(paths):
    for p in paths:
        if p and os.path.exists(p):
            os.remove(p)


def _ok(filename, display_name=None):
    return jsonify({
        'success': True,
        'filename': filename,
        'display_name': display_name or filename,
    })


@app.route('/api/pdf/merge', methods=['POST'])
def pdf_merge():
    paths = []
    try:
        files = request.files.getlist('files')
        if not files:
            files = [request.files.get('file')]
        paths = _save_uploads(files, {'pdf'})
        if len(paths) < 2:
            return jsonify({'error': '请至少选择 2 个 PDF 文件'}), 400
        uid = str(uuid.uuid4())
        out_name = f'{uid}.pdf'
        out_path = os.path.join(OUTPUT_FOLDER, out_name)
        merge_pdfs(paths, out_path)
        return _ok(out_name, '合并结果.pdf')
    except Exception as e:
        app.logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500
    finally:
        _cleanup(paths)


@app.route('/api/pdf/split', methods=['POST'])
def pdf_split():
    path = None
    try:
        f = request.files.get('file')
        if not f:
            return jsonify({'error': '请上传 PDF 文件'}), 400
        paths = _save_uploads([f], {'pdf'})
        path = paths[0]
        mode = request.form.get('mode', 'each')
        uid = str(uuid.uuid4())
        zip_path = split_pdf(path, OUTPUT_FOLDER, uid, mode)
        return _ok(os.path.basename(zip_path), '拆分结果.zip')
    except Exception as e:
        app.logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500
    finally:
        _cleanup([path] if path else [])


@app.route('/api/pdf/rotate', methods=['POST'])
def pdf_rotate():
    path = None
    try:
        f = request.files.get('file')
        if not f:
            return jsonify({'error': '请上传 PDF 文件'}), 400
        paths = _save_uploads([f], {'pdf'})
        path = paths[0]
        angle = int(request.form.get('angle', 90))
        uid = str(uuid.uuid4())
        out_name = f'{uid}.pdf'
        rotate_pdf(path, os.path.join(OUTPUT_FOLDER, out_name), angle)
        return _ok(out_name, '旋转结果.pdf')
    except Exception as e:
        app.logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500
    finally:
        _cleanup([path] if path else [])


@app.route('/api/pdf/compress', methods=['POST'])
def pdf_compress():
    path = None
    try:
        f = request.files.get('file')
        if not f:
            return jsonify({'error': '请上传 PDF 文件'}), 400
        paths = _save_uploads([f], {'pdf'})
        path = paths[0]
        uid = str(uuid.uuid4())
        out_name = f'{uid}.pdf'
        out_path = os.path.join(OUTPUT_FOLDER, out_name)
        compress_pdf(path, out_path)
        orig = os.path.getsize(path)
        new = os.path.getsize(out_path)
        hint = ''
        if new >= orig * 0.95:
            hint = '（此文件已较精简，压缩空间有限）'
        return jsonify({
            'success': True,
            'filename': out_name,
            'display_name': f'压缩结果{hint}.pdf',
        })
    except Exception as e:
        app.logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500
    finally:
        _cleanup([path] if path else [])


@app.route('/api/pdf/to-images', methods=['POST'])
def pdf_to_images():
    path = None
    try:
        f = request.files.get('file')
        if not f:
            return jsonify({'error': '请上传 PDF 文件'}), 400
        paths = _save_uploads([f], {'pdf'})
        path = paths[0]
        uid = str(uuid.uuid4())
        result_path = pdf_to_images_zip(path, OUTPUT_FOLDER, uid)
        out_name = os.path.basename(result_path)
        display_name = 'PDF图片.png' if out_name.endswith('.png') else 'PDF图片.zip'
        return _ok(out_name, display_name)
    except Exception as e:
        app.logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500
    finally:
        _cleanup([path] if path else [])


@app.route('/api/images/to-pdf', methods=['POST'])
def images_to_pdf_route():
    paths = []
    try:
        files = request.files.getlist('files')
        if not files:
            files = [request.files.get('file')]
        paths = _save_uploads(files, IMAGE_EXTS)
        if not paths:
            return jsonify({'error': '请上传图片文件'}), 400
        uid = str(uuid.uuid4())
        out_name = f'{uid}.pdf'
        images_to_pdf(paths, os.path.join(OUTPUT_FOLDER, out_name))
        return _ok(out_name, '图片合并.pdf')
    except Exception as e:
        app.logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500
    finally:
        _cleanup(paths)


@app.route('/api/images/to-pdf/export', methods=['POST'])
def images_to_pdf_export_route():
    paths = []
    try:
        files = request.files.getlist('files')
        if not files:
            return jsonify({'error': '请上传图片文件'}), 400
        paths = _save_uploads(files, IMAGE_EXTS)
        if not paths:
            return jsonify({'error': '请上传图片文件'}), 400

        rotations_raw = request.form.get('rotations', '[]')
        try:
            rotations = json.loads(rotations_raw)
        except Exception:
            rotations = []
        uniform_size = request.form.get('uniform_size', '') or None

        uid = str(uuid.uuid4())
        out_name = f'{uid}.pdf'
        images_to_pdf_export(
            paths, rotations, os.path.join(OUTPUT_FOLDER, out_name),
            uniform_size=uniform_size,
        )
        return _ok(out_name, '图片转PDF.pdf')
    except Exception as e:
        app.logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500
    finally:
        _cleanup(paths)


@app.route('/api/image/compress', methods=['POST'])
def image_compress_route():
    path = None
    try:
        f = request.files.get('file')
        if not f:
            return jsonify({'error': '请上传图片'}), 400
        paths = _save_uploads([f], IMAGE_EXTS)
        path = paths[0]
        quality = int(request.form.get('quality', 80))
        uid = str(uuid.uuid4())
        out_name = f'{uid}.jpg'
        compress_image(path, os.path.join(OUTPUT_FOLDER, out_name), quality)
        return _ok(out_name, '压缩图片.jpg')
    except Exception as e:
        app.logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500
    finally:
        _cleanup([path] if path else [])


@app.route('/api/image/resize', methods=['POST'])
def image_resize_route():
    path = None
    try:
        f = request.files.get('file')
        if not f:
            return jsonify({'error': '请上传图片'}), 400
        paths = _save_uploads([f], IMAGE_EXTS)
        path = paths[0]
        width = request.form.get('width') or None
        height = request.form.get('height') or None
        ext = get_ext(f.filename)
        uid = str(uuid.uuid4())
        out_name = f'{uid}.{ext}'
        resize_image(path, os.path.join(OUTPUT_FOLDER, out_name), width, height)
        return _ok(out_name, f'调整尺寸.{ext}')
    except Exception as e:
        app.logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500
    finally:
        _cleanup([path] if path else [])


@app.route('/api/image/rotate', methods=['POST'])
def image_rotate_route():
    path = None
    try:
        f = request.files.get('file')
        if not f:
            return jsonify({'error': '请上传图片'}), 400
        paths = _save_uploads([f], IMAGE_EXTS)
        path = paths[0]
        degrees = request.form.get('degrees', '90')
        ext = get_ext(f.filename)
        uid = str(uuid.uuid4())
        out_name = f'{uid}.{ext}'
        rotate_image(path, os.path.join(OUTPUT_FOLDER, out_name), degrees)
        return _ok(out_name, f'旋转图片.{ext}')
    except Exception as e:
        app.logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500
    finally:
        _cleanup([path] if path else [])


@app.route('/api/image/convert', methods=['POST'])
def image_convert_route():
    path = None
    try:
        f = request.files.get('file')
        if not f:
            return jsonify({'error': '请上传图片'}), 400
        paths = _save_uploads([f], IMAGE_EXTS)
        path = paths[0]
        fmt = request.form.get('format', 'png')
        uid = str(uuid.uuid4())
        out_name = f'{uid}.{fmt}'
        convert_image_format(path, os.path.join(OUTPUT_FOLDER, out_name), fmt)
        return _ok(out_name, f'转换结果.{fmt}')
    except Exception as e:
        app.logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500
    finally:
        _cleanup([path] if path else [])


@app.route('/api/pdf/delete-pages', methods=['POST'])
def pdf_delete_pages():
    path = None
    try:
        f = request.files.get('file')
        pages = request.form.get('pages', '')
        if not f:
            return jsonify({'error': '请上传 PDF 文件'}), 400
        paths = _save_uploads([f], {'pdf'})
        path = paths[0]
        uid = str(uuid.uuid4())
        out_name = f'{uid}.pdf'
        delete_pdf_pages(path, os.path.join(OUTPUT_FOLDER, out_name), pages)
        return _ok(out_name, '删除页面后.pdf')
    except Exception as e:
        app.logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500
    finally:
        _cleanup([path] if path else [])


@app.route('/api/pdf/watermark', methods=['POST'])
def pdf_watermark():
    path = None
    try:
        f = request.files.get('file')
        text = request.form.get('text', '')
        if not f:
            return jsonify({'error': '请上传 PDF 文件'}), 400
        paths = _save_uploads([f], {'pdf'})
        path = paths[0]
        uid = str(uuid.uuid4())
        out_name = f'{uid}.pdf'
        add_pdf_watermark(path, os.path.join(OUTPUT_FOLDER, out_name), text)
        return _ok(out_name, '加水印后.pdf')
    except Exception as e:
        app.logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500
    finally:
        _cleanup([path] if path else [])


@app.route('/api/pdf/encrypt', methods=['POST'])
def pdf_encrypt():
    path = None
    try:
        f = request.files.get('file')
        password = request.form.get('password', '')
        if not f:
            return jsonify({'error': '请上传 PDF 文件'}), 400
        paths = _save_uploads([f], {'pdf'})
        path = paths[0]
        uid = str(uuid.uuid4())
        out_name = f'{uid}.pdf'
        encrypt_pdf(path, os.path.join(OUTPUT_FOLDER, out_name), password)
        return _ok(out_name, '加密后.pdf')
    except Exception as e:
        app.logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500
    finally:
        _cleanup([path] if path else [])


@app.route('/api/pdf/decrypt', methods=['POST'])
def pdf_decrypt():
    path = None
    try:
        f = request.files.get('file')
        password = request.form.get('password', '')
        if not f:
            return jsonify({'error': '请上传 PDF 文件'}), 400
        paths = _save_uploads([f], {'pdf'})
        path = paths[0]
        uid = str(uuid.uuid4())
        out_name = f'{uid}.pdf'
        decrypt_pdf(path, os.path.join(OUTPUT_FOLDER, out_name), password)
        return _ok(out_name, '解密后.pdf')
    except Exception as e:
        app.logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500
    finally:
        _cleanup([path] if path else [])


@app.route('/api/pdf/grayscale', methods=['POST'])
def pdf_grayscale():
    path = None
    try:
        f = request.files.get('file')
        if not f:
            return jsonify({'error': '请上传 PDF 文件'}), 400
        paths = _save_uploads([f], {'pdf'})
        path = paths[0]
        uid = str(uuid.uuid4())
        out_name = f'{uid}.pdf'
        pdf_to_grayscale(path, os.path.join(OUTPUT_FOLDER, out_name))
        return _ok(out_name, '黑白版.pdf')
    except Exception as e:
        app.logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500
    finally:
        _cleanup([path] if path else [])


@app.route('/api/image/watermark', methods=['POST'])
def image_watermark():
    paths = []
    try:
        files = request.files.getlist('files')
        if not files:
            files = [request.files.get('file')]
        text = request.form.get('text', '')
        paths = _save_uploads(files, IMAGE_EXTS)
        if not paths:
            return jsonify({'error': '请上传图片'}), 400
        uid = str(uuid.uuid4())
        if len(paths) == 1:
            ext = get_ext(files[0].filename) or 'png'
            out_name = f'{uid}.{ext}'
            add_image_watermark(paths[0], os.path.join(OUTPUT_FOLDER, out_name), text)
            return _ok(out_name, '加水印图片.' + ext)
        zip_path = batch_process_images(
            paths,
            lambda s, o: add_image_watermark(s, o, text),
            OUTPUT_FOLDER, uid, 'png',
        )
        return _ok(os.path.basename(zip_path), '批量加水印.zip')
    except Exception as e:
        app.logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500
    finally:
        _cleanup(paths)


@app.route('/api/image/timestamp', methods=['POST'])
def image_timestamp():
    paths = []
    try:
        files = request.files.getlist('files')
        if not files:
            files = [request.files.get('file')]
        paths = _save_uploads(files, IMAGE_EXTS)
        if not paths:
            return jsonify({'error': '请上传图片'}), 400
        uid = str(uuid.uuid4())
        if len(paths) == 1:
            ext = get_ext(files[0].filename) or 'jpg'
            out_name = f'{uid}.{ext}'
            add_image_timestamp(paths[0], os.path.join(OUTPUT_FOLDER, out_name))
            return _ok(out_name, '加时间戳.' + ext)
        zip_path = batch_process_images(
            paths, add_image_timestamp, OUTPUT_FOLDER, uid, 'jpg',
        )
        return _ok(os.path.basename(zip_path), '批量加时间戳.zip')
    except Exception as e:
        app.logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500
    finally:
        _cleanup(paths)


@app.route('/api/pdf/extract-images', methods=['POST'])
def pdf_extract_images():
    path = None
    try:
        f = request.files.get('file')
        if not f:
            return jsonify({'error': '请上传 PDF 文件'}), 400
        paths = _save_uploads([f], {'pdf'})
        path = paths[0]
        uid = str(uuid.uuid4())
        zip_path = extract_pdf_images_zip(path, OUTPUT_FOLDER, uid)
        return _ok(os.path.basename(zip_path), '提取的图片.zip')
    except Exception as e:
        app.logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500
    finally:
        _cleanup([path] if path else [])


@app.route('/api/translate/file', methods=['POST'])
def translate_file():
    path = None
    try:
        f = request.files.get('file')
        if not f or f.filename == '':
            return jsonify({'error': '请上传文件'}), 400
        ext = get_ext(f.filename)
        if ext not in {'txt', 'doc', 'docx', 'pdf'}:
            return jsonify({'error': '支持 TXT、Word、PDF 文件'}), 400
        source = request.form.get('from', 'auto')
        target = request.form.get('to', 'en')
        out_format = request.form.get('format', 'txt')
        path = os.path.join(UPLOAD_FOLDER, str(uuid.uuid4()) + '.' + ext)
        f.save(path)
        raw = extract_text_from_file(path, ext, ocr_pdf)
        if not raw:
            return jsonify({'error': '文件里没有读到可翻译的文字'}), 400
        if len(raw) > 30000:
            return jsonify({'error': '文件文字太多，请截取部分或拆分后再翻译'}), 400
        translated = translate_long_text(raw, source, target)
        usage_stats.bump('translate_file')
        uid = str(uuid.uuid4())
        _, display = translated_to_output(translated, OUTPUT_FOLDER, uid, out_format)
        fname = f'{uid}.{out_format}'
        return _ok(fname, display)
    except Exception as e:
        app.logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500
    finally:
        _cleanup([path] if path else [])


@app.route('/api/pdf/thumbnails', methods=['POST'])
def pdf_thumbnails_route():
    path = None
    try:
        f = request.files.get('file')
        if not f:
            return jsonify({'error': '请上传 PDF 文件'}), 400
        paths = _save_uploads([f], {'pdf'})
        path = paths[0]
        password = request.form.get('password', '') or None

        # Decrypt encrypted PDFs so the session file is always usable
        if password:
            import fitz as _fitz
            _doc = _fitz.open(path)
            if _doc.is_encrypted:
                if not _doc.authenticate(password):
                    _doc.close()
                    raise ValueError('密码错误，PDF 无法打开')
                dec_path = os.path.join(UPLOAD_FOLDER, str(uuid.uuid4()) + '.pdf')
                _doc.save(dec_path, encryption=_fitz.PDF_ENCRYPT_NONE)
                _doc.close()
                os.remove(path)
                path = dec_path
            else:
                _doc.close()

        from pdf_utils import pdf_thumbnails
        thumbs = pdf_thumbnails(path)
        session_file = os.path.basename(path)
        path = None  # keep the file — it's needed for export
        return jsonify({
            'success': True,
            'session_file': session_file,
            'thumbnails': thumbs,
            'page_count': len(thumbs),
        })
    except Exception as e:
        app.logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500
    finally:
        if path and os.path.exists(path):
            os.remove(path)


@app.route('/api/pdf/editor/preview', methods=['GET'])
def pdf_editor_preview_route():
    try:
        fname = secure_filename(request.args.get('file', ''))
        idx = int(request.args.get('idx', '-1'))
        if not fname:
            return jsonify({'error': '无效的文件引用'}), 400
        fpath = os.path.join(UPLOAD_FOLDER, fname)
        if not os.path.exists(fpath):
            return jsonify({'error': '源文件已过期，请重新上传'}), 400

        from pdf_utils import pdf_page_preview
        data_uri = pdf_page_preview(fpath, idx)
        return jsonify({'success': True, 'image': data_uri})
    except Exception as e:
        app.logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500


@app.route('/api/pdf/editor/export', methods=['POST'])
def pdf_editor_export_route():
    output_path = None
    try:
        pages_json = request.form.get('pages', '[]')
        try:
            pages_spec = json.loads(pages_json)
        except Exception:
            return jsonify({'error': '页面顺序参数无效'}), 400
        if not pages_spec:
            return jsonify({'error': '没有页面数据'}), 400

        uniform_size     = request.form.get('uniform_size', '') or None
        watermark_text   = request.form.get('watermark_text', '') or None
        grayscale        = request.form.get('grayscale', 'false').lower() == 'true'
        encrypt_password = request.form.get('encrypt_password', '') or None
        rotate_deg       = int(request.form.get('rotate_deg', '0') or '0')
        compress         = request.form.get('compress', 'false').lower() == 'true'
        compress_target_mb = request.form.get('compress_target_mb', '') or None
        if compress_target_mb:
            compress_target_mb = float(compress_target_mb)

        for item in pages_spec:
            fname = secure_filename(item.get('file', ''))
            if not fname:
                return jsonify({'error': '无效的文件引用'}), 400
            item['file'] = fname
            if not os.path.exists(os.path.join(UPLOAD_FOLDER, fname)):
                return jsonify({'error': '源文件已过期，请重新上传'}), 400

        uid = str(uuid.uuid4())
        out_name = f'{uid}.pdf'
        output_path = os.path.join(OUTPUT_FOLDER, out_name)

        from pdf_utils import pdf_editor_export
        pdf_editor_export(
            UPLOAD_FOLDER, pages_spec, output_path,
            uniform_size=uniform_size,
            watermark_text=watermark_text,
            grayscale=grayscale,
            encrypt_password=encrypt_password,
            rotate_deg=rotate_deg,
            compress=compress,
            compress_target_mb=compress_target_mb,
        )
        return _ok(out_name, '编辑结果.pdf')
    except Exception as e:
        app.logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500


@app.route('/api/download/<filename>', methods=['GET'])
def download(filename):
    file_path = os.path.join(OUTPUT_FOLDER, secure_filename(filename))
    if not os.path.exists(file_path):
        return jsonify({'error': '文件不存在或已过期'}), 404
    response = send_file(file_path, as_attachment=True)
    os.remove(file_path)
    return response


@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok'})


if __name__ == '__main__':
    debug = os.environ.get('FLASK_DEBUG', '0') == '1'
    app.run(host='0.0.0.0', port=5000, debug=debug)