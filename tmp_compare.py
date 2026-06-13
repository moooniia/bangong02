from docx import Document
from docx.oxml.ns import qn

def analyze(path, label):
    doc = Document(path)
    print("\n=== " + label + " ===")
    sec = doc.sections[0]
    print("Page: %.3f x %.3f  L=%.3f R=%.3f" % (sec.page_width.inches, sec.page_height.inches, sec.left_margin.inches, sec.right_margin.inches))
    for ti, table in enumerate(doc.tables):
        nrows = len(table.rows)
        ncols = len(table.columns)
        col_ws = []
        for col in table.columns:
            try:
                col_ws.append(round(col.width / 914400, 3))
            except Exception:
                col_ws.append(0)
        print("Table %d: %dr x %dc  cols(in)=%s" % (ti, nrows, ncols, col_ws))
        for ri, row in enumerate(table.rows):
            trPr_el = row._tr.find(qn("w:trPr"))
            rh = None
            if trPr_el is not None:
                trH = trPr_el.find(qn("w:trHeight"))
                if trH is not None:
                    rh = trH.get(qn("w:val"))
            rh_in = round(int(rh) / 1440, 3) if rh else None
            print("  row[%d]: h=%sin" % (ri, rh_in))

analyze(r"C:\Users\paz\Downloads\47724472-94d6-4225-bfef-49b250f7810d.docx", "PREV v0.10.27")
analyze(r"C:\Users\paz\Downloads\p4_v0.10.30.docx", "NEW  v0.10.30")
