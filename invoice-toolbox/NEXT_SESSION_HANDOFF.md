# 发票工具箱下一轮交接文档

更新日期：2026-07-14  
当前主项目：`C:\Users\paz\toolbox-work\invoice-toolbox`  
网站项目：`C:\Users\paz\toolbox-work\server\frontend`  
用户测试文件夹：`C:\Users\paz\Desktop\111`、`C:\Users\paz\Desktop\发票文件夹`、`C:\Users\paz\Desktop\发票归档文件夹`  
当前已发布线上版本：`1.0.0.52`  
当前本地已安装/可安装候选版本：`1.0.0.60`（已编译、已签名、本机已安装；尚未作为网站 latest 发布）  
当前应用包名：`Paz.InvoiceToolbox`  

## 新对话开场白

新开 Codex 对话时，直接发下面这句：

> 继续做 `C:\Users\paz\toolbox-work\invoice-toolbox\NEXT_SESSION_HANDOFF.md`，先读这个文件，不要重新讨论历史。按“下一轮优先任务”顺序做，能自己完成就继续执行，只有真正需要我提供文件、权限或方向选择时才停下。

## 总目标

发票工具箱必须是一个原生 Windows 桌面软件，不是网页壳。方向是 WinUI 3 原生软件，视觉参考办公工具箱网站的字体、粉色强调、干净柔和的现代界面，而不是老式 WinForms 风格。

核心能力：

- 批量选择发票文件夹，递归读取子文件夹里的 PDF、图片发票。
- 选择项目文件夹/归档文件夹。
- OCR 识别发票字段。
- 表格展示全部关键字段。
- 对不可靠、缺失、冲突字段醒目标记待审核。
- 右侧人工核对栏可以缩放、拖动、旋转预览图，并编辑字段。
- 导出 Excel 和归档文件。
- 软件启动时可检测网站版本，显示“更新/忽略”，不弹窗打扰。
- 网站中提供发票工具箱下载页、真实软件展示图和版本信息。

## 当前状态

已知主线：

