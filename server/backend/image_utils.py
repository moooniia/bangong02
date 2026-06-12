"""轻量图片处理。"""
import glob
import os
import zipfile
from datetime import datetime

from PIL import Image, ImageDraw, ImageFont


def _cn_font(size=32):
    for pat in [
        '/usr/share/fonts/**/NotoSansCJK-Regular.ttc',
        '/usr/share/fonts/**/wqy-microhei.ttc',
    ]:
        hits = glob.glob(pat, recursive=True)
        if hits:
            return ImageFont.truetype(hits[0], size)
    return ImageFont.load_default()


def compress_image(input_path, output_path, quality=80):
    img = Image.open(input_path)
    if img.mode in ('RGBA', 'P'):
        img = img.convert('RGB')
    img.save(output_path, 'JPEG', quality=quality, optimize=True)


def resize_image(input_path, output_path, width=None, height=None):
    img = Image.open(input_path)
    w, h = img.size
    if not width and not height:
        raise ValueError('请指定宽度或高度')
    if width and height:
        new_size = (int(width), int(height))
    elif width:
        ratio = int(width) / w
        new_size = (int(width), int(h * ratio))
    else:
        ratio = int(height) / h
        new_size = (int(w * ratio), int(height))
    img = img.resize(new_size, Image.LANCZOS)
    img.save(output_path)


def convert_image_format(input_path, output_path, fmt):
    img = Image.open(input_path)
    if fmt.upper() in ('JPG', 'JPEG') and img.mode in ('RGBA', 'P'):
        img = img.convert('RGB')
    img.save(output_path, fmt.upper() if fmt.upper() != 'JPG' else 'JPEG')


def add_image_watermark(input_path, output_path, text, opacity=128):
    if not text.strip():
        raise ValueError('请输入水印文字')
    img = Image.open(input_path).convert('RGBA')
    overlay = Image.new('RGBA', img.size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(overlay)
    font = _cn_font(max(24, img.size[0] // 25))
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    x = (img.size[0] - tw) / 2
    y = (img.size[1] - th) / 2
    draw.text((x, y), text, font=font, fill=(180, 180, 180, opacity))
    out = Image.alpha_composite(img, overlay)
    if output_path.lower().endswith('.jpg') or output_path.lower().endswith('.jpeg'):
        out.convert('RGB').save(output_path, 'JPEG', quality=90)
    else:
        out.save(output_path, 'PNG')


def add_image_timestamp(input_path, output_path, fmt=None):
    img = Image.open(input_path).convert('RGBA')
    draw = ImageDraw.Draw(img)
    font = _cn_font(max(20, img.size[0] // 40))
    stamp = datetime.now().strftime(fmt or '%Y-%m-%d %H:%M')
    margin = 12
    draw.text((margin, img.size[1] - margin - 30), stamp, font=font, fill=(255, 255, 255, 220))
    draw.text((margin + 1, img.size[1] - margin - 29), stamp, font=font, fill=(30, 30, 30, 200))
    if output_path.lower().endswith('.jpg') or output_path.lower().endswith('.jpeg'):
        img.convert('RGB').save(output_path, 'JPEG', quality=92)
    else:
        img.save(output_path, 'PNG')


def batch_process_images(input_paths, processor, output_dir, uid, ext='png'):
    """批量处理图片，返回 zip 路径。"""
    outputs = []
    for i, src in enumerate(input_paths):
        out = os.path.join(output_dir, f'{uid}_{i + 1}.{ext}')
        processor(src, out)
        outputs.append(out)
    zip_path = os.path.join(output_dir, f'{uid}.zip')
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for out in outputs:
            zf.write(out, os.path.basename(out))
            os.remove(out)
    return zip_path