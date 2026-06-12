#!/usr/bin/env python3
"""生成统一风格的工具页面。"""
import os

BASE = os.path.join(os.path.dirname(__file__), "server", "frontend")

STYLE = """
*,*::before,*::after{margin:0;padding:0;box-sizing:border-box}
:root{--pink:#e94c88;--pink-bg:#fdf0f6;--near-white:#fbfbfb;--light-gray:#f4f4f4;--dark:#252525;--ink3:#888;--ink4:#ccc;--border:#ebebeb;--radius:12px;--shadow:0 1px 3px rgba(0,0,0,.05),0 4px 16px rgba(0,0,0,.06)}
body{font-family:'Noto Sans SC',sans-serif;background:var(--near-white);color:var(--dark);font-size:14px}
nav{position:sticky;top:0;z-index:99;height:68px;padding:0 56px;display:flex;align-items:center;justify-content:space-between;background:rgba(251,251,251,.95);backdrop-filter:blur(20px);border-bottom:1px solid var(--border)}
.logo{font-family:'Playfair Display',serif;font-size:20px;font-weight:900;color:var(--dark);text-decoration:none}.logo span{color:var(--pink)}
main{max-width:780px;margin:0 auto;padding:56px 32px 100px}
.breadcrumb{display:flex;align-items:center;gap:6px;font-size:12px;color:var(--ink4);margin-bottom:32px}.breadcrumb a{text-decoration:none;color:var(--ink4)}
.tool-header{margin-bottom:40px}.tool-title-row{display:flex;align-items:center;gap:16px;margin-bottom:10px}
.tool-icon-big{width:52px;height:52px;background:var(--pink-bg);border-radius:14px;display:flex;align-items:center;justify-content:center}
.tool-icon-big i{font-size:28px;color:var(--pink)}.tool-header h1{font-family:'Playfair Display',serif;font-size:32px;font-weight:900}
.tool-desc{font-size:14px;color:var(--ink3);line-height:1.75;margin-left:68px}
.upload-area{border:2px dashed var(--border);border-radius:16px;padding:56px 32px;text-align:center;cursor:pointer;background:#fff;margin-bottom:24px;transition:.2s}
.upload-area.drag,.upload-area:hover{border-color:var(--pink);background:var(--pink-bg)}
.upload-icon{font-size:48px;color:var(--ink4);margin-bottom:16px;display:block}
.file-list{display:none;margin-bottom:24px}.file-item{display:flex;align-items:center;gap:12px;background:#fff;border:1px solid var(--border);border-radius:12px;padding:14px 16px;margin-bottom:8px}
.file-item-icon{color:var(--pink)}.file-item-info{flex:1}.file-item-name{font-weight:600}.file-item-size{font-size:11px;color:var(--ink4)}
.file-item-remove{background:none;border:none;cursor:pointer;color:var(--ink4);font-size:18px}
.options{background:#fff;border:1px solid var(--border);border-radius:12px;padding:20px 24px;margin-bottom:24px}
.option-row{display:flex;align-items:center;justify-content:space-between;padding:10px 0}
.option-select{padding:6px 12px;border:1px solid var(--border);border-radius:8px;font-family:inherit}
.convert-btn{width:100%;display:flex;align-items:center;justify-content:center;gap:10px;background:var(--pink);color:#fff;font-size:15px;font-weight:700;padding:16px;border-radius:12px;border:none;cursor:pointer;font-family:inherit;margin-bottom:12px}
.convert-btn:disabled{background:var(--ink4);cursor:not-allowed}
.progress-area,.error-area,.result-area{display:none;margin-bottom:24px;padding:32px 24px;text-align:center;border-radius:12px;background:#fff;border:1px solid var(--border)}
.progress-label{font-size:14px;font-weight:600;color:var(--dark);margin-bottom:16px}
.progress-bar-wrap{background:var(--light-gray);border-radius:8px;height:8px;overflow:hidden;margin-bottom:10px}
.progress-bar{height:100%;border-radius:8px;background:linear-gradient(90deg,var(--pink),#f5a8cc);width:0%;transition:width 0.3s ease}
.progress-pct{font-size:12px;color:var(--ink3)}
.error-area{background:#fff5f5;border-color:#fca5a5;color:#dc2626}
.download-btn{display:inline-flex;align-items:center;gap:8px;background:var(--dark);color:#fff;padding:12px 28px;border-radius:24px;text-decoration:none;font-weight:700}
.tip{font-size:12px;color:var(--ink4);text-align:center;margin-bottom:24px}
"""