- 2026-07-14 本轮已完成后端待审核可靠性第一批修复：
  - `invoice_assistant/record_builder.py` 最终复查已把不含税金额、税额纳入关键必填字段。
  - 增加金额格式、负金额、常见税率、三组金额公式自校验。
  - 重复发票补全会同步补齐不含税金额和税额；补不齐仍待审核。
  - 单元测试已补到 43 项并全部通过。
  - 用 `dist/InvoiceToolbox.Worker.exe` 跑桌面 `发票` 目录 75 个真实样本，再套用当前源码复查：旧规则待审核 9 条，新规则待审核 39 条，已确认 36 条，关键字段空缺漏审 0 条。
  - 新增待审核主要来自金额/税率公式不一致，属于“旧规则会放行、现在要求人工核对”的风险项。
  - 已用本地 `.venv-build` 重建 `dist\InvoiceToolbox.Worker.exe`，并复制到 `winui_app\Backend\InvoiceToolbox.Worker.exe`。
  - 当前机器系统 `dotnet` 只有 Runtime，但用户目录存在可用 SDK：`C:\Users\paz\.dotnet\dotnet.exe`，版本 `8.0.422`。
  - 已使用该 SDK 正常编译 WinUI，并生成 `1.0.0.53` MSIX。
  - `1.0.0.53` 已使用 CurrentUser 证书 `CN=Paz Invoice Toolbox`、Thumbprint `EC83DC4897A69D7150141AC0BFD3FA3855E9784A` 签名，并通过 `signtool verify /pa /v`。
  - 新 worker 单文件烟测：`031002100311_47916740.pdf` 会因金额/税率公式不一致进入待审核，说明候选 worker 已包含新复查规则。
  - 项目包：`C:\Users\paz\toolbox-work\invoice-toolbox\winui_app\AppPackages\InvoiceToolbox.WinUI_1.0.0.53_x64_Test\InvoiceToolbox.WinUI_1.0.0.53_x64.msix`
  - 桌面安装包：`C:\Users\paz\Desktop\invoice-toolbox-1.0.0.53-installer\InvoiceToolbox.WinUI_1.0.0.53_x64.msix`
  - 桌面安装脚本：`C:\Users\paz\Desktop\invoice-toolbox-1.0.0.53-installer\install_admin.cmd`
  - 桌面候选包 size: `209925855`
  - 桌面候选包 sha256: `DDD069E152E0E2084BB14810F5E9929FFE5EDDB66E4B435BE3D39822AADB5696`
  - 2026-07-14 追加 UI 修复：重做多尺寸高质量图标，修复左侧栏折叠按钮裁切，增加发票行持久选中高亮。
  - 因系统已经安装过 `1.0.0.53`，同版本不同内容无法覆盖安装，所以本轮 UI 修复升版为 `1.0.0.54`。
  - `1.0.0.54` 已安装成功：`Get-AppxPackage -Name Paz.InvoiceToolbox` 返回 `Version 1.0.0.54`、`Status Ok`。
  - `1.0.0.54` 桌面安装目录：`C:\Users\paz\Desktop\invoice-toolbox-1.0.0.54-installer`
  - `1.0.0.54` 桌面安装包：`C:\Users\paz\Desktop\invoice-toolbox-1.0.0.54-installer\InvoiceToolbox.WinUI_1.0.0.54_x64.msix`
  - `1.0.0.54` 桌面安装包 sha256：`ABF88D5C4E59F37CEE02CDF557C199F1E0BA5B5B9E352EAEA3DC689D8BD9F228`
  - 已用 `Start-Process shell:AppsFolder\Paz.InvoiceToolbox_nz3s6nt1g6k06!App` 启动验证，`InvoiceToolbox.WinUI` 和 `InvoiceToolbox.Worker` 进程均已出现。
  - 2026-07-14 追加 `1.0.0.55` UI 小修：图标主体进一步放大，接近桌面图标占比；左侧栏折叠按钮跨列居中；当前选中行改为蓝色系，和待审核粉红区分。
  - `1.0.0.55` 已安装成功：`Get-AppxPackage -Name Paz.InvoiceToolbox` 返回 `Version 1.0.0.55`、`Status Ok`。
  - `1.0.0.55` 桌面安装目录：`C:\Users\paz\Desktop\invoice-toolbox-1.0.0.55-installer`
  - `1.0.0.55` 桌面安装包：`C:\Users\paz\Desktop\invoice-toolbox-1.0.0.55-installer\InvoiceToolbox.WinUI_1.0.0.55_x64.msix`
  - `1.0.0.55` 桌面安装包 sha256：`7B04A6BBB485497A0C2464AF4B161220FF2217B753B17A5B85C9D17DE6776D8D`
  - 已启动验证，`InvoiceToolbox.WinUI` 和 `InvoiceToolbox.Worker` 进程均已出现。
  - 2026-07-14 追加 `1.0.0.56` 修复：任务栏/标题栏图标重新生成，粉色圆角主体扩大到接近完整画布；右侧 `人工核对` 关闭按钮改为固定方形按钮；照片类发票 OCR 改为快速单轮识别，图片预处理最大边从 2200 降到 1600；照片类发票金额公式不一致时清空可疑金额/税率字段并标待确认；PDF 金额公式容差放宽到 `0.05`，减少高素质 PDF 因四舍五入误差被错误打成待确认；单元测试增至 44 项并全部通过。
  - `1.0.0.56` 已安装成功：`Get-AppxPackage -Name Paz.InvoiceToolbox` 返回 `Version 1.0.0.56`、`Status Ok`。
  - `1.0.0.56` 桌面安装目录：`C:\Users\paz\Desktop\invoice-toolbox-1.0.0.56-installer`
  - `1.0.0.56` 桌面安装包：`C:\Users\paz\Desktop\invoice-toolbox-1.0.0.56-installer\InvoiceToolbox.WinUI_1.0.0.56_x64.msix`
  - `1.0.0.56` 桌面安装包 sha256：`D8341A1616348F8B56444C76669B95D1CCAA96DA71EA1DFB3F4A58209E68DC97`
  - 已启动验证，`InvoiceToolbox.WinUI` 和 `InvoiceToolbox.Worker` 进程均已出现。
  - 2026-07-14 追加 `1.0.0.57` 识别可靠性修复：先诊断桌面 `发票` 75 张真实样本，确认 `39` 个待确认主要来自 PDF 金额列被旧逻辑猜错；改为 PDF 文本层按坐标读取不含税金额、税额、价税合计、税率，避免把价税合计误当不含税金额；金额公式最终仍不一致时，不分 PDF/图片都清空可疑金额/税率并标待确认，不再保留错数。
  - 源码诊断结果：75 张样本从 `39` 个待确认降到 `14` 个待确认，其中 `11` 个是 JPG 难图，`3` 个是 PDF（两张文本层/金额字符不稳，一张非常规格式），普通高素质 PDF 大批误待确认已解决。
  - 单元测试增至 45 项并全部通过。
  - `1.0.0.57` 已安装成功：`Get-AppxPackage -Name Paz.InvoiceToolbox` 返回 `Version 1.0.0.57`、`Status Ok`。
  - `1.0.0.57` 桌面安装目录：`C:\Users\paz\Desktop\invoice-toolbox-1.0.0.57-installer`
  - `1.0.0.57` 桌面安装包：`C:\Users\paz\Desktop\invoice-toolbox-1.0.0.57-installer\InvoiceToolbox.WinUI_1.0.0.57_x64.msix`
  - `1.0.0.57` 桌面安装包 sha256：`E4BAC1FBD59D8A637E04D411BCBDCD21D890EF954E3E997D485300896D5BDA1A`
  - 已启动验证，`InvoiceToolbox.WinUI` 和 `InvoiceToolbox.Worker` 进程均已出现。
  - 2026-07-14 追加 `1.0.0.58` 识别可靠性和扫描稳定性修复：桌面 `3` 文件夹 88 张高品质 PDF 之前出现识别失败/误待确认，定位为 WinUI 开始扫描复用了预览常驻 worker，批量扫描改为独立一次性 worker，避免 warm worker 状态干扰；同时补充 PDF 坐标金额抽取的紧凑版和低位汇总版布局，修复 `享道出行` 这类高品质 PDF 不含税金额、税额、价税合计位置不同导致的误待确认。
  - `1.0.0.58` 还修复 PDF 金额复查误伤：PDF 若不含税金额 + 税额 = 价税合计已经自洽，不再因为税率反推差异把普通高品质 PDF 打成待确认；图片类仍保持严格公式校验。
  - 验证结果：`C:\Users\paz\Desktop\3` 共 88 张 PDF，当前源码扫描结果 `pending 0`。
  - 验证结果：旧 `C:\Users\paz\Desktop\发票` 共 75 张，当前源码扫描结果 `pending 13`，其中 11 张 JPG 难图、2 张真正问题 PDF；普通高品质 PDF 误待确认已清掉。
  - 单元测试增至 46 项并全部通过。
  - `1.0.0.58` 已安装成功：`Get-AppxPackage -Name Paz.InvoiceToolbox` 返回 `Version 1.0.0.58`、`Status Ok`。
  - `1.0.0.58` 桌面安装目录：`C:\Users\paz\Desktop\invoice-toolbox-1.0.0.58-installer`
  - `1.0.0.58` 桌面安装包：`C:\Users\paz\Desktop\invoice-toolbox-1.0.0.58-installer\InvoiceToolbox.WinUI_1.0.0.58_x64.msix`
  - `1.0.0.58` 桌面安装包 sha256：`95A9D83D69A62FBDA749BA953F6EEE990CAB8444E29875692DDC621040C9BA8C`
  - 已启动验证，`InvoiceToolbox.WinUI` 和 `InvoiceToolbox.Worker` 进程均已出现。
  - 2026-07-14 追加 `1.0.0.60` 前端协议稳定性和重复显示修复：用户连续扫描桌面 `3` 文件夹时，88 张高品质 PDF 偶发在第 4、7、16 张报 `识别失败：'M' is an invalid start...`，根因是 worker 输出里偶尔混入 `MuPDF...` 这类非 JSON 诊断文本，WinUI 前端原来直接 `JsonNode.Parse(line)`，任何杂音都会打断整批扫描。现已改为只解析 `{...}` 开头且合法的 JSON 行，非 JSON 输出自动跳过；同时提前读取 stderr，避免后台错误输出堵塞进程。
  - `1.0.0.60` 还调整了重复发票显示：重复条目保留在上一条相邻位置，下方重复条目的字段文字改为红色加粗，背景不使用待确认粉色，避免和待确认混淆；尾部源文件、归档、审核状态也跟随红色，状态显示为“重复”。
  - `1.0.0.60` 已安装成功：`Get-AppxPackage -Name Paz.InvoiceToolbox` 返回 `Version 1.0.0.60`、`Status Ok`。
  - `1.0.0.60` 桌面安装目录：`C:\Users\paz\Desktop\invoice-toolbox-1.0.0.60-installer`
  - `1.0.0.60` 桌面安装包：`C:\Users\paz\Desktop\invoice-toolbox-1.0.0.60-installer\InvoiceToolbox.WinUI_1.0.0.60_x64.msix`
  - `1.0.0.60` 桌面安装包 sha256：`B66F701E1393D3EF32F4A65F55CFA20C2E5DA006DD95A09F919FC2AE4E6F5DC9`
  - `1.0.0.60` 验证：46 项 Python 单元测试通过；WinUI Release 编译通过；MSIX 签名校验通过；本机安装成功；应用启动后 `InvoiceToolbox.WinUI` 和 `InvoiceToolbox.Worker` 进程均出现。
