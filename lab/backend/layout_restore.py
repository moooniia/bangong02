# -*- coding: utf-8 -*-
"""Lab-only post step after Volcengine parse.

Crop red seals and handwriting-like strokes from the original PDF page,
then place them as floating pictures at the same relative page position.
Does not invent font names. Uses size, color, or position only when the
OCR detail or the page image actually has them.
"""
import os
import re
import shutil
import tempfile

import cv2
import numpy as np

_RENDER_DPI = 150
_MAX_PER_PAGE = 8
_FLOAT_ID = [8800]


def _render_pages(pdf_path, dpi=_RENDER_DPI):
    import fitz

    doc = fitz.open(pdf_path)
    pages = []
    try:
        mat = fitz.Matrix(dpi / 72.0, dpi / 72.0)
        for page in doc:
            pix = page.get_pixmap(matrix=mat, alpha=False)
            arr = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
            if pix.n == 4:
                bgr = cv2.cvtColor(arr, cv2.COLOR_RGBA2BGR)
            else:
                bgr = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
            pages.append((bgr, float(page.rect.width), float(page.rect.height)))
    finally:
        doc.close()
    return pages


def _page_hw(detail, img_w, img_h):
    hw = (detail or {}).get("page_image_hw") or {}
    pw = float(hw.get("w") or hw.get("width") or img_w or 1)
    ph = float(hw.get("h") or hw.get("height") or img_h or 1)
    return pw, ph


def _scaled_text_boxes(detail, img_w, img_h):
    pw, ph = _page_hw(detail, img_w, img_h)
    sx = img_w / max(pw, 1.0)
    sy = img_h / max(ph, 1.0)
    boxes = []
    for blk in (detail or {}).get("textblocks") or []:
        label = (blk.get("label") or "").lower()
        if label in ("image", "table"):
            continue
        box = blk.get("box") or {}
        try:
            x0 = int(float(box.get("x0") or 0) * sx)
            y0 = int(float(box.get("y0") or 0) * sy)
            x1 = int(float(box.get("x1") or 0) * sx)
            y1 = int(float(box.get("y1") or 0) * sy)
        except (TypeError, ValueError):
            continue
        if x1 <= x0 or y1 <= y0:
            continue
        bw, bh = x1 - x0, y1 - y0
        # A box covering most of the page is not a printed line.
        if bw > img_w * 0.92 and bh > img_h * 0.92:
            continue
        boxes.append((x0, y0, x1, y1))
    return boxes


def _iou(a, b):
    ax0, ay0, ax1, ay1 = a
    bx0, by0, bx1, by1 = b
    ix0, iy0 = max(ax0, bx0), max(ay0, by0)
    ix1, iy1 = min(ax1, bx1), min(ay1, by1)
    if ix1 <= ix0 or iy1 <= iy0:
        return 0.0
    inter = (ix1 - ix0) * (iy1 - iy0)
    area = max((ax1 - ax0) * (ay1 - ay0), 1)
    return inter / float(area)


def _too_big(bw, bh, img_w, img_h):
    if bw > img_w * 0.50 or bh > img_h * 0.42:
        return True
    if bw * bh > 0.16 * img_w * img_h:
        return True
    return False


def _save_rgba(path, rgba):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    cv2.imwrite(path, rgba)


