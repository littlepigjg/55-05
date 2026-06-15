from datetime import datetime
from typing import Optional, List, Dict
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox,
    QCheckBox, QDateEdit, QPushButton, QGroupBox, QListWidget,
    QListWidgetItem, QSpinBox, QFrame, QScrollArea
)
from PyQt6.QtCore import Qt, QDate, pyqtSignal
from PyQt6.QtGui import QIcon

from ..search.filter_assembler import (
    FilterAssembler,
    SelectedItemsTracker,
    AdvancedSearchCriteria,
    convert_mb_to_bytes,
)


class AdvancedSearchPanel(QWidget):
    search_requested = pyqtSignal(dict)
    reset_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._all_tags: List[str] = []
        self._all_formats: List[str] = []
        self._tag_tracker = SelectedItemsTracker()
        self._format_tracker = SelectedItemsTracker()
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = self._create_header()
        layout.addWidget(header)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(16, 12, 16, 16)
        content_layout.setSpacing(12)

        content_layout.addWidget(self._create_keyword_group())
        content_layout.addWidget(self._create_format_group())
        content_layout.addWidget(self._create_date_group())
        content_layout.addWidget(self._create_tags_group())
        content_layout.addWidget(self._create_size_group())
        content_layout.addStretch()

        scroll.setWidget(content)
        layout.addWidget(scroll, 1)

        button_row = self._create_button_row()
        layout.addWidget(button_row)

    def _create_header(self) -> QWidget:
        header = QFrame()
        header.setStyleSheet("""
            QFrame {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                padding: 16px;
            }
        """)
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(4)

        title = QLabel("🔍 高级搜索")
        title.setStyleSheet("color: white; font-size: 18px; font-weight: bold;")
        header_layout.addWidget(title)

        subtitle = QLabel("多维度组合筛选，精准定位所需书籍")
        subtitle.setStyleSheet("color: rgba(255,255,255,0.8); font-size: 13px;")
        header_layout.addWidget(subtitle)

        return header

    def _create_keyword_group(self) -> QGroupBox:
        group = QGroupBox("📝 关键词")
        group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                margin-top: 8px;
                padding-top: 12px;
                background: white;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 6px;
                color: #333;
            }
        """)

        layout = QVBoxLayout(group)
        layout.setSpacing(8)

        help_label = QLabel("支持语法: AND/OR/NOT, \"短语匹配\", 模糊~")
        help_label.setStyleSheet("color: #888; font-size: 12px;")
        layout.addWidget(help_label)

        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("书名中包含...")
        layout.addWidget(self.title_edit)

        self.author_edit = QLineEdit()
        self.author_edit.setPlaceholderText("作者中包含...")
        layout.addWidget(self.author_edit)

        self.publisher_edit = QLineEdit()
        self.publisher_edit.setPlaceholderText("出版社中包含...")
        layout.addWidget(self.publisher_edit)

        self.description_edit = QLineEdit()
        self.description_edit.setPlaceholderText("简介中包含...")
        layout.addWidget(self.description_edit)

        self.content_checkbox = QCheckBox("同时搜索正文内容")
        self.content_checkbox.setChecked(True)
        layout.addWidget(self.content_checkbox)

        return group

    def _create_format_group(self) -> QGroupBox:
        group = QGroupBox("📄 文件格式")
        group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                margin-top: 8px;
                padding-top: 12px;
                background: white;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 6px;
                color: #333;
            }
        """)

        layout = QVBoxLayout(group)
        layout.setSpacing(8)

        self.format_list = QListWidget()
        self.format_list.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        self.format_list.setStyleSheet("""
            QListWidget {
                border: 1px solid #e0e0e0;
                border-radius: 4px;
                padding: 4px;
                max-height: 100px;
            }
            QListWidget::item {
                padding: 4px 8px;
                border-radius: 3px;
            }
            QListWidget::item:selected {
                background: #4a9eff33;
                color: #000;
            }
        """)
        layout.addWidget(self.format_list)

        return group

    def _create_date_group(self) -> QGroupBox:
        group = QGroupBox("📅 出版日期")
        group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                margin-top: 8px;
                padding-top: 12px;
                background: white;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 6px;
                color: #333;
            }
        """)

        layout = QHBoxLayout(group)
        layout.setSpacing(8)

        self.date_from_checkbox = QCheckBox("从")
        self.date_from_checkbox.setChecked(False)
        layout.addWidget(self.date_from_checkbox)

        self.date_from = QDateEdit()
        self.date_from.setCalendarPopup(True)
        self.date_from.setDisplayFormat("yyyy-MM-dd")
        self.date_from.setDate(QDate(1990, 1, 1))
        self.date_from.setEnabled(False)
        self.date_from_checkbox.toggled.connect(self.date_from.setEnabled)
        layout.addWidget(self.date_from)

        layout.addWidget(QLabel("至"))

        self.date_to_checkbox = QCheckBox("")
        self.date_to_checkbox.setChecked(False)
        layout.addWidget(self.date_to_checkbox)

        self.date_to = QDateEdit()
        self.date_to.setCalendarPopup(True)
        self.date_to.setDisplayFormat("yyyy-MM-dd")
        self.date_to.setDate(QDate.currentDate())
        self.date_to.setEnabled(False)
        self.date_to_checkbox.toggled.connect(self.date_to.setEnabled)
        layout.addWidget(self.date_to)

        return group

    def _create_tags_group(self) -> QGroupBox:
        group = QGroupBox("🏷️ 标签")
        group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                margin-top: 8px;
                padding-top: 12px;
                background: white;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 6px;
                color: #333;
            }
        """)

        layout = QVBoxLayout(group)
        layout.setSpacing(8)

        tag_row = QHBoxLayout()
        self.tag_filter_edit = QLineEdit()
        self.tag_filter_edit.setPlaceholderText("筛选标签...")
        self.tag_filter_edit.textChanged.connect(self._filter_tags)
        tag_row.addWidget(self.tag_filter_edit, 1)

        select_all_btn = QPushButton("全选")
        select_all_btn.setStyleSheet("""
            QPushButton {
                padding: 4px 12px;
                border: 1px solid #ddd;
                border-radius: 4px;
                background: white;
            }
            QPushButton:hover {
                background: #f0f7ff;
                border-color: #4a9eff;
            }
        """)
        select_all_btn.clicked.connect(self._select_all_tags)
        tag_row.addWidget(select_all_btn)

        clear_btn = QPushButton("清空")
        clear_btn.setStyleSheet("""
            QPushButton {
                padding: 4px 12px;
                border: 1px solid #ddd;
                border-radius: 4px;
                background: white;
            }
            QPushButton:hover {
                background: #f0f7ff;
                border-color: #4a9eff;
            }
        """)
        clear_btn.clicked.connect(self._clear_tags)
        tag_row.addWidget(clear_btn)

        layout.addLayout(tag_row)

        self.tag_list = QListWidget()
        self.tag_list.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        self.tag_list.itemSelectionChanged.connect(self._update_tag_selection)
        self.tag_list.setStyleSheet("""
            QListWidget {
                border: 1px solid #e0e0e0;
                border-radius: 4px;
                padding: 4px;
                max-height: 120px;
            }
            QListWidget::item {
                padding: 4px 8px;
                border-radius: 3px;
            }
            QListWidget::item:selected {
                background: #fff3e0;
                color: #ef6c00;
            }
        """)
        layout.addWidget(self.tag_list)

        return group

    def _create_size_group(self) -> QGroupBox:
        group = QGroupBox("📦 文件大小 (MB)")
        group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                margin-top: 8px;
                padding-top: 12px;
                background: white;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 6px;
                color: #333;
            }
        """)

        layout = QHBoxLayout(group)
        layout.setSpacing(8)

        self.min_size_checkbox = QCheckBox("最小")
        self.min_size_checkbox.setChecked(False)
        layout.addWidget(self.min_size_checkbox)

        self.min_size = QSpinBox()
        self.min_size.setRange(0, 10000)
        self.min_size.setValue(0)
        self.min_size.setSuffix(" MB")
        self.min_size.setEnabled(False)
        self.min_size_checkbox.toggled.connect(self.min_size.setEnabled)
        layout.addWidget(self.min_size)

        layout.addWidget(QLabel("≤ 大小 ≤"))

        self.max_size_checkbox = QCheckBox("最大")
        self.max_size_checkbox.setChecked(False)
        layout.addWidget(self.max_size_checkbox)

        self.max_size = QSpinBox()
        self.max_size.setRange(0, 10000)
        self.max_size.setValue(1000)
        self.max_size.setSuffix(" MB")
        self.max_size.setEnabled(False)
        self.max_size_checkbox.toggled.connect(self.max_size.setEnabled)
        layout.addWidget(self.max_size)

        return group

    def _create_button_row(self) -> QWidget:
        widget = QWidget()
        widget.setStyleSheet("""
            QWidget {
                background: #f8f9fa;
                border-top: 1px solid #e0e0e0;
                padding: 12px 16px;
            }
        """)
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        layout.addStretch()

        reset_btn = QPushButton("🔄 重置")
        reset_btn.setStyleSheet("""
            QPushButton {
                padding: 8px 20px;
                border: 1px solid #ddd;
                border-radius: 6px;
                background: white;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #f5f5f5;
            }
        """)
        reset_btn.clicked.connect(self.reset)
        layout.addWidget(reset_btn)

        search_btn = QPushButton("🔍 开始搜索")
        search_btn.setStyleSheet("""
            QPushButton {
                padding: 8px 24px;
                border: none;
                border-radius: 6px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                font-weight: bold;
            }
            QPushButton:hover {
                background: linear-gradient(135deg, #5a6fd8 0%, #6a4190 100%);
            }
        """)
        search_btn.clicked.connect(self._on_search)
        layout.addWidget(search_btn)

        return widget

    def set_available_tags(self, tags: List[str]):
        self._all_tags = tags
        self._populate_tag_list(tags, preserve_selection=False)

    def set_available_formats(self, formats: List[str]):
        self._all_formats = formats
        self.format_list.clear()
        for fmt in formats:
            item = QListWidgetItem(fmt.upper())
            item.setData(Qt.ItemDataRole.UserRole, fmt)
            self.format_list.addItem(item)

    def _populate_tag_list(self, tags: List[str], preserve_selection: bool = True):
        if preserve_selection:
            self._save_tag_selection()

        self.tag_list.clear()
        for tag in tags:
            item = QListWidgetItem(f"🏷️  {tag}")
            item.setData(Qt.ItemDataRole.UserRole, tag)
            self.tag_list.addItem(item)

        if preserve_selection:
            self._restore_tag_selection()

    def _save_tag_selection(self):
        self._tag_tracker.save(self.tag_list)

    def _update_tag_selection(self):
        self._tag_tracker.update(self.tag_list)

    def _restore_tag_selection(self):
        self._tag_tracker.restore(self.tag_list)

    def _save_format_selection(self):
        self._format_tracker.save(self.format_list)

    def _update_format_selection(self):
        self._format_tracker.update(self.format_list)

    def _restore_format_selection(self):
        self._format_tracker.restore(self.format_list)

    def _filter_tags(self, text: str):
        text = text.lower()
        filtered = [t for t in self._all_tags if text in t.lower()]

        self.tag_list.clear()
        for tag in filtered:
            item = QListWidgetItem(f"🏷️  {tag}")
            item.setData(Qt.ItemDataRole.UserRole, tag)
            self.tag_list.addItem(item)

        self._restore_tag_selection()

    def _select_all_tags(self):
        for i in range(self.tag_list.count()):
            item = self.tag_list.item(i)
            item.setSelected(True)
        self._save_tag_selection()

    def _clear_tags(self):
        self._tag_tracker.clear()
        for i in range(self.tag_list.count()):
            item = self.tag_list.item(i)
            item.setSelected(False)

    def _on_search(self):
        filters = self.get_filters()
        self.search_requested.emit(filters)

    def reset(self):
        self.title_edit.clear()
        self.author_edit.clear()
        self.publisher_edit.clear()
        self.description_edit.clear()
        self.content_checkbox.setChecked(True)

        self.date_from_checkbox.setChecked(False)
        self.date_to_checkbox.setChecked(False)
        self.date_from.setDate(QDate(1990, 1, 1))
        self.date_to.setDate(QDate.currentDate())

        self.min_size_checkbox.setChecked(False)
        self.max_size_checkbox.setChecked(False)
        self.min_size.setValue(0)
        self.max_size.setValue(1000)

        self._tag_tracker.clear()
        self._format_tracker.clear()
        for i in range(self.format_list.count()):
            self.format_list.item(i).setSelected(False)
        for i in range(self.tag_list.count()):
            self.tag_list.item(i).setSelected(False)

        self.tag_filter_edit.clear()
        self._populate_tag_list(self._all_tags, preserve_selection=False)

        self.reset_requested.emit()

    def get_filters(self) -> Dict:
        self._save_tag_selection()
        self._save_format_selection()

        selected_formats = self._format_tracker.get_selected()
        selected_tags = self._tag_tracker.get_selected()

        date_start = FilterAssembler.parse_date_checkbox(
            self.date_from_checkbox, self.date_from
        )
        date_end = FilterAssembler.parse_date_checkbox(
            self.date_to_checkbox, self.date_to
        )
        min_size = FilterAssembler.parse_size_checkbox(
            self.min_size_checkbox, self.min_size
        )
        max_size = FilterAssembler.parse_size_checkbox(
            self.max_size_checkbox, self.max_size
        )

        return FilterAssembler.assemble_filters(
            title=self.title_edit.text(),
            author=self.author_edit.text(),
            publisher=self.publisher_edit.text(),
            description=self.description_edit.text(),
            search_content=self.content_checkbox.isChecked(),
            selected_formats=selected_formats,
            selected_tags=selected_tags,
            date_start=date_start,
            date_end=date_end,
            min_size=min_size,
            max_size=max_size,
        )

    def get_criteria(self) -> AdvancedSearchCriteria:
        self._save_tag_selection()
        self._save_format_selection()

        return FilterAssembler.assemble_criteria(
            title=self.title_edit.text(),
            author=self.author_edit.text(),
            publisher=self.publisher_edit.text(),
            description=self.description_edit.text(),
            search_content=self.content_checkbox.isChecked(),
            formats=self._format_tracker.get_selected(),
            tags=self._tag_tracker.get_selected(),
            date_start=FilterAssembler.parse_date_checkbox(
                self.date_from_checkbox, self.date_from
            ),
            date_end=FilterAssembler.parse_date_checkbox(
                self.date_to_checkbox, self.date_to
            ),
            min_size_bytes=FilterAssembler.parse_size_checkbox(
                self.min_size_checkbox, self.min_size
            ),
            max_size_bytes=FilterAssembler.parse_size_checkbox(
                self.max_size_checkbox, self.max_size
            ),
        )

    def get_selected_tags(self) -> List[str]:
        self._save_tag_selection()
        return self._tag_tracker.get_selected()

    def get_selected_formats(self) -> List[str]:
        self._save_format_selection()
        return self._format_tracker.get_selected()