- WinUI 3 软件已经成型，但仍有 UI、图标、OCR 可靠性、更新发布链路问题。
- 本地源码版本已升到 `1.0.0.60`，本机已安装 `1.0.0.60`；线上 latest 仍停在 `1.0.0.52`。
- 本地网站清单 `C:\Users\paz\toolbox-work\server\frontend\invoice-toolbox-latest.json` 写的是 `1.0.0.52`。
- 线上网站之前仍返回旧版本，导致用户当前安装的 `1.0.0.50` 看不到更新。
- MSIX 包体积约 213 MB，不能只依靠普通 git 提交；需要明确线上下载包托管方式。

已知本地包：

- `C:\Users\paz\toolbox-work\invoice-toolbox\winui_app\AppPackages\InvoiceToolbox.WinUI_1.0.0.52_x64_Test\InvoiceToolbox.WinUI_1.0.0.52_x64.msix`
- `C:\Users\paz\Desktop\invoice-toolbox-1.0.0.52-installer\InvoiceToolbox.WinUI_1.0.0.52_x64.msix`
- `C:\Users\paz\Desktop\invoice-toolbox-1.0.0.52-installer\install_admin.cmd`

安装坑：

- MSIX 签名证书只导入 CurrentUser 不够，部署时可能仍报 `0x800B0109`。
- 需要用管理员权限导入到 LocalMachine `Root` 和 `TrustedPeople`。
- 中文路径下安装脚本容易出现路径问题，已经改用英文安装目录：
  `C:\Users\paz\Desktop\invoice-toolbox-1.0.0.52-installer`
