#!/usr/bin/env python3
"""Quick local test: compact 54-row table fits one landscape section."""
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "server", "backend"))
from docx import Document
from volc_ocr import _sync_doc_section_to_pdf, _add_html_table, _single_page_table_opts

html = "<table><tr>" + "".join(f"<td>c{j}</td>" for j in range(7)) + "</tr>" * 54
html = "<table>" + "".join(
    "<tr>" + "".join(f"<td>{i}-{j}</td>" for j in range(7)) + "</tr>"
    for i in range(54)
) + "</table>"

out = os.path.join(tempfile.gettempdir(), "compact_table_test.docx")
doc = Document()
pdf = r"C:\Users\paz\Desktop\P T W 测试\page_6.pdf"
_sync_doc_section_to_pdf(doc, pdf, 0, tight=True)
doc.add_paragraph("CMCCTD-SS-202400146")
opts = _single_page_table_opts(1, True)
_add_html_table(doc, html, **opts)
doc.save(out)
print("saved", out, "sections", len(doc.sections))