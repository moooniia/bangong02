# -*- mode: python ; coding: utf-8 -*-

import os
from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs, collect_submodules

ROOT = os.path.abspath(os.path.join(SPECPATH, "..", ".."))

datas = [
    (os.path.join(ROOT, "assets"), "assets"),
]
datas += collect_data_files("rapidocr_onnxruntime")
datas += collect_data_files("onnxruntime")

binaries = collect_dynamic_libs("onnxruntime")
hiddenimports = ["tkinter", "tkinter.filedialog", "fitz", "pymupdf"]
hiddenimports += collect_submodules("rapidocr_onnxruntime")
hiddenimports += collect_submodules("onnxruntime")
hiddenimports += collect_submodules("PIL")

a = Analysis(
    [os.path.join(ROOT, "native_app.py")],
    pathex=[ROOT],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["matplotlib", "pandas", "scipy", "notebook", "IPython", "pytest"],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="发票工具箱_原生",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    icon=os.path.join(ROOT, "assets", "icons", "invoice-toolbox.ico"),
)