- 如果安装失败，先看：
  `C:\Users\paz\Desktop\invoice-toolbox-1.0.0.52-installer\install.log`

## 重要准则

1. 不要再回到网页壳。
   这是 WinUI 3 原生桌面软件，网页版本只作为视觉参考。

2. 不要为了“看起来识别成功”硬猜字段。
   能确定就填，不能确定就醒目标待审核。错误填入比空着更危险。

3. 正常 PDF 发票不应该大量待审核。
   如果字段完整、公式一致、税号格式合理，就不要因为补全来源而误进待审核。

4. 高难度照片可以待审核。
   用户已经接受高难度、歪斜、摩尔纹、拍屏、纸质照片 OCR 不完美。不要为了少数难图反复 OCR 卡几分钟。

5. 表格中任何关键字段缺失都必须进入待审核。
   不能出现“表格有空格，但统计只显示 1 张待确认”的情况。

6. 待审核必须醒目。
   不能只在最后一列小字显示。整行要有明显颜色，用户不用拖到最后也能发现。

7. UI 优先级不能低。
   用户非常在意质感：字体、图标、按钮按压、hover、深色浅色一致性、窗口比例、布局裁剪，都要当成产品问题处理。

8. 发布必须闭环。
   不要只说“本地包好了”。要确认：本地包、安装脚本、网站版本清单、下载包、版本号、交接文档都同步。

9. 不要长时间停下等用户。
   用户明确说过：只要还能自行完成，就继续实现、测试、修复和打包。只有必须用户选择方向、提供文件/权限、或遇到外部阻塞才停。

## 已踩过的坑

### 1. 网页版本 vs 原生版本

早期做成网页，用户担心端口占用、普通用户打不开。后来转向原生 UI。  
准则：不要再交付依赖浏览器端口的使用方式。

### 2. 老式 UI 被用户强烈否定

WinForms/Tk 风格过老，用户认为“粗糙、复古、像旧软件”。  
准则：坚持 WinUI 3，视觉接近办公工具箱网站和用户给的发票管家参考图。

### 3. 右侧人工核对栏不是常驻逻辑问题

左侧栏常驻，右侧人工核对栏应该可呼出/收起。  
点选发票条目时，如果右侧栏隐藏，应自动打开。

### 4. 文件夹选择必须真能用

网页版本最早选择按钮点不动，因为浏览器无本地文件夹权限。  
原生版必须使用 Windows 文件夹选择器。

