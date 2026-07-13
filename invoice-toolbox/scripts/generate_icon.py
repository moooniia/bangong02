from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "assets" / "icons"
WINUI_ASSETS = ROOT / "winui_app" / "Assets"
PNG_PATH = OUT_DIR / "invoice-toolbox-icon-256.png"
ICO_PATH = OUT_DIR / "invoice-toolbox.ico"
SIZES = [16, 24, 32, 48, 64, 128, 256]
TASKBAR_SIZES = [16, 24, 32, 44, 48, 64, 256]


def rounded_rectangle(draw: ImageDraw.ImageDraw, xy, radius, fill):
    draw.rounded_rectangle(xy, radius=radius, fill=fill)


def make_icon(size: int) -> Image.Image:
    scale = size / 256
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    # Keep generous transparent padding so Windows taskbar selection does not
    # read as a solid square app icon.
    bg = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    bg_draw = ImageDraw.Draw(bg)
    rounded_rectangle(bg_draw, [46 * scale, 38 * scale, 210 * scale, 218 * scale], 38 * scale, (233, 76, 136, 255))
    image.alpha_composite(bg)

    # Receipt shadow on larger sizes.
    if size >= 48:
        shadow = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        shadow_draw = ImageDraw.Draw(shadow)
        receipt_points = receipt_polygon(scale, offset=(0, 7 * scale))
        shadow_draw.polygon(receipt_points, fill=(120, 20, 70, 52))
        shadow = shadow.filter(ImageFilter.GaussianBlur(max(1, int(4 * scale))))
        image.alpha_composite(shadow)
        draw = ImageDraw.Draw(image)

    # Receipt body.
    draw.polygon(receipt_polygon(scale), fill=(255, 255, 255, 255))

    # Text strokes.
    stroke = max(2, round(12 * scale))
    line_color = (233, 76, 136, 255)
    for y, x2 in [(98, 153), (126, 169), (154, 145)]:
        draw.line(
            [(103 * scale, y * scale), (x2 * scale, y * scale)],
            fill=line_color,
            width=stroke,
            joint="curve",
        )

    return image


def receipt_polygon(scale: float, offset=(0, 0)):
    ox, oy = offset
    points = [
        (91, 69),
        (165, 69),
        (181, 85),
        (181, 190),
        (166, 181),
        (153, 190),
        (140, 181),
        (127, 190),
        (114, 181),
        (101, 190),
        (87, 182),
        (87, 85),
    ]
    return [(x * scale + ox, y * scale + oy) for x, y in points]


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    WINUI_ASSETS.mkdir(parents=True, exist_ok=True)
    icons = [make_icon(size) for size in SIZES]
    make_icon(256).save(PNG_PATH)
    icons[-1].save(ICO_PATH, sizes=[(size, size) for size in SIZES], append_images=icons[:-1])
    for size in TASKBAR_SIZES:
        icon = make_icon(size)
        icon.save(WINUI_ASSETS / f"Square44x44Logo.targetsize-{size}.png")
        icon.save(WINUI_ASSETS / f"Square44x44Logo.targetsize-{size}_altform-unplated.png")
    print(f"wrote {PNG_PATH}")
    print(f"wrote {ICO_PATH}")


if __name__ == "__main__":
    main()
