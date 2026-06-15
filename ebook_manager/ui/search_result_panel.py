import re
import html
from pathlib import Path
from typing import List, Dict, Optional
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QFrame, QScrollArea, QTextEdit, QPushButton, QSplitter, QStatusBar
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QFont, QColor, QTextCursor, QTextCharFormat, QBrush

from ..models import BookMeta


class SearchResultPanel(QWidget):
    result_selected = pyqtSignal(dict)
    result_double_clicked = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._results: List[Dict] = []
        self._query: str = ""
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = self._create_header()
        layout.addWidget(header)

        splitter = QSplitter(Qt.Orientation.Vertical)

        self.result_list = _ResultListWidget()
        self.result_list.itemSelectionChanged.connect(self._on_selection_changed)
        self.result_list.itemDoubleClicked.connect(self._on_double_clicked)
        splitter.addWidget(self.result_list)

        self.detail_panel = _DetailPanel()
        splitter.addWidget(self.detail_panel)

        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 1)
        layout.addWidget(splitter)

    def _create_header(self) -> QWidget:
        header = QFrame()
        header.setStyleSheet("""
            QFrame {
                background: #f8f9fa;
                border-bottom: 1px solid #e0e0e0;
                padding: 8px 12px;
            }
        """)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)

        self.count_label = QLabel("找到 0 个结果")
        self.count_label.setStyleSheet("color: #666; font-weight: bold;")
        header_layout.addWidget(self.count_label)

        header_layout.addStretch()

        self.query_label = QLabel("")
        self.query_label.setStyleSheet("color: #4a9eff;")
        header_layout.addWidget(self.query_label)

        return header

    def set_results(self, results: List[Dict], query: str = ""):
        self._results = results
        self._query = query
        self._populate_results()
        self.count_label.setText(f"找到 {len(results)} 个结果")
        if query:
            self.query_label.setText(f"搜索: \"{query}\"")
        else:
            self.query_label.setText("")

    def _populate_results(self):
        self.result_list.clear()
        self.detail_panel.clear()

        for i, result in enumerate(self._results):
            item = _ResultItem(result, self._query, i + 1)
            list_item = QListWidgetItem(self.result_list)
            list_item.setData(Qt.ItemDataRole.UserRole, result)
            list_item.setSizeHint(item.sizeHint())
            self.result_list.addItem(list_item)
            self.result_list.setItemWidget(list_item, item)

    def _on_selection_changed(self):
        items = self.result_list.selectedItems()
        if items:
            result = items[0].data(Qt.ItemDataRole.UserRole)
            self.detail_panel.set_result(result, self._query)
            self.result_selected.emit(result)

    def _on_double_clicked(self, item: QListWidgetItem):
        result = item.data(Qt.ItemDataRole.UserRole)
        self.result_double_clicked.emit(result)

    def clear(self):
        self._results = []
        self._query = ""
        self.result_list.clear()
        self.detail_panel.clear()
        self.count_label.setText("找到 0 个结果")
        self.query_label.setText("")

    def get_selected_result(self) -> Optional[Dict]:
        items = self.result_list.selectedItems()
        if items:
            return items[0].data(Qt.ItemDataRole.UserRole)
        return None


