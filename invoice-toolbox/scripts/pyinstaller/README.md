# Windows 打包说明

目标产物：

```text
发票工具箱.exe
```

建议在 Windows 10/11 x64 环境打包。不要在 macOS 上交叉打 Windows exe。

## 1. 准备环境

推荐直接运行。脚本会自动查找 Python；如果系统没有 `py`/`python` 命令，可先设置 `PYTHON_EXE` 指向实际 `python.exe`。

```powershell
powershell -ExecutionPolicy Bypass -File build\pyinstaller\build_windows.ps1
```

如果需要看 exe 里的真实错误，打控制台诊断版：

```powershell
powershell -ExecutionPolicy Bypass -File build\pyinstaller\build_windows.ps1 -Console
```

最终版本沿用原网页 UI，程序会自动打开本机页面；`-Console` 仅用于诊断启动错误。脚本会创建 `.venv-win`、安装依赖、生成图标、跑测试并打包。

如需手动执行，按下面步骤：

```powershell
cd path\to\發票助手2
$env:PYTHON_EXE = "C:\Path\To\python.exe"
$env:PYTHON_EXE -m venv .venv-win
.\.venv-win\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install pyinstaller
```

## 2. 生成图标

```powershell
python scripts\generate_icon.py
```

生成文件：

```text
assets\icons\invoice-toolbox.ico
assets\icons\invoice-toolbox-icon-256.png
```

## 3. 打包

```powershell
pyinstaller --clean --noconfirm build\pyinstaller\invoice_toolbox.spec
```

产物位置：

```text
dist\发票工具箱.exe
```

## 4. 基本验收

- 双击 `发票工具箱.exe` 会自动打开完整的发票工具箱界面。
- 选择发票文件夹后可以看到实时识别进度。
- PDF 第一页可以在人工核对区预览。
- 第二张购买方抬头和税号显示 `待确认`，不能乱填。
- 可以保存人工修改。
- 表格支持横向和纵向滚动。
- “重新开始”会清空当前任务，不删除历史归档。
- 可以按年月/业务分类/销售方归档。
- 可以导出 Excel，并保留原文件链接、归档文件链接。
- Windows Defender 不拦截。

## 5. 体积目标

- 理想：150MB 以内。
- 可接受：150MB 到 220MB。
- 超过 220MB 需要检查依赖。
- 超过 300MB 不建议发布。