PAGES = [
    {
        "file": "pdf-merge.html", "title": "合并 PDF", "icon": "ti-files",
        "section": "PDF 处理", "desc": "把多个 PDF 合并成一个文件，顺序按上传先后排列。",
        "accept": ".pdf", "multiple": True, "api": "/api/pdf/merge",
        "btn": "开始合并", "hint": "一次最多 20 个文件，每个不超过 100MB",
        "progressTask": "pdf-process",
        "upload": "选择 PDF 文件（可多选）",
    },
    {
        "file": "pdf-split.html", "title": "拆分 PDF", "icon": "ti-scissors",
        "section": "PDF 处理", "desc": "把 PDF 拆成多个小文件，打包成 ZIP 下载。",
        "accept": ".pdf", "api": "/api/pdf/split", "btn": "开始拆分",
        "hint": "最多 50 页，页数多的请先压缩或分段处理",
        "progressTask": "pdf-process",
        "options": '<div class="options"><div class="option-row"><span>拆分方式</span><select class="option-select" id="modeSelect"><option value="each">每页一个文件</option><option value="half">一分为二</option></select></div></div>',
        "extra": "[{id:'modeSelect',name:'mode'}]",
    },
    {
        "file": "pdf-rotate.html", "title": "PDF 旋转", "icon": "ti-rotate",
        "section": "PDF 处理", "desc": "旋转 PDF 所有页面，纠正扫描方向。",
        "accept": ".pdf", "api": "/api/pdf/rotate", "btn": "开始旋转",
        "progressTask": "pdf-process",
        "options": '<div class="options"><div class="option-row"><span>旋转角度</span><select class="option-select" id="angleSelect"><option value="90">顺时针 90°</option><option value="180">旋转 180°</option><option value="270">逆时针 90°</option></select></div></div>',
        "extra": "[{id:'angleSelect',name:'angle'}]",
    },
    {
        "file": "pdf-compress.html", "title": "PDF 压缩", "icon": "ti-file-zip",
        "section": "PDF 处理", "desc": "减小 PDF 体积，方便微信、邮件发送。已很精简的文件压缩空间有限。",
        "accept": ".pdf", "api": "/api/pdf/compress", "btn": "开始压缩",
        "progressTask": "pdf-process",
    },
    {
        "file": "pdf-to-image.html", "title": "PDF 转图片", "icon": "ti-photo",
        "section": "PDF 处理", "desc": "把 PDF 每一页转成 PNG 图片，打包 ZIP 下载。",
        "accept": ".pdf", "api": "/api/pdf/to-images", "btn": "开始转换",
        "hint": "最多 50 页",
        "progressTask": "pdf-to-image",
    },
    {
        "file": "images-to-pdf.html", "title": "图片转 PDF", "icon": "ti-photo-up",
        "section": "PDF 处理", "desc": "把多张图片合成一个 PDF，顺序按选择先后。",
        "accept": ".jpg,.jpeg,.png", "multiple": True, "api": "/api/images/to-pdf",
        "btn": "生成 PDF", "upload": "选择图片（可多选）",
        "progressTask": "image-process",
    },
    {
        "file": "image-compress.html", "title": "图片压缩", "icon": "ti-photo-minus",
        "section": "图片处理", "desc": "缩小图片体积，发微信、传系统更快。",
        "accept": ".jpg,.jpeg,.png", "api": "/api/image/compress", "btn": "开始压缩",
        "progressTask": "image-process",
        "options": '<div class="options"><div class="option-row"><span>压缩质量</span><select class="option-select" id="qualitySelect"><option value="85">高（推荐）</option><option value="70">中</option><option value="50">小体积</option></select></div></div>',
        "extra": "[{id:'qualitySelect',name:'quality'}]",
    },
    {
        "file": "image-resize.html", "title": "图片改尺寸", "icon": "ti-resize",
        "section": "图片处理", "desc": "按宽度或高度等比缩放图片。",
        "accept": ".jpg,.jpeg,.png", "api": "/api/image/resize", "btn": "开始调整",
        "progressTask": "image-process",
        "options": '<div class="options"><div class="option-row"><span>宽度（像素）</span><input class="option-select" id="widthInput" type="number" placeholder="如 800"></div><div class="option-row"><span>高度（像素）</span><input class="option-select" id="heightInput" type="number" placeholder="留空则按宽度等比"></div></div>',
        "extra": "[{id:'widthInput',name:'width'},{id:'heightInput',name:'height'}]",
    },
    {
        "file": "image-convert.html", "title": "图片格式转换", "icon": "ti-transform",
        "section": "图片处理", "desc": "JPG、PNG 互转，满足不同系统要求。",
        "accept": ".jpg,.jpeg,.png", "api": "/api/image/convert", "btn": "开始转换",
        "progressTask": "image-process",
        "options": '<div class="options"><div class="option-row"><span>输出格式</span><select class="option-select" id="formatSelect"><option value="png">PNG</option><option value="jpg">JPG</option></select></div></div>',
        "extra": "[{id:'formatSelect',name:'format'}]",
    },
    {
        "file": "pdf-delete-pages.html", "title": "删除 PDF 页面", "icon": "ti-trash",
        "section": "PDF 处理", "desc": "删除 PDF 中不需要的页，如空白页、广告页。",
        "accept": ".pdf", "api": "/api/pdf/delete-pages", "btn": "删除并下载",
        "progressTask": "pdf-process",
        "options": '<div class="options"><div class="option-row"><span>要删除的页码</span><input class="option-select" id="pagesInput" placeholder="如 1,3,5-7" style="width:180px"></div></div>',
        "extra": "[{id:'pagesInput',name:'pages'}]",
    },
    {
        "file": "pdf-watermark.html", "title": "PDF 加水印", "icon": "ti-droplet",
        "section": "PDF 处理", "desc": "在 PDF 每页加上文字水印，如「内部资料」「草稿」。",
        "accept": ".pdf", "api": "/api/pdf/watermark", "btn": "添加水印",
        "progressTask": "pdf-process",
        "options": '<div class="options"><div class="option-row"><span>水印文字</span><input class="option-select" id="wmText" placeholder="如：内部资料" style="width:180px"></div></div>',
        "extra": "[{id:'wmText',name:'text'}]",
    },
    {
        "file": "pdf-encrypt.html", "title": "PDF 加密", "icon": "ti-lock",
        "section": "PDF 处理", "desc": "给 PDF 设置打开密码，防止他人随意查看。",
        "accept": ".pdf", "api": "/api/pdf/encrypt", "btn": "加密 PDF",
        "progressTask": "pdf-process",
        "options": '<div class="options"><div class="option-row"><span>打开密码</span><input class="option-select" id="pwdInput" type="password" placeholder="请牢记密码"></div></div>',
        "extra": "[{id:'pwdInput',name:'password'}]",
    },
    {
        "file": "pdf-decrypt.html", "title": "PDF 解密", "icon": "ti-lock-open",
        "section": "PDF 处理", "desc": "去掉 PDF 打开密码（需要知道原密码）。",
        "accept": ".pdf", "api": "/api/pdf/decrypt", "btn": "解密 PDF",
        "progressTask": "pdf-process",
        "options": '<div class="options"><div class="option-row"><span>原密码</span><input class="option-select" id="pwdInput" type="password"></div></div>',
        "extra": "[{id:'pwdInput',name:'password'}]",
    },
    {
        "file": "pdf-grayscale.html", "title": "PDF 转黑白", "icon": "ti-contrast",
        "section": "PDF 处理", "desc": "把彩色 PDF 转成黑白，方便打印、减小体积。",
        "accept": ".pdf", "api": "/api/pdf/grayscale", "btn": "转黑白",
        "hint": "最多 50 页",
        "progressTask": "pdf-process",
    },
    {
        "file": "image-watermark.html", "title": "批量加水印", "icon": "ti-droplet-half-2",
        "section": "图片处理", "desc": "给一张或多张图片加文字水印，多张自动打包 ZIP。",
        "accept": ".jpg,.jpeg,.png", "multiple": True, "api": "/api/image/watermark", "btn": "添加水印",
        "progressTask": "image-process",
        "upload": "选择图片（可多选）",
        "options": '<div class="options"><div class="option-row"><span>水印文字</span><input class="option-select" id="wmText" placeholder="如：内部资料"></div></div>',
        "extra": "[{id:'wmText',name:'text'}]",
    },
    {
        "file": "image-timestamp.html", "title": "批量加时间戳", "icon": "ti-clock",
        "section": "图片处理", "desc": "在图片角落加上当前拍摄时间，多张自动打包 ZIP。",
        "accept": ".jpg,.jpeg,.png", "multiple": True, "api": "/api/image/timestamp", "btn": "加时间戳",
        "progressTask": "image-process",
        "upload": "选择图片（可多选）",
    },
    {
        "file": "pdf-extract-images.html", "title": "提取 PDF 图片", "icon": "ti-photo-search",
        "section": "PDF 处理", "desc": "把 PDF 里嵌入的图片全部提取出来，打包 ZIP 下载。",
        "accept": ".pdf", "api": "/api/pdf/extract-images", "btn": "提取图片",
        "progressTask": "pdf-process",
    },
]