def _detect_seals(img, out_dir, page_index):
    from seal_utils import extract_red_seals_from_image, red_mask, _make_seal_rgba

    h, w = img.shape[:2]
    found = []
    tmp = os.path.join(out_dir, "_page.png")
    cv2.imwrite(tmp, img)
    try:
        seals = extract_red_seals_from_image(tmp, os.path.join(out_dir, "round"))
    except Exception:
        seals = []
    for seal in seals:
        if _too_big(seal["w"], seal["h"], w, h):
            continue
        found.append({
            "kind": "seal",
            "path": seal["path"],
            "x": seal["x"],
            "y": seal["y"],
            "w": seal["w"],
            "h": seal["h"],
        })

    mask = red_mask(img)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (11, 11))
    merged = cv2.dilate(mask, kernel, iterations=1)
    merged = cv2.morphologyEx(merged, cv2.MORPH_CLOSE, kernel, iterations=1)
    contours, _ = cv2.findContours(merged, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    edge_i = 0
    for cnt in contours:
        x, y, bw, bh = cv2.boundingRect(cnt)
        if bw < 28 or bh < 28:
            continue
        if _too_big(bw, bh, w, h):
            continue
        touches = x <= 6 or y <= 6 or (x + bw) >= w - 6 or (y + bh) >= h - 6
        ratio = bw / float(max(bh, 1))
        if touches:
            if ratio < 0.12 or ratio > 4.5:
                continue
        elif ratio < 0.45 or ratio > 2.3:
            continue
        pieces = [(x, y, bw, bh)]
        if bh > bw * 2.4 and bh > 90:
            column = mask[y:y + bh, x:x + bw]
            row_sum = (column > 0).sum(axis=1)
            gap = row_sum < max(2, int(bw * 0.04))
            spans = []
            start = None
            for ri, is_gap in enumerate(gap):
                if not is_gap and start is None:
                    start = ri
                elif is_gap and start is not None:
                    if ri - start > 24:
                        spans.append((start, ri))
                    start = None
            if start is not None and bh - start > 24:
                spans.append((start, bh))
            if len(spans) >= 2:
                pieces = [(x, y + a, bw, b - a) for a, b in spans]
        for px, py, pbw, pbh in pieces:
            x, y, bw, bh = px, py, pbw, pbh
            if bw < 28 or bh < 28 or _too_big(bw, bh, w, h):
                continue
            crop_mask = mask[y:y + bh, x:x + bw]
            red_px = int(cv2.countNonZero(crop_mask))
            if red_px < (180 if touches else 700):
                continue
            if red_px / float(max(bw * bh, 1)) < (0.035 if touches else 0.06):
                continue
            box = (x, y, x + bw, y + bh)
            if any(_iou(box, (s["x"], s["y"], s["x"] + s["w"], s["y"] + s["h"])) > 0.45 for s in found):
                continue
            pad = 6
            x0, y0 = max(0, x - pad), max(0, y - pad)
            x1, y1 = min(w, x + bw + pad), min(h, y + bh + pad)
            rgba = _make_seal_rgba(img[y0:y1, x0:x1])
            if rgba is None or cv2.countNonZero(rgba[:, :, 3]) < 80:
                continue
            path = os.path.join(out_dir, "edge_p%d_%d.png" % (page_index, edge_i))
            edge_i += 1
            _save_rgba(path, rgba)
            found.append({
                "kind": "seal",
                "path": path,
                "x": x0,
                "y": y0,
                "w": x1 - x0,
                "h": y1 - y0,
            })
            if len(found) >= _MAX_PER_PAGE:
                return found[:_MAX_PER_PAGE]
    return found[:_MAX_PER_PAGE]


def _detect_signatures(img, text_boxes, seal_boxes, out_dir, page_index):
    h, w = img.shape[:2]
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    from seal_utils import red_mask

    ink = np.zeros((h, w), dtype=np.uint8)
    ink[gray < 125] = 255
    ink[red_mask(img) > 0] = 0
    horiz = cv2.morphologyEx(ink, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (36, 1)))
    vert = cv2.morphologyEx(ink, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (1, 36)))
    ink[horiz > 0] = 0
    ink[vert > 0] = 0

    # Drop only thin OCR lines. Large table cells stay, so a signature inside a cell can remain.
    for x0, y0, x1, y1 in text_boxes:
        bw, bh = x1 - x0, y1 - y0
        if bh <= 0 or bw <= 0:
            continue
        if bh < h * 0.045 and bw < w * 0.72:
            y0p, y1p = max(0, y0 - 2), min(h, y1 + 2)
            x0p, x1p = max(0, x0 - 2), min(w, x1 + 2)
            ink[y0p:y1p, x0p:x1p] = 0

    merged = cv2.dilate(ink, np.ones((5, 5), np.uint8), iterations=2)
    contours, _ = cv2.findContours(merged, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cands = []
    for cnt in contours:
        x, y, bw, bh = cv2.boundingRect(cnt)
        if bw < 48 or bh < 28:
            continue
        if _too_big(bw, bh, w, h):
            continue
        aspect = bw / float(max(bh, 1))
        # A signature is a wide stroke, not a square character and not a text line.
        if aspect > 4.8 or aspect < 1.15:
            continue
        area = cv2.contourArea(cnt)
        fill = area / float(max(bw * bh, 1))
        if fill > 0.55 or fill < 0.10:
            continue
        hull = cv2.convexHull(cnt)
        hull_area = cv2.contourArea(hull)
        if hull_area <= 1:
            continue
        solidity = area / hull_area
        if solidity > 0.82:
            continue
        crop = ink[y:y + bh, x:x + bw]
        dark = int(cv2.countNonZero(crop))
        if dark < 140:
            continue
        box = (x, y, x + bw, y + bh)
        if any(_iou(box, sb) > 0.35 for sb in seal_boxes):
            continue
        cands.append((x, y, bw, bh, dark))
    isolated = []
    for x, y, bw, bh, dark in cands:
        band = 0
        for ox, oy, ow, oh, _d in cands:
            if ox == x and oy == y and ow == bw and oh == bh:
                continue
            if abs((oy + oh / 2.0) - (y + bh / 2.0)) < max(bh, oh) * 0.55 and abs(oh - bh) < max(bh, oh) * 0.45:
                band += 1
        if band >= 2:
            continue
        isolated.append((x, y, bw, bh, dark))
    cands = isolated

    cands.sort(key=lambda t: t[4], reverse=True)
    kept = []
    sigs = []
    for x, y, bw, bh, _dark in cands:
        cx, cy = x + bw / 2.0, y + bh / 2.0
        if any(abs(cx - (k[0] + k[2] / 2.0)) < min(bw, k[2]) * 0.5 and abs(cy - (k[1] + k[3] / 2.0)) < min(bh, k[3]) * 0.5 for k in kept):
            continue
        kept.append((x, y, bw, bh))
        pad = 4
        x0, y0 = max(0, x - pad), max(0, y - pad)
        x1, y1 = min(w, x + bw + pad), min(h, y + bh + pad)
        crop = img[y0:y1, x0:x1]
        crop_gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        _thr, alpha = cv2.threshold(crop_gray, 150, 255, cv2.THRESH_BINARY_INV)
        alpha[red_mask(crop) > 0] = 0
        if cv2.countNonZero(alpha) < 60:
            continue
        b = np.where(alpha > 0, np.minimum(crop[:, :, 0], 70), 0).astype(np.uint8)
        g = np.where(alpha > 0, np.minimum(crop[:, :, 1], 70), 0).astype(np.uint8)
        r = np.where(alpha > 0, np.minimum(crop[:, :, 2], 70), 0).astype(np.uint8)
        rgba = cv2.merge([b, g, r, alpha])
        path = os.path.join(out_dir, "sig_p%d_%d.png" % (page_index, len(sigs)))
        _save_rgba(path, rgba)
        sigs.append({
            "kind": "signature",
            "path": path,
            "x": x0,
            "y": y0,
            "w": x1 - x0,
            "h": y1 - y0,
        })
        if len(sigs) >= 4:
            break
    return sigs


def collect_overlays(pdf_path, pages_detail, work_dir):
    rendered = _render_pages(pdf_path)
    pages_detail = pages_detail or []
    overlays = []
    for i, (img, _pw_pt, _ph_pt) in enumerate(rendered):
        h, w = img.shape[:2]
        detail = pages_detail[i] if i < len(pages_detail) else {}
        page_dir = os.path.join(work_dir, "p%d" % i)
        os.makedirs(page_dir, exist_ok=True)
        seals = _detect_seals(img, page_dir, i)
        seal_boxes = [(s["x"], s["y"], s["x"] + s["w"], s["y"] + s["h"]) for s in seals]
        text_boxes = _scaled_text_boxes(detail, w, h)
        sigs = _detect_signatures(img, text_boxes, seal_boxes, page_dir, i)
        for item in seals + sigs:
            item["page"] = i
            item["img_w"] = w
            item["img_h"] = h
            overlays.append(item)
    return overlays


def _page_break_indexes(body):
    from docx.oxml.ns import qn

    breaks = []
    for i, child in enumerate(list(body)):
        if child.tag != qn("w:p"):
            continue
        for br in child.iter(qn("w:br")):
            if br.get(qn("w:type")) == "page":
                breaks.append(i)
                break
    return breaks


def _section_emu(doc):
    sec = doc.sections[-1]
    return int(sec.page_width), int(sec.page_height)


def _add_floating(doc, image_path, pos_x, pos_y, width, height, insert_at):
    from docx.shared import Emu
    from lxml import etree
    from docx.oxml.ns import qn

    if not image_path or not os.path.isfile(image_path):
        return False
    if width < 1 or height < 1:
        return False
    tmp_para = doc.add_paragraph()
    tmp_run = tmp_para.add_run()
    try:
        tmp_run.add_picture(image_path, width=Emu(max(int(width), 1)))
    except Exception:
        el = tmp_para._p
        if el.getparent() is not None:
            el.getparent().remove(el)
        return False
    xml = etree.tostring(tmp_para._p, encoding="unicode")
    rid_m = re.search(r'r:embed="(rId\d+)"', xml)
    parent = tmp_para._p.getparent()
    if parent is not None:
        parent.remove(tmp_para._p)
    if not rid_m:
        return False
    r_id = rid_m.group(1)
    img_id = _FLOAT_ID[0]
    _FLOAT_ID[0] += 1
    anchor = (
        '<w:p xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        '<w:pPr><w:spacing w:before="0" w:after="0" w:line="20" w:lineRule="exact"/>'
        '<w:rPr><w:sz w:val="2"/></w:rPr></w:pPr>'
        "<w:r><w:drawing>"
        '<wp:anchor xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"'
        ' distT="0" distB="0" distL="0" distR="0" simplePos="0"'
        ' relativeHeight="251658240" behindDoc="0" locked="0"'
        ' layoutInCell="1" allowOverlap="1">'
        '<wp:simplePos x="0" y="0"/>'
        '<wp:positionH relativeFrom="page"><wp:posOffset>%d</wp:posOffset></wp:positionH>'
        '<wp:positionV relativeFrom="page"><wp:posOffset>%d</wp:posOffset></wp:positionV>'
        '<wp:extent cx="%d" cy="%d"/>'
        '<wp:effectExtent l="0" t="0" r="0" b="0"/>'
        "<wp:wrapNone/>"
        '<wp:docPr id="%d" name="LayoutRestore%d"/>'
        "<wp:cNvGraphicFramePr>"
        '<a:graphicFrameLocks xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" noChangeAspect="1"/>'
        "</wp:cNvGraphicFramePr>"
        '<a:graphic xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">'
        '<a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture">'
        '<pic:pic xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture">'
        '<pic:nvPicPr><pic:cNvPr id="%d" name="LayoutRestore%d"/><pic:cNvPicPr/></pic:nvPicPr>'
        "<pic:blipFill>"
        '<a:blip xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" r:embed="%s"/>'
        "<a:stretch><a:fillRect/></a:stretch>"
        "</pic:blipFill>"
        "<pic:spPr>"
        '<a:xfrm><a:off x="0" y="0"/><a:ext cx="%d" cy="%d"/></a:xfrm>'
        '<a:prstGeom prst="rect"><a:avLst/></a:prstGeom>'
        "</pic:spPr></pic:pic></a:graphicData></a:graphic>"
        "</wp:anchor></w:drawing></w:r></w:p>"
    ) % (
        int(pos_x), int(pos_y), int(width), int(height),
        img_id, img_id, img_id, img_id, r_id, int(width), int(height),
    )
    try:
        elem = etree.fromstring(anchor)
    except etree.XMLSyntaxError:
        return False
    body = doc.element.body
    children = list(body)
    # Keep sectPr last.
    sect = None
    if children and children[-1].tag == qn("w:sectPr"):
        sect = children[-1]
        children = children[:-1]
    insert_at = max(0, min(int(insert_at), len(children)))
    if insert_at >= len(children):
        if sect is not None:
            sect.addprevious(elem)
        else:
            body.append(elem)
    else:
        children[insert_at].addprevious(elem)
    return True


def _table_rows_from_block(block):
    html = block.get("text") or ""
    if "<table" in html.lower():
        rows = []
        for row_html in re.findall(r"<tr[^>]*>(.*?)</tr>", html, flags=re.I | re.S):
            cells = []
            for _attrs, inner in re.findall(r"<t[dh]([^>]*)>(.*?)</t[dh]>", row_html, flags=re.I | re.S):
                text = re.sub(r"<[^>]+>", "", inner)
                text = re.sub(r"\s+", " ", text).strip()
                cells.append(text)
            if cells:
                rows.append(cells)
        if rows:
            return rows
    raw = block.get("rows") or block.get("cells") or block.get("table_cells")
    if not isinstance(raw, list):
        return None
    rows = []
    for row in raw:
        if isinstance(row, dict):
            row = row.get("cells") or row.get("row") or []
        if not isinstance(row, list):
            continue
        cells = []
        for cell in row:
            if isinstance(cell, dict):
                cells.append(str(cell.get("text") or cell.get("content") or "").strip())
            else:
                cells.append(str(cell).strip())
        if cells:
            rows.append(cells)
    return rows or None


def emit_structured_table(doc, block):
    """Emit a real Word table from OCR detail. Returns True if a table was added."""
    rows = _table_rows_from_block(block)
    if not rows:
        return False
    ncols = max(len(r) for r in rows)
    if ncols < 1:
        return False
    table = doc.add_table(rows=len(rows), cols=ncols)
    table.style = "Table Grid"
    for ri, row in enumerate(rows):
        for ci in range(ncols):
            text = row[ci] if ci < len(row) else ""
            cell = table.rows[ri].cells[ci]
            cell.text = text
            _paint_cell_from_detail(cell, row, ci, block)
    return True


def _paint_cell_from_detail(cell, row, ci, block):
    """Apply size or color only when that cell's detail actually carries it."""
    from docx.shared import Pt, RGBColor

    size = None
    color = None
    raw_rows = block.get("rows") or block.get("cells") or []
    source = None
    if isinstance(raw_rows, list) and ci < len(row):
        try:
            source = raw_rows[cell_row_index(block, row)][ci]
        except Exception:
            source = None
    if isinstance(source, dict):
        size, color, _name = explicit_style(source)
    if size:
        for para in cell.paragraphs:
            for run in para.runs:
                run.font.size = Pt(max(6.0, min(28.0, float(size))))
    if color and re.fullmatch(r"[0-9A-Fa-f]{6}", color):
        rgb = RGBColor(int(color[0:2], 16), int(color[2:4], 16), int(color[4:6], 16))
        for para in cell.paragraphs:
            for run in para.runs:
                run.font.color.rgb = rgb


def cell_row_index(block, row):
    return 0


def _existing_table_text(doc):
    blobs = []
    for table in doc.tables:
        parts = []
        for row in table.rows:
            for cell in row.cells:
                parts.append(cell.text or "")
        blobs.append(" ".join(parts))
    return blobs


def _rows_fingerprint(rows):
    parts = []
    for row in rows:
        for cell in row:
            cell = (cell or "").strip()
            if len(cell) >= 2:
                parts.append(cell)
    return parts


def fill_missing_tables(doc, pages_detail):
    """If detail has a table the docx dropped, add a real table. Keep ones already present."""
    added = 0
    existing = _existing_table_text(doc)
    body = doc.element.body
    breaks = _page_break_indexes(body)
    # Insert from the last page so indexes stay valid.
    jobs = []
    for pi, page in enumerate(pages_detail or []):
        for block in page.get("textblocks") or []:
            if (block.get("label") or "").lower() != "table" and "<table" not in (block.get("text") or "").lower():
                continue
            rows = _table_rows_from_block(block)
            if not rows or len(rows) < 1:
                continue
            finger = _rows_fingerprint(rows)
            if not finger:
                continue
            joined = " ".join(existing)
            hit = sum(1 for part in finger if part in joined)
            if hit >= max(1, int(0.5 * len(finger))):
                continue
            jobs.append((pi, rows))
    for pi, rows in reversed(jobs):
        if pi == 0:
            insert_at = 0
        elif pi - 1 < len(breaks):
            insert_at = breaks[pi - 1] + 1
        else:
            insert_at = len(list(body))
        before = len(doc.tables)
        # Build table at end, then move its tbl element.
        emit_structured_table(doc, {"text": "", "rows": rows})
        if len(doc.tables) <= before:
            continue
        tbl = doc.tables[-1]._tbl
        parent = tbl.getparent()
        if parent is not None:
            parent.remove(tbl)
        children = [c for c in list(body) if c.tag != "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}sectPr"]
        insert_at = max(0, min(insert_at, len(children)))
        if insert_at >= len(children):
            sects = [c for c in list(body) if c.tag.endswith("sectPr")]
            if sects:
                sects[-1].addprevious(tbl)
            else:
                body.append(tbl)
        else:
            children[insert_at].addprevious(tbl)
        added += 1
        existing.append(" ".join(_rows_fingerprint(rows)))
    return added


def attach(doc, pdf_path, pages_detail):
    """Place seal and signature crops. Returns a small stats dict."""
    if not pdf_path or not os.path.isfile(pdf_path):
        return {"overlays": 0}
    work = tempfile.mkdtemp(prefix="layout_restore_")
    try:
        tables_added = fill_missing_tables(doc, pages_detail)
        overlays = collect_overlays(pdf_path, pages_detail, work)
        pg_w, pg_h = _section_emu(doc)
        body = doc.element.body
        breaks = _page_break_indexes(body)
        by_page = {}
        for item in overlays:
            by_page.setdefault(item["page"], []).append(item)
        placed = 0
        for pi in sorted(by_page.keys(), reverse=True):
            if pi == 0:
                insert_at = 0
            elif pi - 1 < len(breaks):
                insert_at = breaks[pi - 1] + 1
            else:
                insert_at = len([c for c in list(body)])
            for item in by_page[pi]:
                nx = item["x"] / float(max(item["img_w"], 1))
                ny = item["y"] / float(max(item["img_h"], 1))
                nw = item["w"] / float(max(item["img_w"], 1))
                nh = item["h"] / float(max(item["img_h"], 1))
                # Reject anything that would become a page-sized picture.
                if nw > 0.55 or nh > 0.45:
                    continue
                ok = _add_floating(
                    doc,
                    item["path"],
                    int(nx * pg_w),
                    int(ny * pg_h),
                    max(1, int(nw * pg_w)),
                    max(1, int(nh * pg_h)),
                    insert_at,
                )
                if ok:
                    placed += 1
        return {
            "overlays": placed,
            "detected": len(overlays),
            "tables_added": tables_added,
            "seals": sum(1 for o in overlays if o["kind"] == "seal"),
            "signatures": sum(1 for o in overlays if o["kind"] == "signature"),
        }
    finally:
        shutil.rmtree(work, ignore_errors=True)


def explicit_style(block):
    """Read font size, color, and font name only from fields on the block."""
    block = block or {}
    size = None
    for key in ("font_size", "fontSize", "font_size_pt", "size"):
        if key not in block or block.get(key) in (None, ""):
            continue
        try:
            size = float(block.get(key))
        except (TypeError, ValueError):
            continue
        if size > 0:
            break
        size = None
    color = None
    for key in ("color", "font_color", "text_color", "fontColor", "color_hex"):
        val = block.get(key)
        if not isinstance(val, str):
            continue
        m = re.search(r"#?([0-9A-Fa-f]{6})", val)
        if m:
            color = m.group(1).upper()
            break
    font_name = None
    for key in ("font_name", "fontName", "font"):
        val = block.get(key)
        if isinstance(val, str) and val.strip() and len(val.strip()) <= 40 and not val.strip().isdigit():
            font_name = val.strip()
            break
    return size, color, font_name


def sample_ink_color(rgb_arr, box, page_hw):
    if rgb_arr is None or not box or not page_hw:
        return None
    pw = float(page_hw.get("w") or page_hw.get("width") or 0)
    ph = float(page_hw.get("h") or page_hw.get("height") or 0)
    if pw <= 1 or ph <= 1:
        return None
    try:
        x0 = float(box.get("x0") or 0)
        y0 = float(box.get("y0") or 0)
        x1 = float(box.get("x1") or 0)
        y1 = float(box.get("y1") or 0)
    except (TypeError, ValueError):
        return None
    if x1 <= x0 or y1 <= y0:
        return None
    h_img, w_img = rgb_arr.shape[0], rgb_arr.shape[1]
    xs = max(0, min(w_img - 1, int(x0 / pw * w_img)))
    xe = max(xs + 1, min(w_img, int(x1 / pw * w_img)))
    ys = max(0, min(h_img - 1, int(y0 / ph * h_img)))
    ye = max(ys + 1, min(h_img, int(y1 / ph * h_img)))
    region = rgb_arr[ys:ye, xs:xe]
    if region.size == 0:
        return None
    flat = region.reshape(-1, region.shape[-1])
    step = max(1, len(flat) // 80)
    darks, blues, reds = [], [], []
    for i in range(0, len(flat), step):
        r, g, b = [int(v) for v in flat[i][:3]]
        lum = (r + g + b) / 3.0
        if lum > 225:
            continue
        if b > max(r, g) + 25 and b > 80:
            blues.append((r, g, b))
        elif r > max(g, b) + 28 and r > 90:
            reds.append((r, g, b))
        elif lum < 110:
            darks.append((r, g, b))
    if blues and len(blues) >= max(3, len(darks)):
        picks = blues
    elif reds and len(reds) > max(4, len(darks)):
        picks = reds
    else:
        picks = darks or blues or reds
    if not picks:
        return None
    r = sum(t[0] for t in picks) // len(picks)
    g = sum(t[1] for t in picks) // len(picks)
    b = sum(t[2] for t in picks) // len(picks)
    return "%02X%02X%02X" % (r, g, b)


def _box_size_pt(box, page_hw):
    if not box or not page_hw:
        return None
    ph = float(page_hw.get("h") or page_hw.get("height") or 0)
    if ph <= 1:
        return None
    try:
        y0 = float(box.get("y0") or 0)
        y1 = float(box.get("y1") or 0)
    except (TypeError, ValueError):
        return None
    bh = y1 - y0
    if bh <= 1:
        return None
    # Box height is the position detail. One line is roughly the glyph size.
    pt = bh / ph * 720.0 * 0.72
    if pt < 6 or pt > 36:
        return None
    return pt


def apply_run_style(run, block, box, page_hw, rgb_arr, label="", text="", use_box_size=False):
    """Set size and color from OCR detail or the page image. Never invent a font name."""
    from docx.shared import Pt, RGBColor
    from docx.oxml.ns import qn

    block = dict(block or {})
    if box and "box" not in block:
        block["box"] = box
    size, color, font_name = explicit_style(block)
    if size is None and use_box_size:
        size = _box_size_pt(box or block.get("box") or {}, page_hw)
    if color is None:
        color = sample_ink_color(rgb_arr, box or block.get("box") or {}, page_hw)
    if size:
        # Values above 48 are pixels, not points.
        if size > 48:
            ph = float((page_hw or {}).get("h") or (page_hw or {}).get("height") or 0)
            size = size / ph * 792.0 if ph else None
        if size:
            run.font.size = Pt(max(6.0, min(36.0, float(size))))
    if color and re.fullmatch(r"[0-9A-Fa-f]{6}", color):
        run.font.color.rgb = RGBColor(int(color[0:2], 16), int(color[2:4], 16), int(color[4:6], 16))
    if font_name:
        run.font.name = font_name
        rPr = run._element.get_or_add_rPr()
        rFonts = rPr.find(qn("w:rFonts"))
        if rFonts is None:
            from docx.oxml import OxmlElement
            rFonts = OxmlElement("w:rFonts")
            rPr.append(rFonts)
        rFonts.set(qn("w:ascii"), font_name)
        rFonts.set(qn("w:hAnsi"), font_name)
        rFonts.set(qn("w:eastAsia"), font_name)
    return {"size": size, "color": color, "font_name": font_name}
