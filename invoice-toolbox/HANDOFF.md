# 发票工具箱 HANDOFF

更新时间：2026-07-10

这是从 macOS 转到 Windows 继续开发和打包的交接文件。最终要求以本文和 `交接说明.md` 为准。

## 项目定位

本项目是本地 PC 发票整理工具，名称暂定为“发票工具箱”，品牌为“办公工具箱”。它不是单纯 OCR，而是要完成批量识别、人工核对、重命名归档、Excel 导出的完整流程。

最重要原则：不确定字段不要猜，不要为了填满表格乱写。批量处理时，错误填满比留空更危险。

## 最终产品决策

- 软件名：发票工具箱。
- 品牌：办公工具箱。
- 版本：1.0.0。
- UI 使用办公工具箱粉白品牌风格。
- 导出 Excel 使用正式绿色表头，保持严肃。
- 去掉作者信息、免激活单机版等旧版信息。
- Excel 保留原文件链接、归档文件链接、统计行。
- 不确定字段显示“待确认”，红字加粗并高亮。
- 不要在最终 Excel 里写“异常原因”，用户不需要看技术解释。
- 每条记录都能打开右侧核对栏，不只限待确认记录。
- 右侧核对栏只保留 X 关闭，不要重复“收回”按钮。
- 图片放大不能挡住填写区域，要能边看边填。
- 图片查看支持缩放、拖动、旋转，并有打开/关闭动画。
- 版本信息页要有版本号、版权、办公工具箱链接和缩放动画。
- 图标方案：粉色底 + 白色票据符号。

## 当前已实现

- OCR 识别图片。
- 安全解析购买方/销售方。
- 统一社会信用代码校验。
- 畸变/不确定字段留空并标记待确认。
- 本地网页式 UI。
- 深浅色切换。
- 主表展示、统计、总金额。
- 点击任意记录打开核对栏。
- 人工编辑字段并保存。
- 原图预览、放大、缩放、拖动、旋转。
- 按年月、业务分类/年月、销售方/年月归档。
- 重命名归档文件。
- 导出绿色正式 Excel。
- Excel 保留原文件链接和归档文件链接。
- 待确认字段在 Excel 中红字粗体、浅黄底。
- Windows PyInstaller 打包脚本。
- 图标生成脚本。
- 单元测试 12 个通过。

## 当前卡点

Windows 上已经能打出约 102MB 的 `发票工具箱.exe`。这个大小是合理的，说明不是之前那种 5MB 缺库包。

但双击后浏览器跳到：

```text
http://127.0.0.1:8765/
```

页面打不开。

这说明程序至少执行到了“打开浏览器”，但本机服务没有正常响应。需要在 Windows 上看真实日志。

可能原因：

- PyInstaller 打包后的服务启动异常。
- 静态资源路径在 exe 环境中仍有问题。
- 端口被占用或服务未监听。
- Windows 安全软件/防火墙拦截本机服务。
- 当前 `console=False` 隐藏了真实报错。

## Windows 接手第一步

先不要继续改 UI，先定位服务为什么打不开。

### 1. 用源码直接运行

```powershell
cd C:\Users\paz\Desktop\invoice-toolbox-project-fixed2
.\.venv-win\Scripts\python.exe app.py
```

如果终端显示：

```text
发票工具箱已启动：http://127.0.0.1:8765
```

再手动打开：

```text
http://127.0.0.1:8765/
```

判断：

- 源码能打开，exe 打不开：问题在 PyInstaller 打包。
- 源码也打不开：问题在 app 启动、端口、Windows 本机网络或安全拦截。

### 2. 打控制台版 exe 看报错

临时修改：

```text
build/pyinstaller/invoice_toolbox.spec
```

把：

```python
console=False
```

改成：

```python
console=True
```

重新打包，然后在 PowerShell 运行：

```powershell
.\dist\发票工具箱.exe
```

这样可以看到真实错误。

## 打包命令

重新解压项目后运行：

```powershell
cd C:\Users\paz\Desktop\invoice-toolbox-project-fixed2
Remove-Item -Recurse -Force .venv-win, dist, build\invoice_toolbox -ErrorAction SilentlyContinue
powershell -ExecutionPolicy Bypass -File .\build\pyinstaller\build_windows.ps1
```

注意不要删除整个 `build` 文件夹，因为打包脚本就在里面。

## 主要文件

```text
app.py                                  本地服务入口
web/design.html                         主界面
web/design.css                          主界面样式
web/design.js                           主界面交互
invoice_assistant/ocr.py                OCR 调用
invoice_assistant/field_parser.py       发票字段解析
invoice_assistant/safe_party_parser.py  购买方/销售方安全判断
invoice_assistant/uscc.py               统一社会信用代码校验
invoice_assistant/archive.py            归档与重命名
invoice_assistant/report_exporter.py    Excel 导出
build/pyinstaller/build_windows.ps1     Windows 打包脚本
build/pyinstaller/invoice_toolbox.spec  PyInstaller 配置
scripts/generate_icon.py                图标生成
tests/                                  单元测试
```

## 验收清单

- 双击 exe 能打开界面。
- 页面不是纯文字，CSS 正常加载。
- 任意记录可打开右侧核对栏。
- 右侧核对栏可关闭。
- 图片可放大、缩放、拖动、旋转。
- 畸变样本购买方抬头和税号显示待确认，不能乱填。
- 高质量样本不应出现错字。
- 商品/服务字段不能整列为空。
- 可以导出 Excel。
- Excel 为绿色正式表格。
- Excel 有原文件链接和归档文件链接。
- Excel 有统计行。
- 待确认字段红字粗体高亮。
- Excel 不出现“异常原因”列。

## 注意

`docs/safety_ui_requirements.md` 是早期讨论记录，里面有些内容已过时，例如“异常原因列”。最终以后续要求和本文件为准。

## 2026-07-10 Windows 修正记录

当前最终入口已恢复为原来的网页 UI：`app.py` 提供本地后端，`web/` 保留完整视觉和交互。Tkinter 重做版不作为交付入口。

打包脚本也已增强：

- 支持 `-Console` 打控制台诊断版。
- 支持通过 `PYTHON_EXE` 指定 Python 路径。
- 找不到 Python 时会给出明确错误，不再只报 `py` 命令不存在。
- 支持 PDF 渲染 OCR、PDF 第一页预览、后台识别进度和任务复位。
- 归档文件名使用发票号码或原文件名，不再依赖扫描序号，并对重复归档保持幂等。

建议下一步重新打包并验收：

```powershell
cd C:\Users\paz\Desktop\发票工具箱\发票工具箱_交接包_20260710
powershell -ExecutionPolicy Bypass -File .\build\pyinstaller\build_windows.ps1
.\dist\发票工具箱.exe
```

如果仍打不开，运行：

```powershell
powershell -ExecutionPolicy Bypass -File .\build\pyinstaller\build_windows.ps1 -Console
.\dist\发票工具箱.exe
```

同时查看：

```text
dist\发票工具箱.log
```