def render(p):
    multiple = "true" if p.get("multiple") else "false"
    extra = p.get("extra", "[]")
    progress_task = p.get("progressTask", "")
    progress_line = f"  progressTask: '{progress_task}',\n" if progress_task else ""
    return f"""<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{p['title']} — 办公工具箱</title>
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700;900&family=Noto+Sans+SC:wght@400;500;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@tabler/icons-webfont@latest/tabler-icons.min.css">
<link rel="stylesheet" href="/assets/common.css">
<style>{STYLE}</style>
</head>
<body>
<nav><a class="logo" href="/">办公<span>工具箱</span></a></nav>
<main>
  <div class="breadcrumb"><a href="/">首页</a><i class="ti ti-chevron-right"></i><span>{p['section']}</span><i class="ti ti-chevron-right"></i><span>{p['title']}</span></div>
  <div class="tool-header">
    <div class="tool-title-row">
      <div class="tool-icon-big"><i class="ti {p['icon']}"></i></div>
      <h1>{p['title']}</h1>
    </div>
    <p class="tool-desc">{p['desc']}</p>
  </div>
  <div class="upload-area" id="uploadArea">
    <input type="file" id="fileInput" accept="{p['accept']}" {"multiple" if p.get("multiple") else ""} style="display:none">
    <i class="ti ti-cloud-upload upload-icon"></i>
    <div style="font-weight:700;margin-bottom:6px">{p.get('upload', '点击或拖拽文件到这里')}</div>
    <div style="font-size:13px;color:var(--ink3)">{p.get('hint', '文件处理后自动删除')}</div>
  </div>
  <div class="file-list" id="fileList"></div>
  {p.get('options', '')}
  <button class="convert-btn" id="convertBtn" onclick="startProcess()" disabled><i class="ti ti-bolt"></i>{p['btn']}</button>
  <p class="tip"><i class="ti ti-shield-lock"></i> 文件仅用于本次处理，完成后自动删除</p>
  <div class="progress-area" id="progressArea">
    <div class="progress-label" id="progressLabel">处理中，请稍候…</div>
    <div class="progress-bar-wrap"><div class="progress-bar" id="progressBar"></div></div>
    <div class="progress-pct" id="progressPct">0%</div>
  </div>
  <div class="error-area" id="errorArea"><span id="errorText"></span></div>
  <div class="result-area" id="resultArea">
    <i class="ti ti-circle-check" style="font-size:48px;color:#22c55e"></i>
    <p style="margin:12px 0 20px;font-weight:700">处理完成！</p>
    <a href="#" class="download-btn" id="downloadBtn"><i class="ti ti-download"></i>下载文件</a>
  </div>
</main>
<script src="/assets/convert-progress.js"></script>
<script src="/assets/tool-page.js"></script>
<script>
initToolPage({{
  api: '{p['api']}',
  accept: '{p['accept']}',
  multiple: {multiple},
  extraFields: {extra},
{progress_line}  downloadText: '下载结果'
}});
</script>
</body>
</html>"""


