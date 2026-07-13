from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont


OUT = Path(__file__).with_name("invoice-toolbox-showcase.jpg")
W, H = 2200, 1240


def font(size, bold=False):
    candidates = [
        r"C:\Windows\Fonts\msyhbd.ttc" if bold else r"C:\Windows\Fonts\msyh.ttc",
        r"C:\Windows\Fonts\simhei.ttf",
        r"C:\Windows\Fonts\arial.ttf",
    ]
    for path in candidates:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def rr(draw, box, radius, fill, outline=None, width=1):
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def text(draw, xy, value, size=22, fill="#111827", bold=False, anchor=None):
    draw.text(xy, value, font=font(size, bold), fill=fill, anchor=anchor)


def shadow(base, box, radius=28, blur=28, alpha=40):
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    d.rounded_rectangle(box, radius=radius, fill=(15, 23, 42, alpha))
    layer = layer.filter(ImageFilter.GaussianBlur(blur))
    base.alpha_composite(layer)


def draw_logo(draw, x, y, size=34):
    rr(draw, (x, y, x + size, y + size), 9, "#ec4b8b")
    pad = size * 0.28
    draw.rounded_rectangle((x + pad, y + pad * 0.8, x + size - pad, y + size - pad * 0.7), radius=3, fill="white")
    for i in range(3):
        yy = y + pad * 1.25 + i * size * 0.16
        draw.line((x + pad * 1.35, yy, x + size - pad * 1.3, yy), fill="#ec4b8b", width=2)


