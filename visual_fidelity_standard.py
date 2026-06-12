#!/usr/bin/env python3
"""
视觉/版式验收标准 — 用可量化指标逼近「人眼看出差很大」的问题。

三层标准：
1. 原 PDF 页图 vs 我们 docx 渲染页图（像不像原件）
2. WPS docx 渲染 vs 我们 docx 渲染（离范本差多少）
3. 版式结构（分页、对齐、字号、段落粒度、图宽）

输出：JSON + 可打印报告；未达阈值 = 不能宣称验收通过。
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
import zipfile
from collections import Counter
from dataclasses import asdict, dataclass, field
from typing import Dict, List, Optional, Tuple

try:
    import cv2
    import numpy as np
except ImportError:
    cv2 = None
    np = None

try:
    import fitz
except ImportError:
    fitz = None

PDF = r"C:\Users\paz\Desktop\1212.pdf"
WPS = r"C:\Users\paz\Desktop\1212.docx"
OURS = r"C:\Users\paz\Desktop\1212_full.docx"
OUT_JSON = os.path.join(os.path.dirname(__file__), "visual_fidelity_report.json")
OUT_MD = r"C:\Users\paz\Desktop\1212验收标准报告.txt"

# 阈值：低于此分视为「人眼仍会看出明显问题」
THRESHOLDS = {
    "pdf_ssim_min": 0.72,       # 我们渲染 vs 原 PDF
    "wps_ssim_min": 0.68,       # 我们渲染 vs WPS 渲染
    "layout_vs_wps_min": 0.70,  # 版式结构相似度
    "text_vs_wps_min": 0.88,    # 去空白字符后的文本重合
    "pages_pass_ratio": 0.75,   # 至少 75% 页达标
}

SECTION_ANCHORS = [
    "CMCCTD-SS-202400146",
    "(签字页)",
    "1.工程概况",
    "2.基坑围护方案简介",
    "供应商负面行为处理规则",
    "60IT硬件",
    "108 电源",
    "第八条本协议",
]


@dataclass
class PageLayout:
    page: int
    text_len: int = 0
    paragraphs: int = 0
    tables: int = 0
    pics: int = 0
    max_img_cx: int = 0
    align: Dict[str, int] = field(default_factory=dict)
    font_sizes: Dict[str, int] = field(default_factory=dict)
    fonts: Dict[str, int] = field(default_factory=dict)
    fullpage_image: bool = False
    preview: str = ""


@dataclass
class PageVisual:
    page: int
    pdf_ssim: Optional[float] = None
    wps_ssim: Optional[float] = None
    pdf_edge_ssim: Optional[float] = None
    wps_edge_ssim: Optional[float] = None
    pdf_hist_corr: Optional[float] = None
    layout_vs_wps: Optional[float] = None
    text_vs_wps: Optional[float] = None
    issues: List[str] = field(default_factory=list)


def _read_doc_xml(path: str) -> str:
    with zipfile.ZipFile(path) as z:
        return z.read("word/document.xml").decode("utf-8", errors="replace")


def _plain_text(doc_xml: str) -> str:
    return "".join(re.findall(r"<w:t[^>]*>([^<]*)</w:t>", doc_xml))


def split_pages(doc_xml: str) -> List[str]:
    parts = doc_xml.split('w:br w:type="page"')
    return parts if len(parts) > 1 else [doc_xml]


def split_text_by_anchors(full_text: str, anchors: List[str], expected: int = 12) -> List[str]:
    """按锚点把纯文本切成逻辑页（与 PDF 12 页对齐）。"""
    points = [0]
    for a in anchors[1:]:
        i = full_text.find(a)
        if i > 0 and i not in points:
            points.append(i)
    points = sorted(set(points))
    segs = []
    for i, start in enumerate(points):
        end = points[i + 1] if i + 1 < len(points) else len(full_text)
        segs.append(full_text[start:end])
    # 锚点不足时按字数均分
    while len(segs) < expected:
        longest_i = max(range(len(segs)), key=lambda i: len(segs[i]))
        s = segs.pop(longest_i)
        mid = len(s) // 2
        segs.insert(longest_i, s[mid:])
        segs.insert(longest_i, s[:mid])
    return segs[:expected]


def wps_text_sections(doc_xml: str, expected: int = 12) -> List[str]:
    return split_text_by_anchors(_plain_text(doc_xml), SECTION_ANCHORS, expected)


def layout_from_text(text: str, page_no: int, pxml: str = "") -> PageLayout:
    """仅有纯文本时也能算基础版式指标。"""
    return PageLayout(
        page=page_no,
        text_len=len(text.strip()),
        paragraphs=text.count("\n") + 1 if text else 0,
        tables=pxml.count("<w:tbl") if pxml else 0,
        pics=pxml.count("<pic:pic") if pxml else 0,
        max_img_cx=max([int(x) for x in re.findall(r'cx="(\d+)"', pxml)], default=0) if pxml else 0,
        preview=text.strip()[:200],
    )


def analyze_page_xml(pxml: str, page_no: int) -> PageLayout:
    texts = re.findall(r"<w:t[^>]*>([^<]*)</w:t>", pxml)
    text = "".join(texts).strip()
    aligns = Counter()
    sizes = Counter()
    fonts = Counter()
    for p in re.findall(r"<w:p[ >][\s\S]*?</w:p>", pxml):
        jc = re.search(r'w:jc w:val="(\w+)"', p)
        if jc:
            aligns[jc.group(1)] += 1
        for r in re.findall(r"<w:r[\s\S]*?</w:r>", p):
            t = "".join(re.findall(r"<w:t[^>]*>([^<]*)</w:t>", r))
            if not t:
                continue
            sz = re.search(r'w:sz w:val="(\d+)"', r)
            if sz:
                sizes[sz.group(1)] += 1
            font = re.search(r'w:eastAsia="([^"]+)"', r) or re.search(r'w:ascii="([^"]+)"', r)
            if font:
                fonts[font.group(1)] += 1
    extents = [int(x) for x in re.findall(r'cx="(\d+)"', pxml)]
    max_cx = max(extents) if extents else 0
    paras = len(re.findall(r"<w:p[ >]", pxml))
    return PageLayout(
        page=page_no,
        text_len=len(text),
        paragraphs=paras,
        tables=pxml.count("<w:tbl"),
        pics=pxml.count("<pic:pic"),
        max_img_cx=max_cx,
        align=dict(aligns),
        font_sizes=dict(sizes),
        fonts=dict(fonts),
        fullpage_image=max_cx > 5_000_000,
        preview=text[:80],
    )


def _norm_text(s: str) -> str:
    return re.sub(r"\s+", "", s)


def text_similarity(a: str, b: str) -> float:
    a, b = _norm_text(a), _norm_text(b)
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    # 最长公共子串比 + bigram Jaccard
    def bigrams(t):
        return {t[i:i + 2] for i in range(len(t) - 1)} if len(t) > 1 else {t}
    ba, bb = bigrams(a), bigrams(b)
    j = len(ba & bb) / max(len(ba | bb), 1)
    lr = min(len(a), len(b)) / max(len(a), len(b))
    # 滑动窗口看 WPS 长段是否包含我们短段
    contain = 0.0
    if len(a) < len(b) and a[:40] in b:
        contain = 0.85
    elif len(b) < len(a) and b[:40] in a:
        contain = 0.85
    return max(contain, 0.5 * j + 0.3 * lr + 0.2 * (1 if a[:20] == b[:20] else 0))


def layout_similarity(our: PageLayout, wps: PageLayout) -> float:
    scores = []
    # 段落粒度（太多碎段 = 版式差）
    if wps.paragraphs and our.paragraphs:
        pr = min(our.paragraphs, wps.paragraphs) / max(our.paragraphs, wps.paragraphs)
        scores.append(pr * 0.2)
    # 对齐分布
    keys = set(our.align) | set(wps.align)
    if keys:
        dist = sum(abs(our.align.get(k, 0) - wps.align.get(k, 0)) for k in keys)
        total = sum(wps.align.values()) or 1
        scores.append(max(0, 1 - dist / total) * 0.25)
    # 表格
    if wps.tables or our.tables:
        scores.append((1.0 if our.tables > 0 else 0.0) * 0.2 if wps.tables else 0.1)
    # 图（整页图扣分）
    if our.fullpage_image and not wps.fullpage_image:
        scores.append(0.0)
    elif our.pics == 0 and wps.pics > 0:
        scores.append(0.3)
    else:
        scores.append(0.15)
    # 文字量
    if wps.text_len or our.text_len:
        scores.append(min(our.text_len, wps.text_len) / max(our.text_len, wps.text_len, 1) * 0.25)
    return min(1.0, sum(scores))


def render_pdf_pages(pdf_path: str, out_dir: str, dpi: int = 120) -> List[str]:
    if not fitz:
        return []
    os.makedirs(out_dir, exist_ok=True)
    paths = []
    doc = fitz.open(pdf_path)
    for i in range(doc.page_count):
        p = os.path.join(out_dir, f"pdf_{i+1:02d}.png")
        doc[i].get_pixmap(dpi=dpi).save(p)
        paths.append(p)
    doc.close()
    return paths


def docx_to_pdf(docx_path: str, out_pdf: str) -> bool:
    for cmd in (
        ["soffice", "--headless", "--convert-to", "pdf", "--outdir", os.path.dirname(out_pdf), docx_path],
        ["libreoffice", "--headless", "--convert-to", "pdf", "--outdir", os.path.dirname(out_pdf), docx_path],
    ):
        if not cmd[0] or (cmd[0] == "soffice" and not _which("soffice")):
            if cmd[0] == "soffice":
                continue
        if cmd[0] == "libreoffice" and not _which("libreoffice"):
            continue
        try:
            subprocess.run(cmd, capture_output=True, timeout=120, check=True)
            base = os.path.splitext(os.path.basename(docx_path))[0] + ".pdf"
            src = os.path.join(os.path.dirname(out_pdf), base)
            if os.path.isfile(src):
                if src != out_pdf:
                    os.replace(src, out_pdf)
                return True
        except Exception:
            continue
    return False


def _which(name: str) -> Optional[str]:
    from shutil import which
    return which(name)


def render_docx_pages(docx_path: str, out_dir: str, dpi: int = 120) -> List[str]:
    if not fitz:
        return []
    pdf = os.path.join(out_dir, "tmp.pdf")
    if not docx_to_pdf(docx_path, pdf):
        return []
    os.makedirs(out_dir, exist_ok=True)
    paths = []
    doc = fitz.open(pdf)
    for i in range(doc.page_count):
        p = os.path.join(out_dir, f"{os.path.basename(docx_path)}_{i+1:02d}.png")
        doc[i].get_pixmap(dpi=dpi).save(p)
        paths.append(p)
    doc.close()
    return paths


def _prep_gray(path: str, size: Tuple[int, int]) -> Optional[np.ndarray]:
    if cv2 is None:
        return None
    img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
    if img is None:
        return None
    return cv2.resize(img, size, interpolation=cv2.INTER_AREA)


def ssim(a: np.ndarray, b: np.ndarray) -> float:
    """简化 SSIM（不依赖 skimage）。"""
    a = a.astype(np.float64)
    b = b.astype(np.float64)
    c1, c2 = (0.01 * 255) ** 2, (0.03 * 255) ** 2
    mu_a, mu_b = a.mean(), b.mean()
    sig_a, sig_b = a.var(), b.var()
    sig_ab = ((a - mu_a) * (b - mu_b)).mean()
    num = (2 * mu_a * mu_b + c1) * (2 * sig_ab + c2)
    den = (mu_a ** 2 + mu_b ** 2 + c1) * (sig_a + sig_b + c2)
    return float(max(0, min(1, num / den)))


def hist_corr(a: np.ndarray, b: np.ndarray) -> float:
    ha = cv2.calcHist([a], [0], None, [64], [0, 256])
    hb = cv2.calcHist([b], [0], None, [64], [0, 256])
    cv2.normalize(ha, ha)
    cv2.normalize(hb, hb)
    return float(max(0, cv2.compareHist(ha, hb, cv2.HISTCMP_CORREL)))


def compare_images(path_a: str, path_b: str) -> Tuple[Optional[float], Optional[float], Optional[float]]:
    """返回 (像素 SSIM, 直方图相关, 边缘结构 SSIM)。"""
    if not cv2 or not os.path.isfile(path_a) or not os.path.isfile(path_b):
        return None, None, None
    a = cv2.imread(path_a, cv2.IMREAD_GRAYSCALE)
    b = cv2.imread(path_b, cv2.IMREAD_GRAYSCALE)
    if a is None or b is None:
        return None, None, None
    h, w = min(a.shape[0], b.shape[0]), min(a.shape[1], b.shape[1])
    a = cv2.resize(a, (w, h))
    b = cv2.resize(b, (w, h))
    px = ssim(a, b)
    hc = hist_corr(a, b)
    ea = cv2.Canny(a, 50, 150)
    eb = cv2.Canny(b, 50, 150)
    edge = ssim(ea, eb)
    return px, hc, edge


def evaluate_page(
    page_no: int,
    our_layout: PageLayout,
    wps_layout: Optional[PageLayout],
    pdf_img: Optional[str],
    our_img: Optional[str],
    wps_img: Optional[str],
) -> PageVisual:
    pv = PageVisual(page=page_no)
    if wps_layout:
        pv.layout_vs_wps = layout_similarity(our_layout, wps_layout)
        pv.text_vs_wps = text_similarity(our_layout.preview, wps_layout.preview)
        if pv.layout_vs_wps < THRESHOLDS["layout_vs_wps_min"]:
            pv.issues.append("版式结构偏离 WPS")
        if pv.text_vs_wps < THRESHOLDS["text_vs_wps_min"]:
            pv.issues.append(f"本页文字与 WPS 重合低({pv.text_vs_wps:.2f})")
    if our_layout.fullpage_image:
        pv.issues.append("含整页大图")
    if our_layout.text_len < 30 and our_layout.tables == 0 and our_layout.pics <= 1:
        pv.issues.append("几乎无内容")
    if pdf_img and our_img:
        pv.pdf_ssim, pv.pdf_hist_corr, pv.pdf_edge_ssim = compare_images(pdf_img, our_img)
        vis_score = max(pv.pdf_ssim or 0, pv.pdf_edge_ssim or 0)
        if vis_score < THRESHOLDS["pdf_ssim_min"]:
            pv.issues.append(f"渲染图与原 PDF 差异大(结构{pv.pdf_edge_ssim:.2f}/像素{pv.pdf_ssim:.2f})")
    if wps_img and our_img:
        pv.wps_ssim, _, pv.wps_edge_ssim = compare_images(wps_img, our_img)
        vis_w = max(pv.wps_ssim or 0, pv.wps_edge_ssim or 0)
        if vis_w < THRESHOLDS["wps_ssim_min"]:
            pv.issues.append(f"渲染图与 WPS 差异大(结构{pv.wps_edge_ssim:.2f}/像素{pv.wps_ssim:.2f})")
    return pv


def run(pdf=PDF, wps=WPS, ours=OURS) -> dict:
    wxml = _read_doc_xml(wps)
    oxml = _read_doc_xml(ours)
    opages = split_pages(oxml)
    n = max(len(opages), 12)
    w_text_secs = wps_text_sections(wxml, n)
    o_texts = [_plain_text(opages[i] if i < len(opages) else "") for i in range(n)]

    w_layouts = [layout_from_text(w_text_secs[i] if i < len(w_text_secs) else "", i + 1) for i in range(n)]
    o_layouts = [analyze_page_xml(opages[i] if i < len(opages) else "", i + 1) for i in range(n)]
    for i in range(n):
        o_layouts[i].preview = o_texts[i][:200] if o_texts[i] else o_layouts[i].preview
        w_layouts[i].preview = w_text_secs[i][:200] if i < len(w_text_secs) else ""

    visual_pages: List[PageVisual] = []
    can_render = bool(fitz and cv2)

    with tempfile.TemporaryDirectory(prefix="vfid_") as tmp:
        pdf_imgs = render_pdf_pages(pdf, os.path.join(tmp, "pdf")) if can_render else []
        our_imgs = render_docx_pages(ours, os.path.join(tmp, "our")) if can_render else []
        wps_imgs = render_docx_pages(wps, os.path.join(tmp, "wps")) if can_render else []

        for i in range(n):
            visual_pages.append(
                evaluate_page(
                    i + 1,
                    o_layouts[i],
                    w_layouts[i] if i < len(w_layouts) else None,
                    pdf_imgs[i] if i < len(pdf_imgs) else None,
                    our_imgs[i] if i < len(our_imgs) else None,
                    wps_imgs[min(i, len(wps_imgs) - 1)] if wps_imgs else None,
                )
            )

    def page_pass(p: PageVisual) -> bool:
        hard = [x for x in p.issues if "整页大图" in x or "几乎无内容" in x]
        if hard:
            return False
        pdf_vis = max(p.pdf_ssim or 0, p.pdf_edge_ssim or 0)
        wps_vis = max(p.wps_ssim or 0, p.wps_edge_ssim or 0)
        if p.pdf_ssim is not None and pdf_vis < THRESHOLDS["pdf_ssim_min"]:
            return False
        if p.wps_ssim is not None and wps_vis < THRESHOLDS["wps_ssim_min"]:
            return False
        if (p.layout_vs_wps or 0) < THRESHOLDS["layout_vs_wps_min"]:
            return False
        return True

    passed = sum(1 for p in visual_pages if page_pass(p))
    report = {
        "thresholds": THRESHOLDS,
        "render_available": can_render and bool(our_imgs),
        "docx_render_note": "无 LibreOffice 时仅版式/文本层评分",
        "pages": [asdict(p) for p in visual_pages],
        "our_layouts": [asdict(x) for x in o_layouts],
        "wps_layouts": [asdict(x) for x in w_layouts],
        "summary": {
            "total_pages": n,
            "pages_with_issues": sum(1 for p in visual_pages if p.issues),
            "pass_ratio": round(passed / n, 3),
            "verdict": "未通过" if passed / n < THRESHOLDS["pages_pass_ratio"] else "部分通过",
        },
    }
    return report


def format_report(report: dict) -> str:
    lines = [
        "1212 视觉/版式验收标准 — 自动评估报告",
        "=" * 50,
        f"渲染对比可用: {report['render_available']}",
        f"总体判定: {report['summary']['verdict']}（达标页比例 {report['summary']['pass_ratio']:.0%}）",
        f"有问题页数: {report['summary']['pages_with_issues']}/{report['summary']['total_pages']}",
        "",
        "阈值（低于此 = 人眼仍会觉得差）:",
    ]
    for k, v in report["thresholds"].items():
        lines.append(f"  {k}: {v}")
    lines.append("")
    lines.append("逐页明细:")
    for p in report["pages"]:
        lines.append(
            f"  第{p['page']:2d}页 | pdf_ssim={p.get('pdf_ssim')} wps_ssim={p.get('wps_ssim')} "
            f"layout={p.get('layout_vs_wps')} text={p.get('text_vs_wps')}"
        )
        if p["issues"]:
            lines.append(f"         问题: {', '.join(p['issues'])}")
    lines.append("")
    lines.append("说明: 此前仅用字数/关键词判断会高估质量；本报告以渲染相似度+版式结构为准。")
    return "\n".join(lines)


def main():
    for p in (PDF, WPS, OURS):
        if not os.path.isfile(p):
            print("missing", p)
            return 1
    report = run()
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    text = format_report(report)
    with open(OUT_MD, "w", encoding="utf-8") as f:
        f.write(text)
    print(text)
    print("\njson:", OUT_JSON)
    print("txt:", OUT_MD)
    return 0 if report["summary"]["verdict"] != "未通过" else 1


if __name__ == "__main__":
    raise SystemExit(main())