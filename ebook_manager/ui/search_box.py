import json
import os
from pathlib import Path
from typing import Optional, List
from PyQt6.QtWidgets import (
    QLineEdit, QCompleter, QListWidget, QListWidgetItem,
    QVBoxLayout, QWidget, QLabel, QHBoxLayout, QToolButton
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QSize
from PyQt6.QtGui import QIcon, QAction, QKeySequence


class SearchBox(QLineEdit):
    search_triggered = pyqtSignal(str)
    advanced_search_clicked = pyqtSignal()
    history_file = "search_history.json"

    def __init__(self, parent=None):
        super().__init__(parent)
        self._history: List[str] = []
        self._suggestions: List[str] = []
        self._completer: Optional[QCompleter] = None
        self._suggestion_timer = QTimer(self)
        self._suggestion_timer.setSingleShot(True)
        self._suggestion_timer.setInterval(300)
        self._suggestion_timer.timeout.connect(self._update_suggestions)
        self._dropdown: Optional[_HistoryDropdown] = None
        self._on_suggestion_callback = None
        self._init_ui()
        self._load_history()

    def _init_ui(self):
        self.setPlaceholderText("🔍 搜索书籍 (支持: python AND 数据分析, \"短语匹配\", 模糊~)")
        self.setMinimumWidth(400)
        self.setClearButtonEnabled(True)

        search_action = QAction(QIcon(), "搜索", self)
        search_action.triggered.connect(self._on_search)
        self.addAction(search_action, QLineEdit.ActionPosition.LeadingPosition)

        self.textChanged.connect(self._on_text_changed)
        self.returnPressed.connect(self._on_search)

        self._completer = QCompleter([], self)
        self._completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self._completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self.setCompleter(self._completer)

    def set_suggestion_callback(self, callback):
        self._on_suggestion_callback = callback

    def _on_text_changed(self, text: str):
        if text.strip():
            self._suggestion_timer.start()
        else:
            self._show_history()

    def _update_suggestions(self):
        text = self.text().strip()
        if not text or len(text) < 2:
            return

        suggestions = []
        if self._on_suggestion_callback:
            try:
                suggestions = self._on_suggestion_callback(text)
            except Exception:
                pass

        for item in self._history:
            if item.startswith(text) and item not in suggestions:
                suggestions.append(item)
                if len(suggestions) >= 15:
                    break

        if suggestions:
            model = self._completer.model()
            model.setStringList(suggestions)
            self._completer.complete()

    def _show_history(self):
        if not self._history:
            return

        if self._dropdown is None:
            self._dropdown = _HistoryDropdown(self)
            self._dropdown.item_selected.connect(self._on_history_selected)

        self._dropdown.set_history(self._history)
        self._dropdown.show_below(self)

    def _on_history_selected(self, text: str):
        self.setText(text)
        self._on_search()

    def _on_search(self):
        query = self.text().strip()
        if query:
            self._add_to_history(query)
            self.search_triggered.emit(query)
            if self._dropdown:
                self._dropdown.hide()

    def _add_to_history(self, query: str):
        if query in self._history:
            self._history.remove(query)
        self._history.insert(0, query)
        self._history = self._history[:50]
        self._save_history()

    def _load_history(self):
        history_path = Path.home() / ".ebook_manager" / self.history_file
        if history_path.exists():
            try:
                with open(history_path, "r", encoding="utf-8") as f:
                    self._history = json.load(f)
            except Exception:
                self._history = []

    def _save_history(self):
        history_dir = Path.home() / ".ebook_manager"
        history_dir.mkdir(parents=True, exist_ok=True)
        history_path = history_dir / self.history_file
        try:
            with open(history_path, "w", encoding="utf-8") as f:
                json.dump(self._history, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def clear_history(self):
        self._history = []
        self._save_history()

    def focusInEvent(self, event):
        super().focusInEvent(event)
        if not self.text().strip():
            QTimer.singleShot(100, self._show_history)

    def focusOutEvent(self, event):
        super().focusOutEvent(event)
        if self._dropdown and not self._dropdown.hasFocus():
            QTimer.singleShot(200, self._dropdown.hide)


class _HistoryDropdown(QWidget):
    item_selected = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent, Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)

        header = QHBoxLayout()
        label = QLabel("📜 搜索历史")
        label.setStyleSheet("color: #666; font-weight: bold;")
        header.addWidget(label)
        header.addStretch()

        clear_btn = QToolButton()
        clear_btn.setText("清除")
        clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        clear_btn.setStyleSheet("""
            QToolButton {
                border: none;
                color: #4a9eff;
                padding: 2px 6px;
                border-radius: 4px;
            }
            QToolButton:hover {
                background: #4a9eff22;
            }
        """)
        clear_btn.clicked.connect(self._clear_history)
        header.addWidget(clear_btn)

        layout.addLayout(header)

        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet("""
            QListWidget {
                border: 1px solid #ddd;
                border-radius: 6px;
                background: white;
                padding: 4px;
            }
            QListWidget::item {
                padding: 6px 10px;
                border-radius: 4px;
            }
            QListWidget::item:hover {
                background: #f0f7ff;
            }
            QListWidget::item:selected {
                background: #4a9eff33;
                color: #000;
            }
        """)
        self.list_widget.itemClicked.connect(self._on_item_clicked)
        layout.addWidget(self.list_widget)

    def set_history(self, history: List[str]):
        self.list_widget.clear()
        for item in history[:10]:
            list_item = QListWidgetItem(f"🕐  {item}")
            list_item.setData(Qt.ItemDataRole.UserRole, item)
            self.list_widget.addItem(list_item)

        if self.list_widget.count() == 0:
            empty_item = QListWidgetItem("暂无搜索历史")
            empty_item.setFlags(Qt.ItemFlag.NoItemFlags)
            empty_item.setForeground(Qt.GlobalColor.gray)
            self.list_widget.addItem(empty_item)

    def _on_item_clicked(self, item: QListWidgetItem):
        text = item.data(Qt.ItemDataRole.UserRole)
        if text:
            self.item_selected.emit(text)
            self.hide()

    def _clear_history(self):
        search_box = self.parent()
        if search_box and hasattr(search_box, "clear_history"):
            search_box.clear_history()
        self.list_widget.clear()
        empty_item = QListWidgetItem("暂无搜索历史")
        empty_item.setFlags(Qt.ItemFlag.NoItemFlags)
        empty_item.setForeground(Qt.GlobalColor.gray)
        self.list_widget.addItem(empty_item)

    def show_below(self, widget: QLineEdit):
        pos = widget.mapToGlobal(widget.rect().bottomLeft())
        self.move(pos)
        self.setFixedWidth(max(widget.width(), 300))
        self.show()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.hide()
        else:
            super().keyPressEvent(event)