class _ResultListWidget(QListWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            QListWidget {
                border: none;
                background: white;
            }
            QListWidget::item {
                border-bottom: 1px solid #f0f0f0;
                padding: 0;
            }
            QListWidget::item:selected {
                background: #4a9eff11;
            }
            QListWidget::item:hover {
                background: #f5f5f5;
            }
        """)
        self.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self.setVerticalScrollMode(QListWidget.ScrollMode.ScrollPerPixel)
        self.verticalScrollBar().setSingleStep(20)


class _ResultItem(QFrame):
    def __init__(self, result: Dict, query: str, rank: int, parent=None):
        super().__init__(parent)
        self._result = result
        self._query = query
        self._rank = rank
        self._init_ui()

    def _init_ui(self):
        self.setStyleSheet("""
            QFrame {
                background: transparent;
                padding: 12px 16px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        title_row = QHBoxLayout()

        rank_label = QLabel(f"#{self._rank}")
        rank_label.setStyleSheet("""
            QLabel {
                background: #4a9eff;
                color: white;
                padding: 2px 8px;
                border-radius: 10px;
                font-weight: bold;
                font-size: 11px;
            }
        """)
        rank_label.setFixedHeight(20)
        title_row.addWidget(rank_label)

        title_text = self._highlight_text(self._result.get("title", "未知书名"), self._query)
        title_label = QLabel(title_text)
        title_label.setTextFormat(Qt.TextFormat.RichText)
        title_label.setStyleSheet("font-size: 15px; font-weight: bold; color: #222;")
        title_label.setWordWrap(True)
        title_row.addWidget(title_label, 1)

        score = self._result.get("score", 0)
        score_label = QLabel(f"相关度: {score:.2f}")
        score_label.setStyleSheet("color: #888; font-size: 12px;")
        title_row.addWidget(score_label)

        layout.addLayout(title_row)

        author = self._result.get("author", "")
        publisher = self._result.get("publisher", "")
        meta_parts = []
        if author:
            meta_parts.append(f"✍️ {self._highlight_text(author, self._query)}")
        if publisher:
            meta_parts.append(f"🏢 {publisher}")
        if meta_parts:
            meta_label = QLabel("  ".join(meta_parts))
            meta_label.setTextFormat(Qt.TextFormat.RichText)
            meta_label.setStyleSheet("color: #666; font-size: 12px;")
            layout.addWidget(meta_label)

        description = self._result.get("description", "")
        if description:
            snippet = self._get_snippet(description, self._query)
            if snippet:
                desc_label = QLabel(snippet)
                desc_label.setTextFormat(Qt.TextFormat.RichText)
                desc_label.setStyleSheet("color: #555; font-size: 13px;")
                desc_label.setWordWrap(True)
                layout.addWidget(desc_label)

        info_row = QHBoxLayout()
        file_format = self._result.get("file_format", "").upper()
        if file_format:
            format_label = QLabel(f"📄 {file_format}")
            format_label.setStyleSheet("""
                QLabel {
                    background: #e8f5e9;
                    color: #2e7d32;
                    padding: 2px 8px;
                    border-radius: 4px;
                    font-size: 11px;
                    font-weight: bold;
                }
            """)
            info_row.addWidget(format_label)

        publish_date = self._result.get("publish_date", "")
        if publish_date:
            date_label = QLabel(f"📅 {publish_date[:4]}")
            date_label.setStyleSheet("color: #888; font-size: 12px;")
            info_row.addWidget(date_label)

        tags = self._result.get("tags", "")
        if tags:
            tags = tags.split(",") if isinstance(tags, str) else tags
            for tag in tags[:3]:
                if tag.strip():
                    tag_label = QLabel(f"🏷️ {tag.strip()}")
                    tag_label.setStyleSheet("""
                        QLabel {
                            background: #fff3e0;
                            color: #ef6c00;
                            padding: 2px 6px;
                            border-radius: 8px;
                            font-size: 11px;
                        }
                    """)
                    info_row.addWidget(tag_label)

        info_row.addStretch()

        file_path = self._result.get("file_path", "")
        if file_path:
            path_label = QLabel(f"📁 {Path(file_path).name}")
            path_label.setStyleSheet("color: #aaa; font-size: 11px;")
            path_label.setToolTip(file_path)
            info_row.addWidget(path_label)

        layout.addLayout(info_row)

    def _highlight_text(self, text: str, query: str) -> str:
        if not query or not text:
            return html.escape(text)

        highlighted = html.escape(text)
        keywords = self._extract_keywords(query)

        for keyword in keywords:
            if keyword and len(keyword) >= 2:
                pattern = re.compile(re.escape(keyword), re.IGNORECASE)
                highlighted = pattern.sub(
                    lambda m: f'<span style="background: #fff59d; color: #d84315; padding: 0 2px; border-radius: 2px;">{m.group()}</span>',
                    highlighted
                )

        return highlighted

    def _extract_keywords(self, query: str) -> List[str]:
        query = re.sub(r'[~*"()]', ' ', query)
        query = re.sub(r'\b(AND|OR|NOT)\b', ' ', query, flags=re.IGNORECASE)
        keywords = [k.strip() for k in query.split() if k.strip()]
        return keywords

    def _get_snippet(self, text: str, query: str, max_len: int = 200) -> str:
        if not text:
            return ""

        text = text.strip()
        if len(text) <= max_len:
            return self._highlight_text(text, query)

        keywords = self._extract_keywords(query)
        best_pos = 0

        if keywords:
            text_lower = text.lower()
            for keyword in keywords:
                pos = text_lower.find(keyword.lower())
                if pos != -1:
                    best_pos = max(0, pos - 50)
                    break

        snippet = text[best_pos:best_pos + max_len]
        if best_pos > 0:
            snippet = "..." + snippet
        if best_pos + max_len < len(text):
            snippet = snippet + "..."

        return self._highlight_text(snippet, query)


class _DetailPanel(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        self.setStyleSheet("""
            QFrame {
                background: #fafafa;
                border-top: 1px solid #e0e0e0;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        header = QHBoxLayout()
        title = QLabel("📝 详细信息")
        title.setStyleSheet("font-weight: bold; font-size: 14px; color: #333;")
        header.addWidget(title)
        header.addStretch()
        layout.addLayout(header)

        self.detail_text = _HighlightTextEdit()
        self.detail_text.setReadOnly(True)
        self.detail_text.setStyleSheet("""
            QTextEdit {
                background: white;
                border: 1px solid #e0e0e0;
                border-radius: 6px;
                padding: 10px;
                font-size: 13px;
            }
        """)
        layout.addWidget(self.detail_text, 1)

    def set_result(self, result: Dict, query: str):
        self.detail_text.clear()
        self.detail_text.set_search_query(query)

        html_content = []

        title = result.get("title", "未知书名")
        html_content.append(f"<h2 style='color: #222; margin: 0 0 10px 0;'>{html.escape(title)}</h2>")

        author = result.get("author", "")
        if author:
            html_content.append(f"<p><b>作者:</b> {html.escape(author)}</p>")

        publisher = result.get("publisher", "")
        if publisher:
            html_content.append(f"<p><b>出版社:</b> {html.escape(publisher)}</p>")

        publish_date = result.get("publish_date", "")
        if publish_date:
            html_content.append(f"<p><b>出版日期:</b> {html.escape(publish_date)}</p>")

        isbn = result.get("isbn", "")
        if isbn:
            html_content.append(f"<p><b>ISBN:</b> {html.escape(isbn)}</p>")

        language = result.get("language", "")
        if language:
            html_content.append(f"<p><b>语言:</b> {html.escape(language)}</p>")

        file_format = result.get("file_format", "").upper()
        file_size = result.get("file_size", 0)
        if file_format:
            size_str = BookMeta.format_size(file_size) if file_size else "未知"
            html_content.append(f"<p><b>格式:</b> {html.escape(file_format)} ({size_str})</p>")

        tags = result.get("tags", "")
        if tags:
            tags = tags.split(",") if isinstance(tags, str) else tags
            tags_html = " ".join(
                f'<span style="background: #fff3e0; color: #ef6c00; padding: 2px 8px; border-radius: 10px; font-size: 12px;">🏷️ {html.escape(t.strip())}</span>'
                for t in tags if t.strip()
            )
            html_content.append(f"<p><b>标签:</b> {tags_html}</p>")

        description = result.get("description", "")
        if description:
            html_content.append(f"<h3 style='color: #444; margin: 15px 0 5px 0;'>简介</h3>")
            html_content.append(f"<p style='line-height: 1.6; color: #555;'>{html.escape(description)}</p>")

        file_path = result.get("file_path", "")
        if file_path:
            html_content.append(f"<h3 style='color: #444; margin: 15px 0 5px 0;'>文件路径</h3>")
            html_content.append(f"<p style='font-family: monospace; font-size: 12px; color: #666; word-break: break-all;'>{html.escape(file_path)}</p>")

        self.detail_text.setHtml("".join(html_content))
        self.detail_text.highlight_all()

    def clear(self):
        self.detail_text.clear()
        self.detail_text.setHtml("<p style='color: #888;'>选择搜索结果查看详细信息</p>")


class _HighlightTextEdit(QTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._query: str = ""
        self._highlight_format = QTextCharFormat()
        self._highlight_format.setBackground(QBrush(QColor("#fff59d")))
        self._highlight_format.setForeground(QBrush(QColor("#d84315")))

    def set_search_query(self, query: str):
        self._query = query

    def highlight_all(self):
        if not self._query:
            return

        keywords = self._extract_keywords(self._query)
        if not keywords:
            return

        doc = self.document()
        cursor = QTextCursor(doc)

        for keyword in keywords:
            if len(keyword) < 2:
                continue

            cursor = doc.find(keyword, 0)
            while not cursor.isNull():
                cursor.mergeCharFormat(self._highlight_format)
                cursor = doc.find(keyword, cursor)

    def _extract_keywords(self, query: str) -> List[str]:
        query = re.sub(r'[~*"()]', ' ', query)
        query = re.sub(r'\b(AND|OR|NOT)\b', ' ', query, flags=re.IGNORECASE)
        keywords = [k.strip() for k in query.split() if k.strip()]
        return keywords