for p in PAGES:
    path = os.path.join(BASE, p["file"])
    with open(path, "w", encoding="utf-8") as f:
        f.write(render(p))
    print("Generated", p["file"])

# QR code page - pure frontend
qr_html = """<!DOCTYPE html>
<html lang="zh"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>生成二维码 — 办公工具箱</title>
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700;900&family=Noto+Sans+SC:wght@400;500;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@tabler/icons-webfont@latest/tabler-icons.min.css">
<link rel="stylesheet" href="/assets/common.css">
<style>""" + STYLE + """textarea{width:100%;min-height:120px;border:1px solid var(--border);border-radius:12px;padding:16px;font-family:inherit;font-size:14px;resize:vertical}
</style></head><body>
<nav><a class="logo" href="/">办公<span>工具箱</span></a></nav>
<main>
<div class="breadcrumb"><a href="/">首页</a><i class="ti ti-chevron-right"></i><span>图片处理</span></div>
<div class="tool-header"><div class="tool-title-row"><div class="tool-icon-big"><i class="ti ti-qrcode"></i></div><h1>生成二维码</h1></div>
<p class="tool-desc">输入网址或文字，一键生成二维码图片，可右键保存。</p></div>
<textarea id="qrText" placeholder="输入网址、文字、WiFi 信息等..."></textarea>
<button class="convert-btn" style="margin-top:16px" onclick="genQr()"><i class="ti ti-qrcode"></i>生成二维码</button>
<div class="result-area" id="resultArea" style="display:none"><canvas id="qrCanvas"></canvas>
<p style="margin-top:12px;font-size:12px;color:var(--ink3)">右键图片 → 另存为</p></div>
</main>
<script src="https://cdn.jsdelivr.net/npm/qrcode@1/build/qrcode.min.js"></script>
<script>
async function genQr(){
  const t=document.getElementById('qrText').value.trim();
  if(!t){alert('请输入内容');return;}
  const c=document.getElementById('qrCanvas');
  await QRCode.toCanvas(c,t,{width:280,margin:2});
  document.getElementById('resultArea').style.display='block';
}
</script></body></html>"""
with open(os.path.join(BASE, "qrcode.html"), "w", encoding="utf-8") as f:
    f.write(qr_html)
