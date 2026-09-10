# Move the shared tool-page <style> into common.css and strip duplicates from HTML.
# Page-unique rules stay in each file. Appearance is preserved.
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COMMON = os.path.join(ROOT, "assets", "common.css")
MARKER = "/* ---- shared tool page chrome (do not duplicate in HTML) ---- */"
TEMPLATE = "image-compress.html"


def extract_style(html):
    m = re.search(r"<style>(.*?)</style>", html, re.S | re.I)
    return (m.group(1) if m else ""), (m.start() if m else None), (m.end() if m else None)


def parse_rules(css):
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    rules = []
    i = 0
    n = len(css)
    while True:
        while i < n and css[i].isspace():
            i += 1
        if i >= n:
            break
        if css.startswith("@", i):
            start = i
            brace = css.find("{", i)
            if brace < 0:
                break
            depth = 0
            j = brace
            while j < n:
                if css[j] == "{":
                    depth += 1
                elif css[j] == "}":
                    depth -= 1
                    if depth == 0:
                        j += 1
                        break
                j += 1
            rules.append(("AT:" + re.sub(r"\s+", " ", css[start:j].strip()), css[start:j].strip()))
            i = j
            continue
        brace = css.find("{", i)
        if brace < 0:
            break
        sel = re.sub(r"\s+", "", css[i:brace].strip())
        depth = 0
        j = brace
        while j < n:
            if css[j] == "{":
                depth += 1
            elif css[j] == "}":
                depth -= 1
                if depth == 0:
                    j += 1
                    break
            j += 1
        body = re.sub(r"\s+", "", css[brace + 1 : j - 1])
        rules.append((sel + "{" + body + "}", css[i:j].strip()))
        i = j
    return rules


def split_top_rules(css):
    """Return list of raw top-level rule strings (pretty, original-ish)."""
    rules = []
    i = 0
    n = len(css)
    while True:
        while i < n and css[i].isspace():
            i += 1
        if i >= n:
            break
        start = i
        if css.startswith("@", i):
            brace = css.find("{", i)
            depth = 0
            j = brace
            while j < n:
                if css[j] == "{":
                    depth += 1
                elif css[j] == "}":
                    depth -= 1
                    if depth == 0:
                        j += 1
                        break
                j += 1
            rules.append(css[start:j].strip())
            i = j
            continue
        brace = css.find("{", i)
        if brace < 0:
            break
        depth = 0
        j = brace
        while j < n:
            if css[j] == "{":
                depth += 1
            elif css[j] == "}":
                depth -= 1
                if depth == 0:
                    j += 1
                    break
            j += 1
        rules.append(css[start:j].strip())
        i = j
    return rules


def rule_key(raw):
    raw = re.sub(r"/\*.*?\*/", "", raw, flags=re.S)
    if raw.lstrip().startswith("@"):
        return "AT:" + re.sub(r"\s+", " ", raw.strip())
    brace = raw.find("{")
    if brace < 0:
        return re.sub(r"\s+", "", raw)
    sel = re.sub(r"\s+", "", raw[:brace].strip())
    body = re.sub(r"\s+", "", raw[brace + 1 : raw.rfind("}")])
    return sel + "{" + body + "}"


def main():
    tmpl_html = open(os.path.join(ROOT, TEMPLATE), encoding="utf-8").read()
    tmpl_css, _, _ = extract_style(tmpl_html)
    shared_keys = {rule_key(r) for r in split_top_rules(tmpl_css)}

    common = open(COMMON, encoding="utf-8").read()
    if MARKER not in common:
        block = "\n\n" + MARKER + "\n" + tmpl_css.strip() + "\n"
        open(COMMON, "w", encoding="utf-8", newline="\n").write(common.rstrip() + block)
        print("appended shared CSS to common.css", "rules", len(shared_keys))
    else:
        print("common.css already has shared block")

    changed = 0
    for dirpath, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in ("downloads", "assets")]
        for fn in files:
            if not fn.endswith(".html"):
                continue
            path = os.path.join(dirpath, fn)
            rel = os.path.relpath(path, ROOT)
            if "map-coord-tool" in rel.replace("\\", "/"):
                continue
            html = open(path, encoding="utf-8").read()
            if 'href="/assets/common.css"' not in html and "href='/assets/common.css'" not in html:
                continue
            css, a, b = extract_style(html)
            if not css:
                continue
            kept = []
            removed = 0
            for raw in split_top_rules(css):
                if rule_key(raw) in shared_keys:
                    removed += 1
                else:
                    kept.append(raw)
            if removed == 0:
                continue
            if kept:
                new_style = "<style>\n" + "\n".join(kept) + "\n</style>"
            else:
                new_style = ""
            html2 = html[:a] + new_style + html[b:]
            html2 = re.sub(r"\n{3,}", "\n\n", html2)
            open(path, "w", encoding="utf-8", newline="\n").write(html2)
            changed += 1
            print("stripped", rel, "removed", removed, "kept", len(kept))
    print("files updated", changed)


if __name__ == "__main__":
    main()