### 5. 发票文件夹必须递归扫描

用户发现只扫了一层文件夹，子文件夹里的发票没读。  
准则：发票输入目录必须递归扫描 PDF 和图片。

### 6. 识别进度不能假死

用户多次反馈开始识别后等待几秒、进度条卡住、突然跳数。  
准则：点击开始后 UI 立刻反馈；枚举文件、预热 OCR、识别、复查都要有阶段文字和数字。

### 7. 识别完成后不能卡 3 到 5 秒

结束阶段一致性复查、重复判断、写归档状态可能卡 UI。  
准则：结束复查必须后台执行或分阶段提示，不能让界面像死掉。

### 8. 高难度照片不能拖累整个批次

歪斜、拍屏、摩尔纹、纸质照片会导致 OCR 慢。  
准则：限制增强候选和 OCR 尝试次数。超过阈值就待审核，不要卡几分钟。

### 9. OCR 前缀污染

出现过 `称：江西省勘察设计研究院有限公司`、`桥：`、`社：` 这类前缀污染。  
准则：公司名字段需清理常见 OCR 垃圾前缀；清理后仍异常则待审核。

### 10. 买方/销方反写

曾多次把销售方写进公司抬头。  
准则：公司抬头等于购买方名称，不是销售方。字段命名必须明确：

- `buyer_name` / 公司抬头 / 购买方名称
- `buyer_tax` / 购买方税号
- `seller_name` / 销售方名称
- `seller_tax` / 销售方税号

### 11. 正常 PDF 误进待审核

同批次补全字段后，正常 PDF 曾被误判待审核。  
准则：如果 PDF 字段完整、同批次补全可靠、公式一致，不要待审核。

### 12. 字段空缺被隐藏

曾出现表格里有空白字段，但待审核计数没有增加。  
准则：任何关键字段空缺或公式冲突都必须计入待审核。

### 13. 金额统计和重复跳过口径混乱

本软件总数包括重复，另一个深色软件显示“已识别 + 重复跳过 + 识别失败 = 总数”。金额也可能因为重复是否计入而不同。  
准则：统计口径必须明确：

- 总文件：扫描到的全部文件。
- 已识别：非重复且成功进入表格的发票。
- 待确认：字段缺失、公式冲突、低置信度。
- 重复跳过：重复文件或重复发票，不计入有效金额。
- 识别失败：无法解析。
- 价税合计/已识别金额：建议默认只统计非重复、非失败记录。

### 14. 重复文件归档

用户希望重复发票不要消失。  
准则：归档时应有 `重复` 文件夹，重复文件单独放进去，便于追查。

### 15. 导出归档设置逻辑

侧边栏不应常驻归档规则。  
导出时弹出高级设置：

- 左侧：文件重命名规则，勾选表示启用该字段，上下拖动表示命名顺序。
- 右侧：Excel 导出列，勾选表示导出该列，上下拖动表示列顺序。
- 不是用勾选先后顺序决定顺序。

### 16. 发票类型和业务分类下拉太窄

空值时下拉框太短。  
准则：即使未选择，也保持合理宽度。

### 17. 业务分类应该可维护

临时加号只能加一次不够。  
准则：业务分类应支持用户添加、删除、保存预设。默认可有：

- 办公用品
- 技术服务
- 差旅交通
- 硬件设备

### 18. 表格列宽

用户希望像 Excel 一样拖动列宽。  
准则：表头和内容列宽必须同步移动，表头分隔线要引导用户可拖动，不能表头先动、内容后动。

### 19. 右侧预览

预览图必须支持：

- 滚轮缩放
- 拖动平移
- 原大小
- 适应窗口
- 左旋
- 右旋

图像放大不能遮住工具按钮。拖拽延迟不能明显。

### 20. 图标问题

任务栏图标之前出现方形蓝底，后来蓝底可能消失，但图标质量仍低。  
准则：不能只拉伸小图。需要高质量透明底多尺寸资源：

- 16
- 24
- 32
- 44
- 48
- 64
- 256

同时检查：

- `StoreLogo.png`
- `Square44x44Logo.png`
- `Square44x44Logo.targetsize-*.png`
- `Square44x44Logo.targetsize-*_altform-unplated.png`
- `Square150x150Logo.png`
- tile assets
- `Package.appxmanifest`

### 21. 标题栏和收起按钮裁剪

用户截图显示左上角 logo/标题、侧栏收起按钮被遮住一半。  
准则：不要让父容器裁剪图标；折叠状态也要完整显示。

