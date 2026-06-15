from pathlib import Path

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QStatusBar, QMessageBox, QTabWidget, QLabel, QApplication,
    QFileDialog, QToolBar, QToolButton, QWidgetAction, QFrame
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSize, QTimer
from PyQt6.QtGui import QAction, QIcon, QKeySequence

from ..models import BookMeta
from ..scanner import BookshelfScanner
from ..metadata_parser import MetadataParser
from ..metadata_editor import MetadataEditor
from ..network_source import NetworkSourceManager
from ..converter import FormatConverter
from ..search import SearchEngine, IndexFileWatcher

from .scanner_panel import ScannerPanel
from .book_table import BookTableWidget
from .edit_panel import MetadataEditPanel
from .search_dialog import OnlineSearchDialog
from .convert_dialog import ConvertDialog
from .workers import ScanWorker, ParseWorker
from .search_box import SearchBox
from .search_result_panel import SearchResultPanel
from .advanced_search_panel import AdvancedSearchPanel
from .index_management_panel import IndexManagementPanel
from .search_workers import (
    SearchWorker,
    IndexWorker,
    IndexSingleWorker,
    OptimizeWorker,
    CleanupWorker,
    FileAddWorker,
)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("📚 电子书元数据管理器")
        self.setMinimumSize(1400, 800)

        self._books: list = []
        self._scanner = BookshelfScanner()
        self._parser = MetadataParser()
        self._editor = MetadataEditor()
        self._source_manager = NetworkSourceManager()
        self._converter = FormatConverter()

        self._search_engine = SearchEngine()
        self._file_watcher = IndexFileWatcher()

        self._search_thread: QThread = None
        self._index_thread: QThread = None
        self._optimize_thread: QThread = None
        self._cleanup_thread: QThread = None
        self._suggestion_thread: QThread = None
        self._file_add_thread: QThread = None

        self._watch_directories: list = []

        self._init_ui()
        self._init_menu()
        self._init_statusbar()
        self._init_search_components()

    def _init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(8)

        self.scanner_panel = ScannerPanel()
        self.scanner_panel.scan_requested.connect(self._on_scan_requested)
        main_layout.addWidget(self.scanner_panel)

        self._init_search_toolbar()
        main_layout.addLayout(self._search_toolbar_layout)

        self.main_tab = QTabWidget()
        self.main_tab.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #ddd;
                border-radius: 4px;
                top: -1px;
            }
            QTabBar::tab {
                background: #f5f5f5;
                border: 1px solid #ddd;
                border-bottom: none;
                padding: 8px 16px;
                margin-right: 2px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            QTabBar::tab:selected {
                background: white;
                border-bottom: 1px solid white;
            }
            QTabBar::tab:hover {
                background: #e8e8e8;
            }
        """)

        self._init_library_tab()
        self._init_search_tab()
        self._init_advanced_search_tab()

        self.main_tab.addTab(self.library_tab, "📚 书库")
        self.main_tab.addTab(self.search_tab, "🔍 搜索结果")
        self.main_tab.addTab(self.advanced_search_tab, "⚙️ 高级搜索")
        self.main_tab.currentChanged.connect(self._on_tab_changed)

        main_layout.addWidget(self.main_tab, 1)

        self.setStyleSheet("""
            QMainWindow { background: #f5f6fa; }
            QGroupBox {
                font-weight: bold;
                border: 1px solid #ddd;
                border-radius: 6px;
                margin-top: 8px;
                padding-top: 16px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 6px;
            }
            QTableWidget {
                border: 1px solid #ddd;
                border-radius: 4px;
                gridline-color: #eee;
                selection-background-color: #4a9eff33;
                selection-color: #000;
            }
            QTableWidget::item:hover { background: #f0f7ff; }
            QHeaderView::section {
                background: #fafafa;
                border: none;
                border-bottom: 2px solid #ddd;
                padding: 6px;
                font-weight: bold;
            }
            QLineEdit, QTextEdit, QComboBox {
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 4px 8px;
            }
            QLineEdit:focus, QTextEdit:focus {
                border-color: #4a9eff;
            }
            QPushButton {
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 4px 12px;
                background: white;
            }
            QPushButton:hover { background: #f0f7ff; border-color: #4a9eff; }
        """)

    def _init_search_toolbar(self):
        self._search_toolbar_layout = QHBoxLayout()
        self._search_toolbar_layout.setContentsMargins(0, 0, 0, 0)
        self._search_toolbar_layout.setSpacing(8)

        self.search_box = SearchBox()
        self.search_box.search_triggered.connect(self._on_search_triggered)
        self.search_box.set_suggestion_callback(self._get_suggestions)
        self._search_toolbar_layout.addWidget(self.search_box, 1)

        self.advanced_search_btn = QToolButton()
        self.advanced_search_btn.setText("⚙️ 高级")
        self.advanced_search_btn.setToolTip("打开高级搜索面板")
        self.advanced_search_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.advanced_search_btn.setStyleSheet("""
            QToolButton {
                padding: 6px 12px;
                border: 1px solid #ddd;
                border-radius: 4px;
                background: white;
            }
            QToolButton:hover {
                background: #f0f7ff;
                border-color: #4a9eff;
            }
        """)
        self.advanced_search_btn.clicked.connect(lambda: self.main_tab.setCurrentIndex(2))
        self._search_toolbar_layout.addWidget(self.advanced_search_btn)

        self.index_management_btn = QToolButton()
        self.index_management_btn.setText("📊 索引")
        self.index_management_btn.setToolTip("管理索引文件")
        self.index_management_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.index_management_btn.setStyleSheet("""
            QToolButton {
                padding: 6px 12px;
                border: 1px solid #ddd;
                border-radius: 4px;
                background: white;
            }
            QToolButton:hover {
                background: #f0f7ff;
                border-color: #4a9eff;
            }
        """)
        self.index_management_btn.clicked.connect(self._show_index_management)
        self._search_toolbar_layout.addWidget(self.index_management_btn)

    def _init_library_tab(self):
        self.library_tab = QWidget()
        layout = QVBoxLayout(self.library_tab)
        layout.setContentsMargins(0, 0, 0, 0)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        self.book_table = BookTableWidget()
        self.book_table.selection_changed.connect(self._on_selection_changed)
        self.book_table.edit_requested.connect(self._on_edit_requested)
        self.book_table.convert_requested.connect(self._on_convert_requested)
        self.book_table.search_meta_requested.connect(self._on_search_meta_requested)
        splitter.addWidget(self.book_table)

        self.edit_panel = MetadataEditPanel()
        self.edit_panel.save_requested.connect(self._on_save_metadata)
        splitter.addWidget(self.edit_panel)

        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)
        layout.addWidget(splitter)

    def _init_search_tab(self):
        self.search_tab = QWidget()
        layout = QVBoxLayout(self.search_tab)
        layout.setContentsMargins(0, 0, 0, 0)

        self.search_result_panel = SearchResultPanel()
        self.search_result_panel.result_selected.connect(self._on_search_result_selected)
        self.search_result_panel.result_double_clicked.connect(self._on_search_result_double_clicked)
        layout.addWidget(self.search_result_panel)

    def _init_advanced_search_tab(self):
        self.advanced_search_tab = QWidget()
        layout = QVBoxLayout(self.advanced_search_tab)
        layout.setContentsMargins(0, 0, 0, 0)

        self.advanced_search_panel = AdvancedSearchPanel()
        self.advanced_search_panel.search_requested.connect(self._on_advanced_search)
        self.advanced_search_panel.reset_requested.connect(self._on_advanced_search_reset)
        layout.addWidget(self.advanced_search_panel)

    def _init_search_components(self):
        self._index_management_dialog = None

        self._file_watcher.on_file_added = self._on_watcher_file_added
        self._file_watcher.on_file_deleted = self._on_watcher_file_deleted
        self._file_watcher.on_file_modified = self._on_watcher_file_modified

    def _init_menu(self):
        menubar = self.menuBar()

        file_menu = menubar.addMenu("文件(&F)")
        import_action = QAction("导入文件(&I)...", self)
        import_action.triggered.connect(self._import_files)
        file_menu.addAction(import_action)

        import_dir_action = QAction("导入目录(&D)...", self)
        import_dir_action.triggered.connect(self._import_directory)
        file_menu.addAction(import_dir_action)

        file_menu.addSeparator()
        exit_action = QAction("退出(&Q)", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        edit_menu = menubar.addMenu("编辑(&E)")
        batch_edit_action = QAction("批量编辑(&B)", self)
        batch_edit_action.triggered.connect(lambda: self._on_edit_requested(self.book_table.get_selected_books()))
        edit_menu.addAction(batch_edit_action)

        search_meta_action = QAction("在线搜索元数据(&S)", self)
        search_meta_action.triggered.connect(lambda: self._on_search_meta_requested(self.book_table.get_selected_books()))
        edit_menu.addAction(search_meta_action)

        search_menu = menubar.addMenu("搜索(&S)")
        fulltext_action = QAction("全文搜索(&F)...", self)
        fulltext_action.setShortcut(QKeySequence("Ctrl+F"))
        fulltext_action.triggered.connect(lambda: self.search_box.setFocus())
        search_menu.addAction(fulltext_action)

        advanced_action = QAction("高级搜索(&A)...", self)
        advanced_action.setShortcut(QKeySequence("Ctrl+Shift+F"))
        advanced_action.triggered.connect(lambda: self.main_tab.setCurrentIndex(2))
        search_menu.addAction(advanced_action)

        search_menu.addSeparator()

        index_mgmt_action = QAction("索引管理(&M)...", self)
        index_mgmt_action.triggered.connect(self._show_index_management)
        search_menu.addAction(index_mgmt_action)

        rebuild_index_action = QAction("重建索引(&R)...", self)
        rebuild_index_action.triggered.connect(lambda: self._show_index_management())
        search_menu.addAction(rebuild_index_action)

        incremental_index_action = QAction("增量索引(&U)", self)
        incremental_index_action.triggered.connect(self._on_incremental_index)
        search_menu.addAction(incremental_index_action)

        tool_menu = menubar.addMenu("工具(&T)")
        convert_action = QAction("格式转换(&C)...", self)
        convert_action.triggered.connect(lambda: self._on_convert_requested(self.book_table.get_selected_books()))
        tool_menu.addAction(convert_action)

        calibre_status = QAction("Calibre 状态检查", self)
        calibre_status.triggered.connect(self._check_calibre)
        tool_menu.addAction(calibre_status)

        help_menu = menubar.addMenu("帮助(&H)")
        about_action = QAction("关于(&A)", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    def _init_statusbar(self):
        self.statusBar().showMessage("就绪")

    def _on_tab_changed(self, index):
        if index == 2:
            self._refresh_advanced_search_options()

    def _refresh_advanced_search_options(self):
        try:
            tags = self._search_engine.get_all_tags()
            formats = self._search_engine.get_all_formats()
            self.advanced_search_panel.set_available_tags(tags)
            self.advanced_search_panel.set_available_formats(formats)
        except Exception:
            pass

    def _on_scan_requested(self, directories: list, recursive: bool):
        self.statusBar().showMessage("正在扫描目录...")
        self._scan_worker = ScanWorker(directories, recursive)
        self._scan_worker.progress.connect(self.scanner_panel.on_scan_progress)
        self._scan_worker.finished_signal.connect(self._on_scan_finished)
        self._scan_worker.start()

        self._watch_directories = directories
        self._file_watcher.set_watch_directories(directories)
        if not self._file_watcher.is_running:
            self._file_watcher.start()

    def _on_scan_finished(self, files: list):
        self.scanner_panel.on_scan_complete(len(files))
        if not files:
            self.statusBar().showMessage("未找到电子书文件")
            return
        self.statusBar().showMessage(f"扫描到 {len(files)} 个文件，正在解析元数据...")
        self._parse_worker = ParseWorker(files)
        self._parse_worker.progress.connect(
            lambda c, t, p: self.statusBar().showMessage(f"解析中 {c}/{t}: {Path(p).name}")
        )
        self._parse_worker.finished_signal.connect(self._on_parse_finished)
        self._parse_worker.start()

    def _on_parse_finished(self, books: list):
        self._books = books
        self.book_table.load_books(books)
        self.statusBar().showMessage(f"已加载 {len(books)} 本电子书，开始增量索引...")
        self._start_incremental_index(books)

    def _start_incremental_index(self, books: list, rebuild: bool = False):
        self._index_thread = IndexWorker(self._search_engine, books, extract_content=True, rebuild=rebuild)
        self._index_thread.progress.connect(self._on_index_progress)
        self._index_thread.finished_signal.connect(self._on_index_finished)
        self._index_thread.error_occurred.connect(self._on_index_error)
        self._index_thread.start()

    def _on_index_progress(self, current: int, total: int, file_path: str):
        self.statusBar().showMessage(f"索引中 {current}/{total}: {Path(file_path).name}")
        if self._index_management_dialog:
            self._index_management_dialog.set_progress(current, total, f"索引中: {Path(file_path).name}")

    def _on_index_finished(self, indexed: int, skipped: int):
        msg = f"索引完成: 新增/更新 {indexed} 本，跳过 {skipped} 本（已存在且未修改）"
        self.statusBar().showMessage(msg)

        if self._index_management_dialog:
            self._index_management_dialog.set_busy(False)
            self._index_management_dialog.update_stats(self._search_engine.get_stats())
            self._index_management_dialog.set_progress(0, 0, msg)
            self._index_management_dialog.show_message(msg)

    def _on_index_error(self, error_msg: str):
        self.statusBar().showMessage(error_msg)
        if self._index_management_dialog:
            self._index_management_dialog.set_busy(False)
            self._index_management_dialog.show_message(error_msg, QMessageBox.Icon.Critical)

    def _on_selection_changed(self, selected: list):
        self.edit_panel.set_books(selected)
        self.statusBar().showMessage(f"已选择 {len(selected)} 本")

    def _on_edit_requested(self, books: list):
        if books:
            self.edit_panel.set_books(books)

    def _on_save_metadata(self, books: list, changes: dict):
        self._editor.apply_batch(books, changes)
        for book in books:
            if book.file_format == "epub":
                self._editor.save_epub_metadata(book)
            self._search_engine.index_book(book, extract_content=False)

        self.book_table.load_books(self._books)
        self.statusBar().showMessage(f"已更新 {len(books)} 本书的元数据")

    def _on_search_meta_requested(self, books: list):
        if not books:
            QMessageBox.information(self, "提示", "请先选择书籍")
            return
        dialog = OnlineSearchDialog(books, self._source_manager, self)
        if dialog.exec() == OnlineSearchDialog.DialogCode.Accepted:
            data = dialog.get_selected_data()
            if data:
                overwrite = QMessageBox.question(
                    self,
                    "确认",
                    "是否用搜索结果覆盖已有元数据？\n选\"是\"覆盖全部，选\"否\"仅填充空字段",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel,
                )
                if overwrite == QMessageBox.StandardButton.Cancel:
                    return
                for book in books:
                    self._editor.merge_from_source(book, data, overwrite=(overwrite == QMessageBox.StandardButton.Yes))
                    if book.file_format == "epub":
                        self._editor.save_epub_metadata(book)
                    self._search_engine.index_book(book, extract_content=False)
                self.book_table.load_books(self._books)
                self.statusBar().showMessage(f"已从在线源填充 {len(books)} 本书的元数据")

    def _on_convert_requested(self, books: list):
        if not books:
            books = self.book_table.get_selected_books()
        if not books:
            QMessageBox.information(self, "提示", "请先选择要转换的书籍")
            return
        dialog = ConvertDialog(books, self._converter, self)
        dialog.exec()

    def _import_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "选择电子书文件", "",
            "电子书 (*.epub *.mobi *.pdf);;所有文件 (*)"
        )
        if files:
            self._parse_and_add(files)

    def _import_directory(self):
        d = QFileDialog.getExistingDirectory(self, "选择电子书目录")
        if d:
            files = self._scanner.scan_directory(d)
            if files:
                self._parse_and_add(files)

            if d not in self._watch_directories:
                self._watch_directories.append(d)
                self._file_watcher.set_watch_directories(self._watch_directories)
                if not self._file_watcher.is_running:
                    self._file_watcher.start()

    def _parse_and_add(self, files: list):
        existing_paths = {b.file_path for b in self._books}
        new_files = [f for f in files if f not in existing_paths]
        if not new_files:
            self.statusBar().showMessage("文件已存在于列表中")
            return

        parser = MetadataParser()
        for f in new_files:
            try:
                book = parser.parse(f)
                self._books.append(book)
            except Exception:
                self._books.append(BookMeta(file_path=f, file_format=Path(f).suffix.lstrip("."), title=Path(f).stem))

        self.book_table.load_books(self._books)
        self.statusBar().showMessage(f"已导入 {len(new_files)} 本电子书，开始索引...")

        new_books = [b for b in self._books if b.file_path in new_files]
        for book in new_books:
            self._search_engine.index_book(book, extract_content=True)

    def _check_calibre(self):
        if self._converter.is_calibre_available:
            QMessageBox.information(self, "Calibre 状态", "✅ Calibre (ebook-convert) 已安装且可用")
        else:
            QMessageBox.warning(
                self, "Calibre 状态",
                "❌ 未检测到 Calibre\n\n格式转换功能需要 Calibre 支持。\n"
                "请从 https://calibre-ebook.com 下载安装，\n"
                "并确保 ebook-convert 在系统 PATH 中。"
            )

    def _show_about(self):
        QMessageBox.about(
            self, "关于",
            "📚 电子书元数据管理器 v2.0\n\n"
            "支持 EPUB/MOBI/PDF 元数据编辑与格式转换\n"
            "支持全文搜索，基于 Whoosh + Jieba 分词\n"
            "元数据来源: 豆瓣读书、OpenLibrary\n"
            "格式转换依赖: Calibre (ebook-convert)"
        )

    def _on_search_triggered(self, query: str):
        self.statusBar().showMessage(f"搜索中: {query}...")
        self.main_tab.setCurrentIndex(1)

        self._search_thread = SearchWorker(self._search_engine, query)
        self._search_thread.results_ready.connect(self._on_search_results)
        self._search_thread.error_occurred.connect(self._on_search_error)
        self._search_thread.start()

    def _on_advanced_search(self, filters: dict):
        query = filters.get("query", "")
        self.statusBar().showMessage(f"高级搜索中: {query or '(无关键词)'}...")
        self.main_tab.setCurrentIndex(1)

        self._search_thread = SearchWorker(self._search_engine, query, filters)
        self._search_thread.results_ready.connect(self._on_search_results)
        self._search_thread.error_occurred.connect(self._on_search_error)
        self._search_thread.start()

    def _on_advanced_search_reset(self):
        pass

    def _on_search_results(self, results: list, query: str):
        self.search_result_panel.set_results(results, query)
        self.statusBar().showMessage(f"找到 {len(results)} 个结果")

    def _on_search_error(self, error_msg: str):
        self.statusBar().showMessage(error_msg)
        QMessageBox.critical(self, "搜索错误", error_msg)

    def _on_search_result_selected(self, result: dict):
        file_path = result.get("file_path", "")
        if file_path:
            book = self._find_book_by_path(file_path)
            if book:
                self.edit_panel.set_books([book])

    def _on_search_result_double_clicked(self, result: dict):
        file_path = result.get("file_path", "")
        if file_path:
            book = self._find_book_by_path(file_path)
            if book:
                self.main_tab.setCurrentIndex(0)
                self.book_table.select_book(book)

    def _find_book_by_path(self, file_path: str):
        for book in self._books:
            if book.file_path == file_path:
                return book
        return None

    def _get_suggestions(self, prefix: str) -> list:
        try:
            return self._search_engine.suggest(prefix, limit=10)
        except Exception:
            return []

    def _show_index_management(self):
        if self._index_management_dialog is None:
            self._index_management_dialog = IndexManagementPanel(self)
            self._index_management_dialog.rebuild_requested.connect(self._on_rebuild_index)
            self._index_management_dialog.optimize_requested.connect(self._on_optimize_index)
            self._index_management_dialog.cleanup_requested.connect(self._on_cleanup_index)
            self._index_management_dialog.incremental_index_requested.connect(self._on_incremental_index)

        self._index_management_dialog.update_stats(self._search_engine.get_stats())
        self._index_management_dialog.show()

    def _on_incremental_index(self):
        if not self._books:
            QMessageBox.information(self, "提示", "请先扫描或导入书籍")
            return

        if self._index_management_dialog:
            self._index_management_dialog.set_busy(True)

        self.statusBar().showMessage("开始增量索引...")
        self._start_incremental_index(self._books, rebuild=False)

    def _on_rebuild_index(self, confirm: bool):
        if not self._books:
            QMessageBox.information(self, "提示", "请先扫描或导入书籍")
            return

        if confirm:
            if self._index_management_dialog:
                self._index_management_dialog.set_busy(True)

            self.statusBar().showMessage("开始重建索引...")
            self._start_incremental_index(self._books, rebuild=True)

    def _on_optimize_index(self):
        if self._index_management_dialog:
            self._index_management_dialog.set_busy(True)
            self._index_management_dialog.set_progress(0, 0, "正在优化索引...")

        self.statusBar().showMessage("正在优化索引...")

        self._optimize_thread = OptimizeWorker(self._search_engine)
        self._optimize_thread.finished_signal.connect(self._on_optimize_finished)
        self._optimize_thread.error_occurred.connect(self._on_optimize_error)
        self._optimize_thread.start()

    def _on_optimize_finished(self, success: bool):
        if success:
            msg = "索引优化完成"
        else:
            msg = "索引优化失败"

        self.statusBar().showMessage(msg)
        if self._index_management_dialog:
            self._index_management_dialog.set_busy(False)
            self._index_management_dialog.update_stats(self._search_engine.get_stats())
            self._index_management_dialog.set_progress(0, 0, msg)
            if success:
                self._index_management_dialog.show_message(msg)
            else:
                self._index_management_dialog.show_message(msg, QMessageBox.Icon.Warning)

    def _on_optimize_error(self, error_msg: str):
        self.statusBar().showMessage(error_msg)
        if self._index_management_dialog:
            self._index_management_dialog.set_busy(False)
            self._index_management_dialog.show_message(error_msg, QMessageBox.Icon.Critical)

    def _on_cleanup_index(self):
        existing_paths = [b.file_path for b in self._books]

        if self._index_management_dialog:
            self._index_management_dialog.set_busy(True)
            self._index_management_dialog.set_progress(0, 0, "正在清理无效索引...")

        self.statusBar().showMessage("正在清理无效索引...")

        self._cleanup_thread = CleanupWorker(self._search_engine, existing_paths)
        self._cleanup_thread.finished_signal.connect(self._on_cleanup_finished)
        self._cleanup_thread.error_occurred.connect(self._on_cleanup_error)
        self._cleanup_thread.start()

    def _on_cleanup_finished(self, removed: int):
        msg = f"清理完成，移除了 {removed} 个无效索引条目"
        self.statusBar().showMessage(msg)

        if self._index_management_dialog:
            self._index_management_dialog.set_busy(False)
            self._index_management_dialog.update_stats(self._search_engine.get_stats())
            self._index_management_dialog.set_progress(0, 0, msg)
            self._index_management_dialog.show_message(msg)

    def _on_cleanup_error(self, error_msg: str):
        self.statusBar().showMessage(error_msg)
        if self._index_management_dialog:
            self._index_management_dialog.set_busy(False)
            self._index_management_dialog.show_message(error_msg, QMessageBox.Icon.Critical)

    def _on_watcher_file_added(self, file_path: str):
        self.statusBar().showMessage(f"检测到新文件: {Path(file_path).name}")
        QTimer.singleShot(1000, lambda: self._add_new_file(file_path))

    def _on_watcher_file_deleted(self, file_path: str):
        self.statusBar().showMessage(f"文件已删除: {Path(file_path).name}")
        self._search_engine.remove_from_index(file_path)
        self._books = [b for b in self._books if b.file_path != file_path]
        self.book_table.load_books(self._books)

    def _on_watcher_file_modified(self, file_path: str):
        self.statusBar().showMessage(f"文件已修改，重新索引: {Path(file_path).name}")
        book = self._find_book_by_path(file_path)
        if book:
            parser = MetadataParser()
            updated_book = parser.parse(file_path)
            book.title = updated_book.title
            book.author = updated_book.author
            book.description = updated_book.description
            book.tags = updated_book.tags
            self._search_engine.index_book(book, extract_content=True)
            self.book_table.load_books(self._books)

    def _add_new_file(self, file_path: str):
        if any(b.file_path == file_path for b in self._books):
            return

        self._file_add_thread = FileAddWorker(file_path)
        self._file_add_thread.book_parsed.connect(self._on_new_book_parsed)
        self._file_add_thread.error_occurred.connect(self._on_file_add_error)
        self._file_add_thread.start()

    def _on_new_book_parsed(self, book: BookMeta):
        self._books.append(book)
        self.book_table.load_books(self._books)
        self._search_engine.index_book(book, extract_content=True)
        self.statusBar().showMessage(f"已添加新书: {book.title}")

    def _on_file_add_error(self, error_msg: str):
        self.statusBar().showMessage(error_msg)

    def closeEvent(self, event):
        try:
            if self._file_watcher.is_running:
                self._file_watcher.stop()
        except Exception:
            pass

        try:
            self._search_engine.close()
        except Exception:
            pass

        super().closeEvent(event)