print("Generated qrcode.html")

# 文件翻译
ft = """<!DOCTYPE html>
<html lang="zh"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>文件翻译 — 办公工具箱</title>
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700;900&family=Noto+Sans+SC:wght@400;500;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@tabler/icons-webfont@latest/tabler-icons.min.css">
<link rel="stylesheet" href="/assets/common.css">
<style>""" + STYLE + """</style></head><body>
<nav><a class="logo" href="/">办公<span>工具箱</span></a></nav>
<main>
<div class="breadcrumb"><a href="/">首页</a><i class="ti ti-chevron-right"></i><span>翻译</span></div>
<div class="tool-header"><div class="tool-title-row"><div class="tool-icon-big"><i class="ti ti-file-symlink"></i></div><h1>文件翻译</h1></div>
<p class="tool-desc">上传 Word、PDF 或 TXT，自动提取文字并翻译，下载译文文件。</p></div>
<div class="upload-area" id="uploadArea"><input type="file" id="fileInput" accept=".txt,.doc,.docx,.pdf" style="display:none">
<i class="ti ti-cloud-upload upload-icon"></i><div style="font-weight:700">选择文件</div><div style="font-size:13px;color:var(--ink3)">支持 TXT、Word、PDF</div></div>
<div class="file-list" id="fileList"></div>
<div class="options">
<div class="option-row"><span>原文语言</span><select class="option-select" id="fromLang"><option value="auto">自动</option><option value="zh-CN">中文</option><option value="en">英语</option></select></div>
<div class="option-row"><span>译为</span><select class="option-select" id="toLang"><option value="en">英语</option><option value="zh-CN">中文</option></select></div>
<div class="option-row"><span>输出格式</span><select class="option-select" id="fmtSelect"><option value="txt">TXT 文本</option><option value="docx">Word 文档</option></select></div>
</div>
<button class="convert-btn" id="convertBtn" onclick="startProcess()" disabled><i class="ti ti-language"></i>开始翻译</button>
<div class="progress-area" id="progressArea">
<div class="progress-label" id="progressLabel">翻译中，请稍候…</div>
<div class="progress-bar-wrap"><div class="progress-bar" id="progressBar"></div></div>
<div class="progress-pct" id="progressPct">0%</div>
</div>
<div class="error-area" id="errorArea"><span id="errorText"></span></div>
<div class="result-area" id="resultArea"><a href="#" class="download-btn" id="downloadBtn"><i class="ti ti-download"></i>下载译文</a></div>
</main>
<script src="/assets/convert-progress.js"></script>
<script src="/assets/tool-page.js"></script>
<script>initToolPage({api:'/api/translate/file',accept:'.txt,.doc,.docx,.pdf',multiple:false,extraFields:[{id:'fromLang',name:'from'},{id:'toLang',name:'to'},{id:'fmtSelect',name:'format'}],progressTask:'translate',downloadText:'下载译文'});</script>
</body></html>"""
with open(os.path.join(BASE, "file-translate.html"), "w", encoding="utf-8") as f:
    f.write(ft)