### 22. 深色浅色切换不同步

曾出现主界面先变色，表格和下方信息延迟变色。  
准则：主题切换应一次性同步更新资源，不要局部延迟。

### 23. 更新按钮

用户不要弹窗骚扰。  
准则：

- 软件启动联网读取网站版本。
- 如果网站版本高于本地，在左侧顶部显示“更新”和“忽略”。
- 更新按钮粉色，只写“更新”，不要显示长版本号。
- 忽略按钮普通白色。
- 点忽略后本次隐藏，下次启动再出现。
- 不理会也不影响使用。
- 点更新后展示中文更新内容卡片，不能用英文丑弹窗。

### 24. 网站下载页

用户嫌之前展示图太假、像幼稚园。  
准则：发票工具箱官网页要用接近真实桌面软件的大幅产品展示图，可编假数据，但 UI 必须像真实软件；发票图片可模糊保护隐私。下载按钮加好看的 Windows 11 风格图标。

### 25. 网站导航

办公工具箱首页可以有功能区跳转。  
但发票工具箱页、关于我们、意见反馈、隐私政策、用户协议、免责声明等页面顶部不应出现不完整的功能跳转链接。

### 26. 关于我们

关于我们页面需要写网站版本号和版本日期。  
版权排版要和网站风格一致，不要复古卡片。  
办公工具箱文字/发票工具箱文字要参考网站 logo 字体风格。

### 27. 编码坑

PowerShell 直接 `Get-Content` 有时会把中文 JSON 显示成乱码。  
准则：检查中文文件时明确按 UTF-8 读取/写入；不要因为 PowerShell 显示乱码就误判文件内容。

## 当前最重要的未完成任务

### A. OCR 可靠性和待审核逻辑

必须做：

1. 增加字段完整性校验。
   关键字段缺失即待审核：
   - 公司抬头/购买方名称
   - 购买方税号
   - 销售方名称
   - 销售方税号
   - 开票日期
   - 不含税金额
   - 税额
   - 价税合计
   - 税率
   - 发票类型
   - 发票号码

2. 增加金额公式校验。
   - `不含税金额 + 税额 ≈ 价税合计`
   - `不含税金额 × 税率 ≈ 税额`
   - `价税合计 / (1 + 税率) ≈ 不含税金额`
   - 允许小数误差，例如 0.02 元以内。

3. 增加税率合法性校验。
   常见税率：`1%`、`3%`、`5%`、`6%`、`9%`、`13%`。  
   其他税率不一定错，但需要更谨慎。

4. 增加税号格式校验。
   统一社会信用代码/税号长度和字符应合理。明显不合理就待审核。

5. 高难度图片策略。
   不要为了补全字段反复 OCR 几分钟。  
   可尝试有限增强，失败就待审核。  
   用户接受难图人工审核。

6. OCR 清洗。
   清理公司名开头的 `称：`、`社：`、`桥：`、`名：`、`名称：` 等污染。

7. 不要把低置信度补全结果直接变成已确认。
   批量一致性补全只能用于高置信字段；否则标待审核。

8. 待审核整行高亮。
   用户不能靠拖到最后一列看“待确认”。

### B. UI 立刻修复

1. 修左上角标题/图标被裁剪。
2. 修折叠侧边栏按钮被遮住一半。
3. 重做高质量任务栏图标资源。
4. 统一导出按钮高度，不要为了突出做成不等高。
5. 开始识别、保存按钮增加 hover/pressed 按压反馈。
6. 主题按钮改成太阳/月亮并排的办公工具箱风格，不要单个奇怪图标。
7. 深浅色切换同步。
8. 右侧人工核对栏缩小窗口时必须可滚动。
9. 预览图放大不能盖住按钮。
10. 旋转/垃圾桶等图标不能显示残缺。
11. 表头分隔线和内容列分隔线对齐，并保留拖拽列宽能力。
12. 顶部标题栏高度减少，避免占用过多纵向空间。
13. 左侧折叠按钮放到左侧栏逻辑位置；标题栏可放 logo。

### C. 更新发布链路

目标：

- 本地软件版本低于网站版本时显示更新按钮。
- 用户点击更新后下载 MSIX。
- 不弹强制弹窗，不打扰。
- 忽略只在本次启动隐藏。

必须完成：

1. 决定 MSIX 托管方式。
   可选：
   - 网站服务器静态文件：`/downloads/InvoiceToolbox.WinUI_latest.msix`
   - GitHub Release 资产
   - 其他对象存储

