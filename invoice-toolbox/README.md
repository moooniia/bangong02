# 发票工具箱

办公工具箱出品的本地 PC 发票整理工具。

## 当前状态

- OCR 识别发票图片和 PDF。
- 不确定字段留空并标记 `待确认`，不乱填。
- 支持人工核对、保存修改、原图放大查看。
- 支持按年月、业务分类/年月、销售方/年月归档。
- 导出正式绿色 Excel 报表，保留原文件链接和归档文件链接。
- 使用原网页 UI 作为唯一视觉基准，保留左侧工具栏、主题切换、版本信息、人工核对和原图预览。
- 程序启动后自动打开本机窗口页面；识别、进度、复位和归档逻辑由本地后端提供。

## 本地运行

```bash
.venv/bin/python app.py
```

## 测试

```bash
.venv/bin/python -m unittest discover -s tests -v
```

## Windows 打包

打包说明见：

```text
build/pyinstaller/README.md
```
