from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "assets" / "icons"
WINUI_ASSETS = ROOT / "winui_app" / "Assets"
PNG_PATH = OUT_DIR / "invoice-toolbox-icon-256.png"
ICO_PATH = OUT_DIR / "invoice-toolbox.ico"
SIZES = [16, 20, 24, 30, 32, 36, 40, 44, 48, 64, 96, 128, 256]
TASKBAR_SIZES = [16, 20, 24, 30, 32, 36, 40, 44, 48, 64, 96, 256]


def rounded_rectangle(draw: ImageDraw.ImageDraw, xy, radius, fill):
    draw.rounded_rectangle(xy, radius=radius, fill=fill)


def make_icon(size: int) -> Image.Image:
    # Draw on a supersampled canvas so taskbar-scale assets do not look like
    # nearest-neighbor miniatures.
    canvas = 1024
    scale = canvas / 256
    image = Image.new("RGBA", (canvas, canvas), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    # Soft ambient shadow, visible at larger sizes and harmless after downscale.
    shadow = Image.new("RGBA", (canvas, canvas), (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(shadow)
    rounded_rectangle(shadow_draw, [4 * scale, 7 * scale, 252 * scale, 255 * scale], 58 * scale, (92, 18, 54, 62))
    shadow = shadow.filter(ImageFilter.GaussianBlur(round(9 * scale)))
    image.alpha_composite(shadow)

    # Pink rounded app body with a small highlight so it reads less flat in the
    # Windows taskbar.
    body = Image.new("RGBA", (canvas, canvas), (0, 0, 0, 0))
    body_draw = ImageDraw.Draw(body)
    rounded_rectangle(body_draw, [1 * scale, 1 * scale, 255 * scale, 255 * scale], 58 * scale, (233, 65, 135, 255))
    for y in range(round(1 * scale), round(255 * scale)):
        t = (y - 1 * scale) / (254 * scale)
        color = (
            round(247 - 20 * t),
            round(86 - 22 * t),
            round(153 - 18 * t),
            255,
        )
        body_draw.line([(1 * scale, y), (255 * scale, y)], fill=color, width=1)
    mask = Image.new("L", (canvas, canvas), 0)
    mask_draw = ImageDraw.Draw(mask)
    rounded_rectangle(mask_draw, [1 * scale, 1 * scale, 255 * scale, 255 * scale], 58 * scale, 255)
    image = Image.composite(body, image, mask)

    # Receipt shadow and paper.
    paper_shadow = Image.new("RGBA", (canvas, canvas), (0, 0, 0, 0))
    paper_shadow_draw = ImageDraw.Draw(paper_shadow)
    paper_shadow_draw.polygon(receipt_polygon(scale, offset=(0, 8 * scale)), fill=(125, 24, 74, 58))
    paper_shadow = paper_shadow.filter(ImageFilter.GaussianBlur(round(3.5 * scale)))
    image.alpha_composite(paper_shadow)
    draw = ImageDraw.Draw(image)
    draw.polygon(receipt_polygon(scale), fill=(255, 255, 255, 255))

    # Subtle folded corner.
    draw.polygon([(176 * scale, 58 * scale), (198 * scale, 80 * scale), (176 * scale, 80 * scale)], fill=(255, 220, 235, 255))

    # Text strokes with rounded ends.
    line_color = (231, 64, 132, 255)
    for y, x2 in [(92, 162), (124, 184), (156, 152)]:
        draw.rounded_rectangle(
            [82 * scale, y * scale, x2 * scale, (y + 10) * scale],
            radius=5 * scale,
            fill=line_color,
        )

    # Downscale with high-quality filtering.
    return image.resize((size, size), Image.Resampling.LANCZOS)


def receipt_polygon(scale: float, offset=(0, 0)):
    ox, oy = offset
    points = [
        (66, 54),
        (176, 54),
        (198, 76),
        (198, 206),
        (179, 195),
        (162, 206),
        (145, 195),
        (128, 206),
        (111, 195),
        (94, 206),
        (74, 196),
        (74, 76),
    ]
    return [(x * scale + ox, y * scale + oy) for x, y in points]


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    WINUI_ASSETS.mkdir(parents=True, exist_ok=True)
    icons = [make_icon(size) for size in SIZES]
    make_icon(256).save(PNG_PATH)
    icons[-1].save(ICO_PATH, sizes=[(size, size) for size in SIZES], append_images=icons[:-1])
    make_icon(256).save(WINUI_ASSETS / "invoice-toolbox-icon-256.png")
    make_icon(256).save(WINUI_ASSETS / "StoreLogo.png")
    make_icon(44).save(WINUI_ASSETS / "Square44x44Logo.png")
    make_icon(150).save(WINUI_ASSETS / "Square150x150Logo.png")
    make_icon(71).save(WINUI_ASSETS / "SmallTile.png")
    make_icon(310).save(WINUI_ASSETS / "Square310x310Logo.png")
    make_icon(256).save(WINUI_ASSETS / "InvoiceToolbox.ico", sizes=[(size, size) for size in SIZES], append_images=icons[:-1])
    for size in TASKBAR_SIZES:
        icon = make_icon(size)
        icon.save(WINUI_ASSETS / f"Square44x44Logo.targetsize-{size}.png")
        icon.save(WINUI_ASSETS / f"Square44x44Logo.targetsize-{size}_altform-unplated.png")
    print(f"wrote {PNG_PATH}")
    print(f"wrote {ICO_PATH}")


if __name__ == "__main__":
    main()