def main():
    img = Image.new("RGBA", (W, H), "#f8fafc")
    d = ImageDraw.Draw(img)
    # soft page background
    for i in range(90):
        alpha = int(70 * (1 - i / 90))
        d.ellipse((150 - i * 8, -160 - i * 5, 760 + i * 10, 410 + i * 8), fill=(236, 72, 153, max(alpha, 0)))
    for i in range(110):
        alpha = int(42 * (1 - i / 110))
        d.ellipse((1450 - i * 7, 40 - i * 5, 2320 + i * 7, 760 + i * 6), fill=(29, 78, 216, max(alpha, 0)))

    window = (64, 52, W - 64, H - 66)
    shadow(img, window, 34, 34, 44)
    rr(d, window, 34, "#ffffff", "#e5e7eb", 2)
    x0, y0, x1, y1 = window
    d.rounded_rectangle((x0, y0, x1, y0 + 72), radius=34, fill="#ffffff")
    d.rectangle((x0, y0 + 38, x1, y0 + 72), fill="#ffffff")
    d.line((x0, y0 + 72, x1, y0 + 72), fill="#eef0f4", width=2)
    draw_logo(d, x0 + 28, y0 + 20, 34)
    text(d, (x0 + 78, y0 + 23), "发票", 24, "#111827", True)
    text(d, (x0 + 132, y0 + 23), "工具箱", 24, "#ec4b8b", True)
    text(d, (x0 + 222, y0 + 28), "批量识别 · 归档 · 核对", 17, "#8b95a5")
    for i, c in enumerate(("#111827", "#9ca3af", "#9ca3af")):
        d.line((x1 - 150 + i * 48, y0 + 35, x1 - 132 + i * 48, y0 + 35), fill=c, width=3)

    # left panel
    left = (x0 + 18, y0 + 96, x0 + 278, y1 - 26)
    rr(d, left, 20, "#ffffff", "#e9edf3", 1)
    text(d, (left[0] + 22, left[1] + 28), "文件夹", 20, "#111827", True)
    for idx, (label, sub, icon) in enumerate([
        ("选择发票文件夹", "C:/Users/paz/Desktop/111", "□"),
        ("选择归档文件夹", "C:/Users/paz/Desktop/111/222", "□"),
    ]):
        y = left[1] + 72 + idx * 78
        rr(d, (left[0] + 18, y, left[2] - 18, y + 62), 12, "#fbfcff", "#e5e7eb")
        text(d, (left[0] + 38, y + 16), icon, 19, "#ec4b8b")
        text(d, (left[0] + 66, y + 13), label, 16, "#1f2937", True)
        text(d, (left[0] + 66, y + 37), sub, 13, "#7a8495")
    stats_y = left[1] + 250
    rr(d, (left[0] + 18, stats_y, left[2] - 18, stats_y + 210), 16, "#ffffff", "#e5e7eb")
    text(d, (left[0] + 40, stats_y + 24), "统计信息", 18, "#1f2937", True)
    stats = [("总文件", "160", "#111827"), ("待确认", "3", "#ec4b8b"), ("已确认", "157", "#111827"), ("重复跳过", "13", "#111827"), ("已识别金额", "¥46,255.37", "#111827")]
    for i, (a, b, c) in enumerate(stats):
        yy = stats_y + 62 + i * 27
        text(d, (left[0] + 40, yy), a, 14, "#6b7280")
        text(d, (left[2] - 40, yy), b, 17, c, True, "ra")
    rr(d, (left[0] + 18, y1 - 156, left[2] - 18, y1 - 106), 13, "#ec4b8b")
    text(d, ((left[0] + left[2]) / 2, y1 - 141), "开始识别", 17, "white", True, "ma")
    rr(d, (left[0] + 18, y1 - 92, left[2] - 18, y1 - 46), 12, "#ffffff", "#e5e7eb")
    text(d, ((left[0] + left[2]) / 2, y1 - 79), "重新开始", 16, "#111827", False, "ma")

    # center table
    main = (left[2] + 24, y0 + 96, x1 - 620, y1 - 26)
    text(d, (main[0], main[1] + 4), "发票列表", 28, "#111827", True)
    text(d, (main[0] + 138, main[1] + 13), "共 160 张发票，3 张需要人工核对", 16, "#7b8494")
    for i, label in enumerate(["仅看待确认 3", "收起核对", "导出"]):
        w = 126 if i < 2 else 82
        bx = main[2] - 350 + i * 132
        fill = "#ec4b8b" if label == "导出" else "#ffffff"
        fg = "#ffffff" if label == "导出" else "#1f2937"
        rr(d, (bx, main[1] - 4, bx + w, main[1] + 38), 10, fill, "#e5e7eb")
        text(d, (bx + w / 2, main[1] + 8), label, 15, fg, True, "ma")
    table_y = main[1] + 62
    rr(d, (main[0], table_y, main[2], table_y + 56), 12, "#252b36")
    headers = ["公司抬头", "购买方税号", "销售方", "销售方税号", "开票日期", "价税合计", "税率", "审核状态"]
    colw = [210, 190, 230, 190, 120, 120, 78, 110]
    x = main[0]
    for h, cw in zip(headers, colw):
        text(d, (x + cw / 2, table_y + 18), h, 15, "white", True, "ma")
        d.line((x + cw, table_y + 10, x + cw, table_y + 46), fill="#414957")
        x += cw
    rows = [
        ("江西省勘察设计研究院上海分院", "913101097590284041", "上海浦东华海加油站有限公司", "91310115133504376H", "2022-09-28", "¥255.50", "13%", "已确认", False),
        ("江西省勘察设计研究院有限公司", "91360000158286715E", "上海三快智送科技有限公司", "91310000MA1FW9A80N", "2026-03-02", "¥11.00", "6%", "已确认", False),
        ("上海洪君基础工程中心", "91310230MA1K1Y021L", "中国石化销售股份有限公司上海分公司", "9131000834486035U", "2026-02-11", "¥186.78", "13%", "待确认", True),
        ("昆山东东方臻贸易有限公司个人", "", "昆山东东方臻贸易有限公司", "91320583MA1XQL286M", "2026-01-08", "¥446.20", "13%", "待确认", True),
    ]
    more = [
        ("江西省勘察设计研究院上海分院", "913101097590284041", "北京京东世纪信息技术有限公司", "91110302562134916R", "2023-03-08", "¥1218.98", "13%", "已确认", False),
        ("江西省勘察设计研究院上海分院", "913101097590284041", "中国电信股份有限公司上海分公司", "91310115671143758E", "2026-01-20", "¥147.00", "免税", "已确认", False),
        ("江西省勘察设计研究院有限公司", "91360000158286715E", "上海市普陀区涌敏餐厅", "92310107MA1KJ0Q9X4", "2026-04-17", "¥151.70", "1%", "待确认", True),
        ("江西省勘察设计研究院上海分院", "913101097590284041", "芜湖慧迈贸易有限公司", "91340207MA8PEYGF80", "2026-01-16", "¥29.90", "13%", "已确认", False),
    ]
    data = (rows + more) * 2
    for r, row in enumerate(data[:16]):
        y = table_y + 56 + r * 48
        bg = "#fff0f5" if row[-1] else ("#ffffff" if r % 2 else "#f8fafc")
        d.rectangle((main[0], y, main[2], y + 48), fill=bg)
        d.line((main[0], y + 48, main[2], y + 48), fill="#e5e7eb")
        x = main[0]
        colors = ["#0f766e", "#4d7c0f", "#1d4ed8", "#a16207", "#334155", "#047857", "#b45309", "#16a34a"]
        for c, val in enumerate(row[:-1]):
            s = str(val)
            if len(s) > 15:
                s = s[:14] + "..."
            fill = "#db1754" if row[-1] else colors[min(c, len(colors) - 1)]
            text(d, (x + colw[c] / 2, y + 15), s, 14, fill, row[-1], "ma")
            d.line((x + colw[c], y + 8, x + colw[c], y + 40), fill="#e1e5ec")
            x += colw[c]

    # review panel
    review = (main[2] + 22, y0 + 96, x1 - 18, y1 - 26)
    rr(d, review, 18, "#ffffff", "#e5e7eb")
    text(d, (review[0] + 28, review[1] + 28), "人工核对", 29, "#111827", True)
    text(d, (review[0] + 28, review[1] + 68), "发票号码：2631700000289177353    开票日期：2026-01-20", 15, "#667085")
    pv = (review[0] + 28, review[1] + 100, review[2] - 28, review[1] + 520)
    rr(d, pv, 14, "#f5f6f8", "#e5e7eb")
    for i, label in enumerate(["−", "+", "原大小", "适应窗口", "↶", "↷"]):
        bx = pv[0] + 18 + i * 70
        bw = 44 if i < 2 or i > 3 else 74
        rr(d, (bx, pv[1] + 16, bx + bw, pv[1] + 52), 8, "#ffffff", "#e5e7eb")
        text(d, (bx + bw / 2, pv[1] + 25), label, 15, "#111827", False, "ma")
    inv = (pv[0] + 42, pv[1] + 78, pv[2] - 42, pv[3] - 34)
    rr(d, inv, 6, "#fffdf9", "#f1d4c8")
    text(d, (inv[0] + 260, inv[1] + 36), "电子发票（普通发票）", 29, "#b7432e", True, "ma")
    d.ellipse((inv[0] + 320, inv[1] + 8, inv[0] + 470, inv[1] + 84), outline="#ef4444", width=5)
    d.rectangle((inv[0] + 24, inv[1] + 104, inv[2] - 24, inv[1] + 210), outline="#d8a59a", width=2)
    d.rectangle((inv[0] + 24, inv[1] + 210, inv[2] - 24, inv[3] - 42), outline="#d8a59a", width=2)
    for i in range(6):
        d.line((inv[0] + 24 + i * 92, inv[1] + 210, inv[0] + 24 + i * 92, inv[3] - 42), fill="#ebc6bc")
    text(d, (inv[0] + 52, inv[1] + 128), "名称：江西省勘察设计研究院上海分院", 17, "#8a473d")
    text(d, (inv[0] + 52, inv[1] + 160), "税号：913101097590284041", 17, "#8a473d")
    text(d, (inv[0] + 52, inv[3] - 80), "销售方：上海某科技有限公司", 17, "#8a473d")
    inv_blur = img.crop(inv).filter(ImageFilter.GaussianBlur(0.35))
    img.paste(inv_blur, inv)
    form_y = pv[3] + 34
    labels = ["发票号码", "购买方税号", "开票日期", "价税合计", "销售方名称", "销售方税号", "购买方名称", "税额"]
    vals = ["2631700000289177353", "913101097590284041", "2026-01-20", "147.00", "中国电信股份有限公司上海分公司", "91310115671143758E", "江西省勘察设计研究院上海分院", "147.00"]
    for i, (lab, val) in enumerate(zip(labels, vals)):
        cx = review[0] + 28 + (i % 2) * 260
        cy = form_y + (i // 2) * 76
        text(d, (cx, cy), lab, 14, "#667085")
        rr(d, (cx, cy + 24, cx + 238, cy + 62), 8, "#ffffff", "#e5e7eb")
        text(d, (cx + 12, cy + 34), val[:18], 14, "#111827")
    rr(d, (review[2] - 142, review[3] - 62, review[2] - 28, review[3] - 18), 10, "#ec4b8b")
    text(d, (review[2] - 85, review[3] - 50), "保存", 16, "white", True, "ma")

    # dark mode preview chip
    chip = (260, H - 240, 875, H - 70)
    shadow(img, chip, 22, 26, 58)
    rr(d, chip, 20, "#111827", "#273244")
    text(d, (chip[0] + 24, chip[1] + 22), "深色模式预览", 18, "#ffffff", True)
    rr(d, (chip[0] + 186, chip[1] + 20, chip[0] + 232, chip[1] + 44), 12, "#ec4b8b")
    d.ellipse((chip[0] + 207, chip[1] + 24, chip[0] + 227, chip[1] + 40), fill="#ffffff")
    for i, val in enumerate(["总览", "待处理", "已归档", "供应商"]):
        yy = chip[1] + 68 + i * 24
        fill = "#ec4b8b" if i == 0 else "#94a3b8"
        text(d, (chip[0] + 28, yy), val, 13, fill, i == 0)
    rr(d, (chip[0] + 170, chip[1] + 66, chip[2] - 26, chip[3] - 20), 12, "#1f2937", "#334155")
    text(d, (chip[0] + 194, chip[1] + 86), "发票总览", 15, "#ffffff", True)
    for i in range(4):
        y = chip[1] + 116 + i * 26
        d.line((chip[0] + 194, y, chip[2] - 48, y), fill="#334155")
        text(d, (chip[0] + 204, y + 6), f"2631700000{i+1}", 11, "#93c5fd")
        text(d, (chip[0] + 330, y + 6), "已审核", 11, "#34d399")
        text(d, (chip[0] + 430, y + 6), "¥147.00", 11, "#facc15")

    img = img.convert("RGB")
    img.save(OUT, quality=92, optimize=True)
    print(OUT)


if __name__ == "__main__":
    main()