2. 保证线上 `https://www.bangong02.com/invoice-toolbox-latest.json` 指向最新版本。

3. JSON 字段建议：

```json
{
  "product": "发票工具箱",
  "appId": "Paz.InvoiceToolbox",
  "version": "1.0.0.52",
  "releaseDate": "2026-07-14",
  "build": "2026.07.14.1",
  "downloadUrl": "https://www.bangong02.com/downloads/InvoiceToolbox.WinUI_latest.msix",
  "size": 213471219,
  "sha256": "17959a400cae3f98c9e645d999f00faa252585049e98c204a762dc84c226fd76",
  "mandatory": false,
  "notes": [
    "修复正常 PDF 误进待审核的问题",
    "优化高难度照片识别策略",
    "补齐任务栏图标资源",
    "优化更新按钮显示"
  ]
}
```

4. 软件端下载后必须校验 sha256。
5. 下载完成后可以提示“下次打开时更新”或引导用户打开安装包。
6. 如果无法自动静默安装，不要伪装成能自动完成。MSIX/Windows 安全机制可能需要用户确认。

### D. 网站

1. 发票工具箱下载页使用真实感产品展示图。
2. 展示图可以用假数据，但界面必须像软件真实 UI。
3. 右侧发票图可模糊，避免隐私。
4. 可做大幅展示区、堆叠卡片、轮播点，效果要现代。
5. 下载按钮使用 Windows 11 风格图标。
6. 移除子页面顶部不合逻辑的功能跳转链接。
7. 关于我们加入网站版本号、版本日期、最新版下载提示。
8. 更新 `C:\Users\paz\Desktop\办公工具箱\交接文档` 中的新版本交接文档，建议写 `工作交接文档_v13_完整版.md`，不要只写增量。

### E. 安装包和旧文件

用户问过旧文件能否删除：

可以删除或移到待删除区的旧快照：

- `C:\Users\paz\Desktop\invoice-toolbox-project-fixed`
- `C:\Users\paz\Desktop\invoice-toolbox-project-fixed2`
- `C:\Users\paz\Desktop\发票工具箱\发票工具箱_交接包_20260710\winui_app\AppPackages` 中 v45 以前早期包

建议先移动到一个待删除文件夹，不要直接永久删除：

- `C:\Users\paz\Desktop\发票工具箱\可删除旧版本_20260714`

不要删除：

- `C:\Users\paz\toolbox-work`
- `C:\Users\paz\toolbox-work\invoice-toolbox`
- `C:\Users\paz\toolbox-work\server\frontend`
- `C:\Users\paz\Desktop\办公工具箱\交接文档`
- 当前安装器目录：`C:\Users\paz\Desktop\invoice-toolbox-1.0.0.52-installer`
- 测试发票目录：`C:\Users\paz\Desktop\111`、`发票文件夹`、`发票归档文件夹`

## 文件和目录索引

主项目：

- `C:\Users\paz\toolbox-work\invoice-toolbox`

WinUI：

- `C:\Users\paz\toolbox-work\invoice-toolbox\winui_app`
- `C:\Users\paz\toolbox-work\invoice-toolbox\winui_app\MainPage.xaml`
- `C:\Users\paz\toolbox-work\invoice-toolbox\winui_app\MainPage.xaml.cs`
- `C:\Users\paz\toolbox-work\invoice-toolbox\winui_app\Package.appxmanifest`
- `C:\Users\paz\toolbox-work\invoice-toolbox\winui_app\Assets`

OCR/后端：

- `C:\Users\paz\toolbox-work\invoice-toolbox\invoice_assistant\ocr.py`
- `C:\Users\paz\toolbox-work\invoice-toolbox\invoice_assistant\record_builder.py`
- `C:\Users\paz\toolbox-work\invoice-toolbox\native_worker.py`

测试：

- `C:\Users\paz\toolbox-work\invoice-toolbox\tests`

网站：

- `C:\Users\paz\toolbox-work\server\frontend`
- `C:\Users\paz\toolbox-work\server\frontend\invoice-toolbox.html`
- `C:\Users\paz\toolbox-work\server\frontend\invoice-toolbox-latest.json`
- `C:\Users\paz\toolbox-work\server\frontend\downloads\InvoiceToolbox.WinUI_latest.msix`
- `C:\Users\paz\toolbox-work\server\frontend\assets\invoice-toolbox`

交接文档：

