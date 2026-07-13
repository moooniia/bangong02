from pathlib import Path

from PySide6.QtCore import QEasingCurve, QObject, QPoint, QPropertyAnimation, QThread, Qt, Signal
from PySide6.QtGui import QColor, QFont, QIcon, QImage, QPainter, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QDialog,
    QPushButton,
    QMessageBox,
    QProgressBar,
    QRadioButton,
    QScrollArea,
    QSizePolicy,
    QStyle,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from invoice_assistant.record_builder import scan_invoice_files
from invoice_assistant.archive import archive_records
from invoice_assistant.report_exporter import export_invoice_report


PINK = "#e94487"
BG = "#f8f8fa"
TEXT = "#202124"
MUTED = "#7b7f87"
BORDER = "#e5e5e8"


class StatTile(QFrame):
    def __init__(self, label, value, warning=False, parent=None):
        super().__init__(parent)
        self.setObjectName("statTile")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        caption = QLabel(label)
        caption.setObjectName("statCaption")
        number = QLabel(value)
        number.setObjectName("statWarning" if warning else "statNumber")
        self.value_label = number
        layout.addWidget(caption)
        layout.addWidget(number)


class TitleBar(QFrame):
    def __init__(self, window):
        super().__init__(window)
        self.window = window
        self.setObjectName("titleBar")
        self.drag_position = QPoint()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 0, 8, 0)
        layout.setSpacing(9)
        logo = QLabel()
        logo.setObjectName("titleLogo")
        logo.setPixmap(QPixmap(str(Path(__file__).resolve().parents[1] / "assets" / "icons" / "invoice-toolbox-icon-256.png")).scaled(22, 22, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        title = QLabel("发票工具箱")
        title.setObjectName("titleText")
        subtitle = QLabel("批量识别 · 归档 · 核对")
        subtitle.setObjectName("titleSubtitle")
        layout.addWidget(logo)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addStretch(1)
        for name, handler, standard_icon in (
            ("windowMinimize", window.showMinimized, QStyle.SP_TitleBarMinButton),
            ("windowMaximize", window.toggle_maximized, QStyle.SP_TitleBarMaxButton),
            ("windowClose", window.close, QStyle.SP_TitleBarCloseButton),
        ):
            button = QPushButton()
            button.setObjectName(name)
            button.setFixedSize(42, 34)
            button.setIcon(QApplication.style().standardIcon(standard_icon))
            button.clicked.connect(handler)
            layout.addWidget(button)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_position = event.globalPosition().toPoint() - self.window.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton and not self.window.isMaximized():
            self.window.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()


class ScanWorker(QObject):
    progress = Signal(int, int, object)
    finished = Signal(object)
    failed = Signal(str)

    def __init__(self, folder):
        super().__init__()
        self.folder = folder

    def run(self):
        try:
            records = scan_invoice_files(
                Path(self.folder),
                progress=lambda current, total, _path, record: self.progress.emit(current, total, record),
            )
            self.finished.emit(records)
        except Exception as exc:
            self.failed.emit(str(exc))


class PreviewCanvas(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.pixmap = QPixmap()
        self.scale = 1.0
        self.offset = QPoint()
        self.drag_start = QPoint()
        self.setMinimumHeight(190)
        self.setMouseTracking(True)

    def setPixmap(self, pixmap):
        self.pixmap = pixmap or QPixmap()
        self.fit_image()
        self.update()

    def clear(self):
        self.pixmap = QPixmap()
        self.update()

    def setText(self, text):
        self.placeholder = text
        self.update()

    def fit_image(self):
        if self.pixmap.isNull() or not self.width() or not self.height():
            return
        self.scale = min(
            self.width() / self.pixmap.width(),
            self.height() / self.pixmap.height(),
        ) * 0.92
        self.scale = max(0.05, min(self.scale, 8.0))
        self.offset = QPoint()

    def resizeEvent(self, event):
        self.fit_image()
        super().resizeEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#17181a"))
        if self.pixmap.isNull():
            painter.setPen(QColor("#9ba0a8"))
            painter.drawText(self.rect(), Qt.AlignCenter, getattr(self, "placeholder", "发票预览"))
            return
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        painter.translate(self.rect().center() + self.offset)
        painter.scale(self.scale, self.scale)
        painter.drawPixmap(-self.pixmap.width() // 2, -self.pixmap.height() // 2, self.pixmap)

    def wheelEvent(self, event):
        if self.pixmap.isNull():
            return
        self.scale *= 1.15 if event.angleDelta().y() > 0 else 0.87
        self.scale = max(0.05, min(self.scale, 8.0))
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_start = event.position().toPoint()
            self.setCursor(Qt.ClosedHandCursor)

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton:
            self.offset += event.position().toPoint() - self.drag_start
            self.drag_start = event.position().toPoint()
            self.update()

    def mouseReleaseEvent(self, event):
        self.unsetCursor()


class InvoiceWindow(QMainWindow):
    columns = [
        "公司抬头", "购买方税号", "销售方", "销售方税号", "开票日期",
        "不含税金额", "税额", "价税合计", "税率", "发票类型", "发票号码",
        "业务分类", "月份归档", "原文件", "归档文件",
    ]

    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)
        self.setWindowTitle("发票工具箱")
        self.resize(1440, 900)
        self.setMinimumSize(1120, 720)
        self.dark_mode = False
        self.setStyleSheet(self.styles())
        self.setCentralWidget(self.build_shell())
        self.records = []
        self.scan_thread = None
        self.scan_worker = None
        self.scan_done = False
        self.drawer_animation = QPropertyAnimation(self.drawer, b"maximumWidth", self)
        self.drawer_animation.setDuration(220)
        self.drawer_animation.setEasingCurve(QEasingCurve.OutCubic)
        self.drawer.setMaximumWidth(0)
        self.drawer.setMinimumWidth(0)
        self.drawer.setVisible(False)

    def build_shell(self):
        root = QWidget()
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)
        root_layout.addWidget(TitleBar(self))
        content = QWidget()
        content_layout = QHBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        self.sidebar = self.build_sidebar()
        content_layout.addWidget(self.sidebar)
        content_layout.addWidget(self.build_workspace(), 1)
        self.drawer = self.build_drawer()
        content_layout.addWidget(self.drawer)
        root_layout.addWidget(content, 1)
        return root

    def toggle_maximized(self):
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()

    def build_sidebar(self):
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setMinimumWidth(0)
        sidebar.setMaximumWidth(292)
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        brand = QHBoxLayout()
        mark = QLabel("▤")
        mark.setObjectName("brandMark")
        brand_text = QVBoxLayout()
        title = QLabel("发票工具箱")
        title.setObjectName("brandTitle")
        subtitle = QLabel("批量识别 · 归档 · 核对")
        subtitle.setObjectName("brandSubtitle")
        brand_text.addWidget(title)
        brand_text.addWidget(subtitle)
        brand.addLayout(brand_text)
        layout.addLayout(brand)

        layout.addWidget(self.path_card("发票文件夹", "点击右侧按钮选择", "input"))
        layout.addWidget(self.path_card("归档文件夹", "点击右侧按钮选择", "output"))

        archive = QFrame()
        archive.setObjectName("panel")
        archive_layout = QVBoxLayout(archive)
        archive_layout.setContentsMargins(12, 10, 12, 10)
        archive_layout.addWidget(QLabel("归档规则", objectName="panelTitle"))
        self.archive_mode = "month"
        self.archive_radios = {}
        for value, text in (("month", "按开票年月"), ("category_month", "按业务分类 / 年月"), ("seller_month", "按销售方 / 年月")):
            radio = QRadioButton(text)
            self.archive_radios[value] = radio
            radio.toggled.connect(lambda checked, mode=value: self.set_archive_mode(mode, checked))
            if value == "month":
                radio.setChecked(True)
            archive_layout.addWidget(radio)
        layout.addWidget(archive)

        stats = QWidget()
        stats_layout = QGridLayout(stats)
        stats_layout.setContentsMargins(0, 0, 0, 0)
        stats_layout.setSpacing(10)
        self.stat_tiles = {
            "total": StatTile("总文件", "0"),
            "confirmed": StatTile("已确认", "0"),
            "review": StatTile("待确认", "0", True),
            "duplicate": StatTile("重复跳过", "0"),
        }
        stats_layout.addWidget(self.stat_tiles["total"], 0, 0)
        stats_layout.addWidget(self.stat_tiles["confirmed"], 0, 1)
        stats_layout.addWidget(self.stat_tiles["review"], 1, 0)
        stats_layout.addWidget(self.stat_tiles["duplicate"], 1, 1)
        layout.addWidget(stats)

        total = QFrame()
        total.setObjectName("totalBox")
        total_layout = QVBoxLayout(total)
        total_layout.setContentsMargins(14, 11, 14, 11)
        total_layout.addWidget(QLabel("价税合计", objectName="statCaption"))
        self.total_amount_label = QLabel("¥0.00", objectName="totalAmount")
        total_layout.addWidget(self.total_amount_label)
        layout.addWidget(total)
        layout.addStretch(1)

        reset = QPushButton("重新开始")
        reset.setObjectName("resetButton")
        reset.setIcon(QApplication.style().standardIcon(QStyle.SP_BrowserReload))
        reset.clicked.connect(self.reset_task)
        self.reset_button = reset
        export = QPushButton("导出报表与归档")
        export.setObjectName("secondaryButton")
        export.setIcon(QApplication.style().standardIcon(QStyle.SP_DialogSaveButton))
        export.clicked.connect(self.export_and_archive)
        self.export_button = export
        scan = QPushButton("开始识别")
        scan.setObjectName("primaryButton")
        scan.setIcon(QApplication.style().standardIcon(QStyle.SP_MediaPlay))
        scan.clicked.connect(self.start_scan)
        self.scan_button = scan
        self.progress_bar = QProgressBar()
        self.progress_bar.setObjectName("scanProgress")
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("等待识别")
        layout.addWidget(self.progress_bar)
        layout.addWidget(export)
        layout.addWidget(reset)
        layout.addWidget(scan)
        return sidebar

    def path_card(self, title, path, kind):
        card = QFrame()
        card.setObjectName("pathCard")
        layout = QHBoxLayout(card)
        layout.setContentsMargins(12, 10, 10, 10)
        icon_label = QLabel()
        icon_label.setObjectName("pathIcon")
        icon_type = QStyle.SP_DirOpenIcon if kind == "input" else QStyle.SP_DriveHDIcon
        icon_label.setPixmap(QApplication.style().standardIcon(icon_type).pixmap(20, 20))
        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)
        text_layout.addWidget(QLabel(title, objectName="pathTitle"))
        path_label = QLabel(path, objectName="pathText")
        path_label.setWordWrap(True)
        self.path_labels = getattr(self, "path_labels", {})
        self.path_labels[kind] = path_label
        text_layout.addWidget(path_label)
        choose = QPushButton("选择")
        choose.setObjectName("chooseButton")
        choose.clicked.connect(lambda: self.choose_folder(kind))
        layout.addWidget(icon_label)
        layout.addLayout(text_layout, 1)
        layout.addWidget(choose)
        return card

    def set_archive_mode(self, mode, checked):
        if checked:
            self.archive_mode = mode

    def reset_task(self):
        if self.scan_thread and self.scan_thread.isRunning():
            QMessageBox.information(self, "正在识别", "请等待当前识别完成后再重新开始。")
            return
        self.records = []
        self.load_records([])
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("等待识别")
        self.preview_image.clear()
        self.preview_image.setText("发票预览")
        for editor in self.field_editors.values():
            editor.clear()

    def export_and_archive(self):
        if not self.records:
            QMessageBox.information(self, "暂无数据", "请先选择发票文件夹并完成识别。")
            return
        output_text = self.path_labels.get("output").text() if self.path_labels.get("output") else ""
        if not output_text or output_text == "点击右侧按钮选择":
            output_text = QFileDialog.getExistingDirectory(self, "选择归档文件夹")
            if not output_text:
                return
            self.path_labels["output"].setText(output_text)
        output_root = Path(output_text)
        try:
            archive_records(self.records, output_root, self.archive_mode)
            report_path = export_invoice_report(self.records, output_root / "发票整理报表.xlsx")
            self.load_records(self.records)
            QMessageBox.information(self, "处理完成", f"归档和报表已完成。\n{report_path}")
        except Exception as exc:
            QMessageBox.critical(self, "导出失败", str(exc))

    def choose_folder(self, kind):
        selected = QFileDialog.getExistingDirectory(self, "选择文件夹")
        if selected:
            self.path_labels[kind].setText(selected)

    def start_scan(self):
        folder_text = self.path_labels.get("input").text() if self.path_labels.get("input") else ""
        if not folder_text or folder_text == "点击右侧按钮选择":
            QMessageBox.warning(self, "无法开始识别", "请先选择发票文件夹。")
            return
        self.scan_button.setEnabled(False)
        self.scan_button.setText("识别中…")
        self.scan_done = False
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("准备识别")
        self.records = []
        self.load_records([])
        self.scan_thread = QThread(self)
        self.scan_worker = ScanWorker(folder_text)
        self.scan_worker.moveToThread(self.scan_thread)
        self.scan_thread.started.connect(self.scan_worker.run)
        self.scan_worker.progress.connect(self.on_scan_progress)
        self.scan_worker.finished.connect(self.on_scan_finished)
        self.scan_worker.failed.connect(self.on_scan_failed)
        self.scan_worker.finished.connect(self.scan_thread.quit)
        self.scan_worker.failed.connect(self.scan_thread.quit)
        self.scan_thread.finished.connect(self.scan_worker.deleteLater)
        self.scan_thread.finished.connect(self.on_scan_thread_finished)
        self.scan_thread.finished.connect(self.scan_thread.deleteLater)
        self.scan_thread.start()

    def on_scan_progress(self, current, total, record):
        self.records.append(record)
        percent = int(current * 100 / total) if total else 0
        self.progress_bar.setValue(percent)
        self.progress_bar.setFormat(f"正在识别 {current} / {total}")
        self.load_records(self.records)

    def on_scan_finished(self, records):
        self.records = list(records)
        self.load_records(self.records)
        self.progress_bar.setValue(100)
        self.progress_bar.setFormat(f"识别完成，共 {len(self.records)} 张")
        self.scan_button.setEnabled(True)
        self.scan_button.setText("▶  开始识别")
        self.scan_done = True

    def on_scan_failed(self, message):
        self.progress_bar.setFormat("识别失败")
        self.scan_button.setEnabled(True)
        self.scan_button.setText("▶  开始识别")
        self.scan_done = True
        QMessageBox.critical(self, "识别失败", message)

    def on_scan_thread_finished(self):
        self.scan_thread = None
        self.scan_worker = None

    def build_workspace(self):
        workspace = QWidget()
        layout = QVBoxLayout(workspace)
        layout.setContentsMargins(16, 16, 16, 0)
        layout.setSpacing(12)
        toolbar = QHBoxLayout()
        title = QLabel("●  发票明细  <span style='color:#8b8e95;font-size:13px'>未加载</span>")
        title.setObjectName("workspaceTitle")
        toolbar.addWidget(title)
        toolbar.addStretch(1)
        theme_button = self.toolbar_button("", "themeButton")
        theme_button.setToolTip("切换深浅色")
        theme_button.clicked.connect(self.toggle_theme)
        self.theme_button = theme_button
        toolbar.addWidget(theme_button)
        info_button = self.toolbar_button("", "infoButton")
        info_button.setToolTip("关于发票工具箱")
        info_button.clicked.connect(self.show_about)
        toolbar.addWidget(info_button)
        self.review_button = QPushButton("人工核对")
        self.review_button.setObjectName("secondaryButton")
        self.review_button.clicked.connect(self.toggle_drawer)
        toolbar.addWidget(self.review_button)
        layout.addLayout(toolbar)

        table = QTableWidget(0, len(self.columns))
        table.setHorizontalHeaderLabels(self.columns)
        table.setObjectName("invoiceTable")
        table.setAlternatingRowColors(True)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setHorizontalScrollMode(QTableWidget.ScrollPerPixel)
        table.setVerticalScrollMode(QTableWidget.ScrollPerPixel)
        table.horizontalHeader().setStretchLastSection(False)
        table.verticalHeader().setVisible(False)
        table.setShowGrid(True)
        table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        table.horizontalHeader().setDefaultSectionSize(120)
        self.table = table
        table.itemSelectionChanged.connect(self.on_table_selection_changed)
        layout.addWidget(table, 1)
        hint = QLabel("双击行可设置业务分类与修改数据    ·    点任意行打开核对面板")
        hint.setObjectName("hintbar")
        layout.addWidget(hint)
        return workspace

    def toggle_theme(self):
        self.dark_mode = not self.dark_mode
        self.setStyleSheet(self.styles(self.dark_mode))
        icon_type = QStyle.SP_TitleBarUnshadeButton if self.dark_mode else QStyle.SP_TitleBarShadeButton
        self.theme_button.setIcon(QApplication.style().standardIcon(icon_type))

    def show_about(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("关于发票工具箱")
        dialog.setWindowIcon(QIcon())
        dialog.setFixedSize(420, 280)
        dialog.setStyleSheet(self.styles(self.dark_mode) + "QDialog { border-radius: 14px; }")
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(30, 26, 30, 24)
        logo = QLabel()
        logo.setAlignment(Qt.AlignCenter)
        logo.setPixmap(QPixmap(str(Path(__file__).resolve().parents[1] / "assets" / "icons" / "invoice-toolbox-icon-256.png")).scaled(52, 52, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        title = QLabel("发票工具箱")
        title.setObjectName("aboutTitle")
        title.setAlignment(Qt.AlignCenter)
        version = QLabel("版本 1.0.0  ·  批量识别 · 归档 · 核对")
        version.setObjectName("aboutVersion")
        version.setAlignment(Qt.AlignCenter)
        company = QLabel("办公工具箱出品")
        company.setObjectName("aboutCompany")
        company.setAlignment(Qt.AlignCenter)
        close = QPushButton("关闭")
        close.setObjectName("primaryButton")
        close.clicked.connect(dialog.accept)
        layout.addWidget(logo)
        layout.addWidget(title)
        layout.addWidget(version)
        layout.addWidget(company)
        layout.addStretch(1)
        layout.addWidget(close)
        dialog.exec()

    def on_table_selection_changed(self):
        row = self.table.currentRow()
        if row < 0 or row >= len(self.records):
            return
        self.selected_record_index = row
        self.populate_drawer(self.records[row])
        if not self.drawer.isVisible() or self.drawer.maximumWidth() == 0:
            self.toggle_drawer()

    def populate_drawer(self, record):
        for field, editor in self.field_editors.items():
            editor.setText(str(getattr(record, field, "") or ""))
        self.preview_image.clear()
        self.preview_image.setText("发票预览")
        path = str(getattr(record, "original_path", "") or "")
        try:
            if path.lower().endswith(".pdf"):
                import fitz
                document = fitz.open(path)
                page = document.load_page(0)
                pixmap = page.get_pixmap(matrix=fitz.Matrix(1.4, 1.4), alpha=False)
                image = QImage(pixmap.samples, pixmap.width, pixmap.height, pixmap.stride, QImage.Format_RGB888).copy()
                document.close()
                self.preview_image.setPixmap(QPixmap.fromImage(image))
            elif path:
                self.preview_image.setPixmap(QPixmap(path))
            self.preview_image.setScaledContents(False)
        except Exception as exc:
            self.preview_image.setText(f"预览失败：{exc}")

    def save_drawer(self):
        index = getattr(self, "selected_record_index", -1)
        if index < 0 or index >= len(self.records):
            return
        record = self.records[index]
        for field, editor in self.field_editors.items():
            setattr(record, field, editor.text().strip())
        editable_review_fields = set(self.field_editors)
        record.fields_needing_review = {
            field for field in record.fields_needing_review
            if field in editable_review_fields and not getattr(record, field, "")
        }
        record.status = "需人工确认" if record.fields_needing_review else "已确认"
        self.load_records(self.records)
        self.table.selectRow(index)

    def load_records(self, records):
        """Render invoice records without coupling the UI to the OCR worker."""
        self.table.setRowCount(0)
        review_fields = {
            "buyer_name", "buyer_tax", "seller_name", "seller_tax", "invoice_date",
            "pretax_amount", "tax_amount", "total_amount", "tax_rate", "invoice_type",
        }
        field_order = [
            "buyer_name", "buyer_tax", "seller_name", "seller_tax", "invoice_date",
            "pretax_amount", "tax_amount", "total_amount", "tax_rate", "invoice_type",
            "invoice_no", "category", "invoice_date", "original_name", "archived_path",
        ]
        total = 0.0
        confirmed = 0
        for row, record in enumerate(records):
            self.table.insertRow(row)
            values = []
            needed = set(
                getattr(record, "fields_needing_review", set())
                if not isinstance(record, dict)
                else record.get("fields_needing_review", [])
            )
            for field in field_order:
                value = getattr(record, field, "") if not isinstance(record, dict) else record.get(field, "")
                values.append(str(value or ("（未归档）" if field == "archived_path" else "待确认" if field in review_fields else "")))
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                field = field_order[column]
                if field in needed or (field in review_fields and value == "待确认"):
                    item.setForeground(QColor("#c00000"))
                    item.setBackground(QColor("#fff2cc"))
                    item.setFont(QFont("Microsoft YaHei UI", 10, QFont.Bold))
                self.table.setItem(row, column, item)
            raw_total = getattr(record, "total_amount", "0") if not isinstance(record, dict) else record.get("total_amount", "0")
            try:
                total += float(str(raw_total).replace(",", ""))
            except (TypeError, ValueError):
                pass
            if not needed:
                confirmed += 1
        count = len(records)
        self.stat_tiles["total"].value_label.setText(str(count))
        self.stat_tiles["confirmed"].value_label.setText(str(confirmed))
        self.stat_tiles["review"].value_label.setText(str(count - confirmed))
        self.total_amount_label.setText(f"¥{total:,.2f}")

    def toggle_drawer(self):
        opening = not self.drawer.isVisible() or self.drawer.maximumWidth() == 0
        self.drawer_animation.stop()
        self.drawer.setVisible(True)
        self.drawer_animation.setStartValue(self.drawer.maximumWidth())
        if opening:
            self.drawer.setMinimumWidth(460)
        else:
            self.drawer.setMinimumWidth(0)
        self.drawer_animation.setEndValue(460 if opening else 0)
        if not opening:
            self.drawer_animation.finished.connect(self.hide_drawer_after_animation)
        else:
            self.review_button.setText("收起核对")
        self.drawer_animation.start()

    def hide_drawer_after_animation(self):
        try:
            self.drawer_animation.finished.disconnect(self.hide_drawer_after_animation)
        except RuntimeError:
            pass
        if self.drawer.maximumWidth() == 0:
            self.drawer.setVisible(False)
            self.review_button.setText("人工核对")

    def toolbar_button(self, text, name):
        button = QPushButton(text)
        button.setObjectName(name)
        button.setFixedSize(42, 42)
        icon_type = QStyle.SP_MessageBoxInformation if name == "infoButton" else QStyle.SP_TitleBarShadeButton
        button.setIcon(QApplication.style().standardIcon(icon_type))
        return button

    def build_drawer(self):
        drawer = QFrame()
        drawer.setObjectName("drawer")
        drawer.setMinimumWidth(0)
        drawer.setMaximumWidth(460)
        layout = QVBoxLayout(drawer)
        layout.setContentsMargins(16, 18, 16, 16)
        title = QLabel("人工核对")
        title.setObjectName("drawerTitle")
        layout.addWidget(title)
        layout.addWidget(QLabel("选择一张发票", objectName="pathText"))
        preview = QFrame()
        preview.setObjectName("previewCard")
        preview.setMinimumHeight(230)
        preview_layout = QVBoxLayout(preview)
        preview_layout.addStretch(1)
        self.preview_image = PreviewCanvas()
        self.preview_image.setObjectName("previewImage")
        preview_layout.addWidget(self.preview_image)
        preview_layout.addStretch(1)
        layout.addWidget(preview)
        fields = QScrollArea()
        fields.setWidgetResizable(True)
        fields.setFrameShape(QFrame.NoFrame)
        field_host = QWidget()
        field_layout = QVBoxLayout(field_host)
        self.field_editors = {}
        field_labels = {
            "buyer_name": "购买方抬头",
            "buyer_tax": "购买方税号",
            "seller_name": "销售方名称",
            "seller_tax": "销售方税号",
            "invoice_date": "开票日期",
            "pretax_amount": "不含税金额",
            "tax_amount": "税额",
            "total_amount": "价税合计",
            "tax_rate": "税率",
            "invoice_type": "发票类型",
            "invoice_no": "发票号码",
            "category": "业务分类",
        }
        for field, label in field_labels.items():
            field_layout.addWidget(QLabel(label, objectName="fieldLabel"))
            editor = QLineEdit()
            editor.setPlaceholderText("待确认")
            editor.setObjectName("reviewEditor")
            self.field_editors[field] = editor
            field_layout.addWidget(editor)
        field_layout.addStretch(1)
        fields.setWidget(field_host)
        layout.addWidget(fields, 1)
        save = QPushButton("✓  保存修改")
        save.setObjectName("primaryButton")
        save.clicked.connect(self.save_drawer)
        layout.addWidget(save)
        return drawer

    @staticmethod
    def styles(dark_mode=False):
        base = f"""
        QWidget {{ color: {TEXT}; font-family: 'Microsoft YaHei UI'; font-size: 13px; }}
        QMainWindow, QWidget {{ background: {BG}; }}
        #titleBar {{ background: #ffffff; border-bottom: 1px solid {BORDER}; }}
        #titleLogo {{ background: {PINK}; color: white; border-radius: 8px; font-size: 20px; min-width: 30px; min-height: 30px; max-width: 30px; max-height: 30px; qproperty-alignment: AlignCenter; }}
        #titleText {{ font-size: 15px; font-weight: 700; }}
        #titleSubtitle {{ color: {MUTED}; font-size: 12px; }}
        #windowMinimize, #windowMaximize, #windowClose {{ background: transparent; border: none; border-radius: 6px; font-size: 18px; }}
        #windowMinimize:hover, #windowMaximize:hover {{ background: #f0f0f2; }}
        #windowClose:hover {{ background: #e94487; color: white; }}
        #sidebar, #drawer {{ background: #ffffff; border: 1px solid {BORDER}; }}
        #brandMark {{ background: {PINK}; color: white; border-radius: 12px; font-size: 26px; min-width: 42px; min-height: 42px; max-width: 42px; max-height: 42px; qproperty-alignment: AlignCenter; }}
        #brandTitle {{ font-size: 18px; font-weight: 700; }}
        #toolbarLogo {{ background: {PINK}; color: white; border-radius: 10px; font-size: 22px; min-width: 38px; min-height: 38px; max-width: 38px; max-height: 38px; qproperty-alignment: AlignCenter; }}
        #brandSubtitle, #pathText, #statCaption, #hintbar, #fieldLabel {{ color: {MUTED}; }}
        #pathCard, #panel, #statTile, #totalBox {{ background: #f7f7f8; border: 1px solid {BORDER}; border-radius: 10px; }}
        #pathIcon {{ color: {PINK}; font-size: 22px; }}
        #pathTitle, #panelTitle {{ font-weight: 700; }}
        #chooseButton, #secondaryButton, #resetButton, #themeButton, #infoButton, #menuButton {{ background: #ffffff; border: 1px solid {BORDER}; border-radius: 8px; padding: 8px 12px; }}
        QPushButton:hover {{ border-color: {PINK}; color: {PINK}; }}
        #primaryButton {{ background: {PINK}; color: white; border: none; border-radius: 8px; padding: 11px; font-weight: 700; }}
        #primaryButton:hover {{ background: #d93677; }}
        #scanProgress {{ min-height: 18px; border: 1px solid {BORDER}; border-radius: 8px; background: #f1f1f3; text-align: center; }}
        #scanProgress::chunk {{ background: {PINK}; border-radius: 7px; }}
        #statNumber, #totalAmount {{ font-size: 22px; font-weight: 700; }}
        #statWarning {{ color: #c00000; font-size: 22px; font-weight: 700; }}
        #reviewValue {{ color: #c00000; font-size: 14px; font-weight: 700; }}
        #totalAmount {{ font-size: 24px; }}
        #workspaceTitle {{ font-size: 18px; font-weight: 700; }}
        #invoiceTable {{ background: #ffffff; border: 1px solid {BORDER}; gridline-color: {BORDER}; }}
        #invoiceTable QHeaderView::section {{ background: #222222; color: white; padding: 10px 8px; border: 0; font-weight: 700; }}
        #invoiceTable::item {{ padding: 7px; }}
        #invoiceTable::item:selected {{ background: #ffe9b8; color: {TEXT}; }}
        #previewCard {{ background: #f1f1f3; border: 1px solid {BORDER}; border-radius: 10px; }}
        #previewImage {{ color: {MUTED}; background: #f1f1f3; }}
        #drawerTitle {{ font-size: 20px; font-weight: 700; }}
        #reviewEditor {{ background: #ffffff; border: 1px solid {BORDER}; border-radius: 7px; padding: 8px 10px; min-height: 20px; }}
        #reviewEditor:focus {{ border: 1px solid {PINK}; }}
        #aboutTitle {{ font-size: 22px; font-weight: 700; color: {TEXT}; }}
        #aboutVersion, #aboutCompany {{ color: {MUTED}; }}
        #reviewValue {{ background: #fff2cc; border: 1px solid #f3d98d; border-radius: 7px; padding: 10px; }}
        QScrollBar:vertical {{ width: 10px; background: transparent; }}
        QScrollBar::handle:vertical {{ background: #c8c8cc; border-radius: 5px; min-height: 36px; }}
        QScrollBar:horizontal {{ height: 10px; background: transparent; }}
        QScrollBar::handle:horizontal {{ background: #c8c8cc; border-radius: 5px; min-width: 36px; }}
        """
        if not dark_mode:
            return base
        return base + f"""
        QMainWindow, QWidget {{ background: #202124; color: #f1f3f4; }}
        #titleBar, #sidebar, #drawer {{ background: #292a2d; border-color: #45464b; }}
        #titleText, #brandTitle, #drawerTitle, #workspaceTitle, #pathTitle, #panelTitle {{ color: #f1f3f4; }}
        #titleSubtitle, #brandSubtitle, #pathText, #statCaption, #hintbar, #fieldLabel {{ color: #aeb2ba; }}
        #pathCard, #panel, #statTile, #totalBox {{ background: #303136; border-color: #45464b; }}
        #invoiceTable, #reviewEditor {{ background: #292a2d; color: #f1f3f4; border-color: #45464b; alternate-background-color: #26282c; }}
        #invoiceTable::item {{ background: #2e3034; color: #f1f3f4; }}
        #invoiceTable::item:alternate {{ background: #26282c; color: #f1f3f4; }}
        #invoiceTable::item:selected {{ background: #5a4318; color: #ffffff; }}
        #previewCard {{ background: #17181a; border-color: #45464b; }}
        #chooseButton, #secondaryButton, #resetButton, #themeButton, #infoButton, #reviewEditor {{ background: #303136; color: #f1f3f4; border-color: #55575d; }}
        #reviewValue {{ background: #4a3919; }}
        #aboutTitle {{ font-size: 22px; font-weight: 700; color: #f1f3f4; }}
        #aboutVersion, #aboutCompany {{ color: #aeb2ba; }}
        """


def run():
    app = QApplication.instance() or QApplication([])
    app.setStyle("Fusion")
    window = InvoiceWindow()
    window.show()
    return app.exec()
