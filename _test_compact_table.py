#!/usr/bin/env python3
"""Quick local test: compact 54-row table fits one landscape section."""
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "server", "backend"))
from docx import Document
from volc_ocr import _init_doc_landscape, _add_html_table, _single_page_table_opts

html = "<table><tr>" + "".join(f"<td>c{j}</td>" for j in range(7)) + "</tr>" * 54
html = "<table>" + "".join(
    "<tr>" + "".join(f"<td>{i}-{j}</td>" for j in range(7)) + "</tr>"
    for i in range(54)
) + "</table>"

out = os.path.join(tempfile.gettempdir(), "compact_table_test.docx")
doc = Document()
_init_doc_landscape(doc)
doc.add_paragraph("CMCCTD-SS-202400146")
opts = _single_page_table_opts(1, True)
_add_html_table(doc, html, **opts)
doc.save(out)
print("saved", out, "sections", len(doc.sections))