- `C:\Users\paz\Desktop\办公工具箱\交接文档`
- 当前本文件：`C:\Users\paz\toolbox-work\invoice-toolbox\NEXT_SESSION_HANDOFF.md`

## 建议下一轮执行顺序

第一批：先修“不可靠会骗人”的问题。

1. 加待审核判定总规则：关键字段缺失、公式不一致、税号异常、低置信度都待审核。
2. 加金额/税率/税额/合计自校验。
3. 高难度图片限制 OCR 尝试次数，超时进人工审核。
4. 正常 PDF 若字段完整且公式一致，不误进待审核。
5. 跑 `Desktop\111` 和 `发票文件夹` 测试，对比待审核数量和空字段。

第二批：修 UI 硬伤。

1. 修左上角图标/标题裁剪。
2. 修折叠按钮遮挡。
3. 重做任务栏图标多尺寸资源。
4. 修深浅色同步。
5. 修表头分隔线和列宽拖动。
6. 修按钮 hover/pressed。
7. 修右侧预览工具栏遮挡和拖动延迟。

第三批：修发布。

1. 重新打包 MSIX。
2. 用管理员安装脚本验证本地安装。
3. 更新网站 JSON。
4. 确认 MSIX 线上托管。
5. 软件内更新按钮读取线上版本。

第四批：修网站。

1. 真实感发票工具箱展示图。
2. 删除子页面不合理顶部跳转。
3. 关于我们加入版本号。
4. 更新交接文档 v13。

## 推荐验证命令

检查安装版本：

```powershell
Get-AppxPackage -Name Paz.InvoiceToolbox | Select-Object Name, Version, Status, InstallLocation
```

检查线上更新清单：

```powershell
Invoke-WebRequest 'https://www.bangong02.com/invoice-toolbox-latest.json' -UseBasicParsing | Select-Object -ExpandProperty Content
```

运行 Python 测试：

```powershell
C:\Users\paz\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m unittest discover -s C:\Users\paz\toolbox-work\invoice-toolbox\tests
```

查看 git 状态：

```powershell
git -C C:\Users\paz\toolbox-work status --short
git -C C:\Users\paz\toolbox-work log -5 --oneline
```

检查 MSIX 签名：

```powershell
signtool verify /pa /v C:\Users\paz\Desktop\invoice-toolbox-1.0.0.60-installer\InvoiceToolbox.WinUI_1.0.0.60_x64.msix
```

安装脚本：

```powershell
C:\Users\paz\Desktop\invoice-toolbox-1.0.0.60-installer\install_admin.cmd
```

## 不要做的事

- 不要把网页版本当成最终产品。
- 不要只改截图上的一个像素问题而不验证真实窗口缩放。
- 不要为了减少待审核而把低置信度猜测写成已确认。
- 不要把销售方写成公司抬头。
- 不要只在最后一列显示待确认。
- 不要让用户手动猜哪些文件重复、哪些失败。
- 不要把版本号写得很长挤占侧边栏按钮。
- 不要做英文、复古、系统默认风格的更新弹窗和版权页。
- 不要声称“已更新云端”，除非线上 JSON 和线上 MSIX 都验证过。
- 不要把敏感 token、服务器密码、GitHub token 写进文档。

## 密钥、规则和敏感信息

当前没有在本文档中记录任何私密 key。后续如果需要部署网站或上传大文件，可能会涉及：

- GitHub token
- 服务器 SSH key
- 对象存储 key
- 网站部署凭据

规则：

1. 不要把这些 key 写进源码、交接文档或聊天总结。
2. 如果需要使用，优先读本机已有凭据或让用户在安全工具里登录。
3. 只记录“需要哪类权限”，不记录密钥本身。
4. 发布包的 sha256 可以写，这是校验信息，不是密钥。

当前更新包校验：

- size: `209919923`
- sha256: `B66F701E1393D3EF32F4A65F55CFA20C2E5DA006DD95A09F919FC2AE4E6F5DC9`

## 当前判断

最值得优先做的是“待审核可靠性”。  
因为用户已经接受高难度图片可能识别不出来，但不能接受软件把错的内容伪装成正确。  
所以 OCR 策略应从“尽量填满”改成“确定才填，不确定就明确交给人工”。

第二优先是 UI 裁剪和图标质量。  
这些不是技术难点，但最影响用户对软件专业度的第一印象。

第三优先是线上更新链路。  
本地包做好不等于用户能更新。必须让线上 JSON 和下载包同步，否则旧版软件不会显示正确更新。