print("Generated file-translate.html")

# Office 互转
oc = """<!DOCTYPE html>
<html lang="zh"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Office 文档互转 — 办公工具箱</title>
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700;900&family=Noto+Sans+SC:wght@400;500;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@tabler/icons-webfont@latest/tabler-icons.min.css">
<link rel="stylesheet" href="/assets/common.css">
<style>""" + STYLE + """</style></head><body>
<nav><a class="logo" href="/">办公<span>工具箱</span></a></nav>
<main>
<div class="breadcrumb"><a href="/">首页</a><i class="ti ti-chevron-right"></i><span>文件工具</span></div>
<div class="tool-header"><div class="tool-title-row"><div class="tool-icon-big"><i class="ti ti-refresh"></i></div><h1>Office 文档互转</h1></div>
<p class="tool-desc">Word、Excel、PPT、PDF 之间互相转换，选文件和目标格式即可。</p></div>
<div class="upload-area" id="uploadArea"><input type="file" id="fileInput" accept=".pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx" style="display:none">
<i class="ti ti-cloud-upload upload-icon"></i><div style="font-weight:700">选择 Office 或 PDF 文件</div></div>
<div class="file-list" id="fileList"></div>
<div class="options"><div class="option-row"><span>转换为</span>
<select class="option-select" id="formatSelect">
<option value="pdf">PDF</option><option value="docx">Word (.docx)</option>
<option value="xlsx">Excel (.xlsx)</option><option value="pptx">PPT (.pptx)</option>
</select></div></div>
<button class="convert-btn" id="convertBtn" onclick="startProcess()" disabled><i class="ti ti-transform"></i>开始转换</button>
<div class="progress-area" id="progressArea">
<div class="progress-label" id="progressLabel">转换中，请稍候…</div>
<div class="progress-bar-wrap"><div class="progress-bar" id="progressBar"></div></div>
<div class="progress-pct" id="progressPct">0%</div>
</div>
<div class="error-area" id="errorArea"><span id="errorText"></span></div>
<div class="result-area" id="resultArea"><a href="#" class="download-btn" id="downloadBtn"><i class="ti ti-download"></i>下载文件</a></div>
</main>
<script src="/assets/convert-progress.js"></script>
<script src="/assets/tool-page.js"></script>
<script>initToolPage({api:'/api/convert',accept:'.pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx',multiple:false,extraFields:[{id:'formatSelect',name:'format'}],progressTask:'office-convert',progressOpts:function(files){return{targetFormat:document.getElementById('formatSelect').value,fileName:files[0]&&files[0].name};},downloadText:'下载文件'});</script>
</body></html>"""
with open(os.path.join(BASE, "office-convert.html"), "w", encoding="utf-8") as f:
    f.write(oc)
