import os
from typing import Optional, Dict
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QProgressBar, QFrame, QMessageBox, QGroupBox, QCheckBox,
    QSpinBox, QDialog, QDialogButtonBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QIcon, QFont

from ..models import BookMeta


class IndexManagementPanel(QDialog):
    rebuild_requested = pyqtSignal(bool)
    optimize_requested = pyqtSignal()
    cleanup_requested = pyqtSignal()
    incremental_index_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("📊 索引管理")
        self.setMinimumWidth(500)
        self.setModal(True)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        title = QLabel("🔧 索引管理中心")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #333;")
        layout.addWidget(title)

        subtitle = QLabel("管理全文搜索引擎的索引文件，确保搜索性能")
        subtitle.setStyleSheet("color: #666;")
        layout.addWidget(subtitle)

        layout.addWidget(self._create_stats_group())
        layout.addWidget(self._create_actions_group())
        layout.addWidget(self._create_progress_group())

        btn_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        btn_box.rejected.connect(self.accept)
        layout.addWidget(btn_box)

    def _create_stats_group(self) -> QGroupBox:
        group = QGroupBox("📈 索引状态")
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

        self.stats_labels = {}

        stats = [
            ("total_docs", "📚 索引文档数", "0"),
            ("has_content", "📝 已索引正文", "0"),
            ("index_size", "💾 索引大小", "0 B"),
            ("last_optimize", "⏱️ 上次优化时间", "从未优化"),
        ]

        for key, label, default in stats:
            row = QHBoxLayout()
            label_widget = QLabel(label)
            label_widget.setStyleSheet("color: #555; min-width: 120px;")
            row.addWidget(label_widget)

            value_widget = QLabel(default)
            value_widget.setStyleSheet("font-weight: bold; color: #333;")
            self.stats_labels[key] = value_widget
            row.addWidget(value_widget)
            row.addStretch()

            layout.addLayout(row)

        return group

    def _create_actions_group(self) -> QGroupBox:
        group = QGroupBox("⚡ 操作")
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
        layout.setSpacing(10)

        self.incremental_btn = self._create_action_button(
            "🔄 增量索引",
            "仅索引新增或修改的书籍",
            "#4CAF50"
        )
        self.incremental_btn.clicked.connect(self._on_incremental_index)
        layout.addWidget(self.incremental_btn)

        self.rebuild_btn = self._create_action_button(
            "🔨 重建索引",
            "删除现有索引，重新索引所有书籍",
            "#f44336"
        )
        self.rebuild_btn.clicked.connect(self._on_rebuild)
        layout.addWidget(self.rebuild_btn)

        self.optimize_btn = self._create_action_button(
            "⚡ 优化索引",
            "合并索引文件，提升搜索性能",
            "#2196F3"
        )
        self.optimize_btn.clicked.connect(self._on_optimize)
        layout.addWidget(self.optimize_btn)

        self.cleanup_btn = self._create_action_button(
            "🧹 清理碎片",
            "删除不存在文件的索引条目",
            "#FF9800"
        )
        self.cleanup_btn.clicked.connect(self._on_cleanup)
        layout.addWidget(self.cleanup_btn)

        return group

    def _create_action_button(self, title: str, description: str, color: str) -> QPushButton:
        btn = QPushButton()
        btn.setStyleSheet(f"""
            QPushButton {{
                text-align: left;
                padding: 12px 16px;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                background: white;
            }}
            QPushButton:hover {{
                border-color: {color};
                background: #f8f9fa;
            }}
            QPushButton:pressed {{
                background: #e9ecef;
            }}
        """)

        layout = QVBoxLayout(btn)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        title_label = QLabel(title)
        title_label.setStyleSheet(f"font-weight: bold; color: {color}; font-size: 14px;")
        layout.addWidget(title_label)

        desc_label = QLabel(description)
        desc_label.setStyleSheet("color: #888; font-size: 12px;")
        layout.addWidget(desc_label)

        return btn

    def _create_progress_group(self) -> QGroupBox:
        group = QGroupBox("📊 进度")
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

        self.progress_label = QLabel("就绪")
        self.progress_label.setStyleSheet("color: #666;")
        layout.addWidget(self.progress_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #e0e0e0;
                border-radius: 4px;
                text-align: center;
                height: 20px;
            }
            QProgressBar::chunk {
                background: linear-gradient(90deg, #667eea, #764ba2);
                border-radius: 3px;
            }
        """)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        return group

    def update_stats(self, stats: Dict):
        if "total_docs" in stats:
            self.stats_labels["total_docs"].setText(str(stats["total_docs"]))
        if "has_content" in stats:
            self.stats_labels["has_content"].setText(str(stats["has_content"]))
        if "index_size" in stats:
            size_str = self._format_size(stats["index_size"])
            self.stats_labels["index_size"].setText(size_str)
        if "last_optimize" in stats:
            last_opt = stats.get("last_optimize") or "从未优化"
            self.stats_labels["last_optimize"].setText(str(last_opt))

    def _format_size(self, size_bytes: int) -> str:
        for unit in ["B", "KB", "MB", "GB"]:
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} TB"

    def set_progress(self, current: int, total: int, message: str = ""):
        if total > 0:
            self.progress_bar.setRange(0, total)
            self.progress_bar.setValue(current)
        else:
            self.progress_bar.setRange(0, 0)

        if message:
            self.progress_label.setText(message)

    def set_busy(self, busy: bool):
        self.incremental_btn.setEnabled(not busy)
        self.rebuild_btn.setEnabled(not busy)
        self.optimize_btn.setEnabled(not busy)
        self.cleanup_btn.setEnabled(not busy)

    def _on_incremental_index(self):
        self.incremental_index_requested.emit()

    def _on_rebuild(self):
        reply = QMessageBox.question(
            self,
            "确认重建索引",
            "⚠️ 重建索引将删除所有现有索引并重新开始。\n\n"
            "此过程可能需要较长时间，取决于书籍数量。\n\n"
            "是否继续？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.rebuild_requested.emit(True)

    def _on_optimize(self):
        self.optimize_requested.emit()

    def _on_cleanup(self):
        self.cleanup_requested.emit()

    def show_message(self, message: str, icon_type: QMessageBox.Icon = QMessageBox.Icon.Information):
        QMessageBox(icon_type, "提示", message, QMessageBox.StandardButton.Ok, self).exec()
