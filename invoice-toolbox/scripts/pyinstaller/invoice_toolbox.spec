# -*- mode: python ; coding: utf-8 -*-

import os
from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs, collect_submodules


block_cipher = None
ROOT = os.path.abspath(os.path.join(SPECPATH, "..", ".."))
CONSOLE = os.environ.get("INVOICE_TOOLBOX_CONSOLE") == "1"

datas = [
    (os.path.join(ROOT, "web"), "web"),
    (os.path.join(ROOT, "assets"), "assets"),
]
datas += collect_data_files("rapidocr_onnxruntime")
datas += collect_data_files("onnxruntime")

binaries = []
binaries += collect_dynamic_libs("onnxruntime")

hiddenimports = []
hiddenimports += collect_submodules("rapidocr_onnxruntime")
hiddenimports += collect_submodules("onnxruntime")
hiddenimports += collect_submodules("PIL")
hiddenimports += ["tkinter", "tkinter.filedialog"]
hiddenimports += ["fitz", "pymupdf"]

a = Analysis(
    [os.path.join(ROOT, "app.py")],
    pathex=[ROOT],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "matplotlib",
        "pandas",
        "scipy",
        "notebook",
        "IPython",
        "pytest",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="发票工具箱",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=CONSOLE,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=os.path.join(ROOT, "assets", "icons", "invoice-toolbox.ico"),
    version=os.path.join(ROOT, "build", "pyinstaller", "version_info.txt"),
)