print("Generated office-convert.html")

# 批量改名（纯浏览器，不上传服务器）
fr = """<!DOCTYPE html>
<html lang="zh"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>文件批量改名 — 办公工具箱</title>
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700;900&family=Noto+Sans+SC:wght@400;500;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@tabler/icons-webfont@latest/tabler-icons.min.css">
<link rel="stylesheet" href="/assets/common.css">
<style>""" + STYLE + """.preview{ background:#fff;border:1px solid var(--border);border-radius:12px;padding:16px;margin:16px 0;font-size:13px;max-height:200px;overflow:auto}</style></head><body>
<nav><a class="logo" href="/">办公<span>工具箱</span></a></nav>
<main>
<div class="breadcrumb"><a href="/">首页</a><i class="ti ti-chevron-right"></i><span>文件工具</span></div>
<div class="tool-header"><div class="tool-title-row"><div class="tool-icon-big"><i class="ti ti-forms"></i></div><h1>文件批量改名</h1></div>
<p class="tool-desc">在浏览器本地改名，文件不会上传到服务器。支持 {n} 序号、{name} 原文件名。</p></div>
<div class="upload-area" onclick="document.getElementById('fileInput').click()">
<input type="file" id="fileInput" multiple style="display:none" onchange="onPick(this)">
<i class="ti ti-cloud-upload upload-icon"></i><div style="font-weight:700">选择多个文件</div></div>
<div class="options">
<div class="option-row"><span>命名规则</span><input class="option-select" id="pattern" value="{n}_{name}" style="width:200px" oninput="preview()"></div>
<div class="option-row"><span>起始序号</span><input class="option-select" id="startN" type="number" value="1" style="width:80px" oninput="preview()"></div>
</div>
<div class="preview" id="preview">选择文件后预览新文件名</div>
<button class="convert-btn" id="goBtn" onclick="downloadZip()" disabled><i class="ti ti-download"></i>下载改名后的 ZIP</button>
<p class="tip"><i class="ti ti-shield-lock"></i> 全程在本地处理，不上传服务器</p>
</main>
<script src="https://cdn.jsdelivr.net/npm/jszip@3/dist/jszip.min.js"></script>
<script>
let files=[];
function onPick(input){ files=Array.from(input.files); document.getElementById('goBtn').disabled=!files.length; preview(); }
function preview(){
  const p=document.getElementById('pattern').value||'{n}_{name}';
  let n=parseInt(document.getElementById('startN').value)||1;
  const el=document.getElementById('preview');
  if(!files.length){el.textContent='选择文件后预览新文件名';return;}
  el.innerHTML=files.map(f=>{const base=f.name.replace(/\\.[^.]+$/,'');const ext=f.name.match(/\\.[^.]+$/)?.[0]||'';
    const nn=p.replace(/\\{n\\}/g,n++).replace(/\\{name\\}/g,base)+ext;
    return f.name+' → <b>'+nn+'</b>';}).join('<br>');
}
async function downloadZip(){
  const p=document.getElementById('pattern').value||'{n}_{name}';
  let n=parseInt(document.getElementById('startN').value)||1;
  const zip=new JSZip();
  for(const f of files){const base=f.name.replace(/\\.[^.]+$/,'');const ext=f.name.match(/\\.[^.]+$/)?.[0]||'';
    const nn=p.replace(/\\{n\\}/g,n++).replace(/\\{name\\}/g,base)+ext;
    zip.file(nn,await f.arrayBuffer());}
  const blob=await zip.generateAsync({type:'blob'});
  const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download='重命名文件.zip';a.click();
}
</script></body></html>"""
with open(os.path.join(BASE, "file-rename.html"), "w", encoding="utf-8") as f:
    f.write(fr)
print("Generated file-rename.html")