from pathlib import Path
from typing import List, Dict, Optional
from PyQt6.QtCore import QThread, pyqtSignal

from ..models import BookMeta
from ..search import SearchEngine
from ..metadata_parser import MetadataParser


class SearchWorker(QThread):
    results_ready = pyqtSignal(list, str)
    error_occurred = pyqtSignal(str)

    def __init__(self, search_engine: SearchEngine, query: str, filters: Optional[Dict] = None):
        super().__init__()
        self._search_engine = search_engine
        self._query = query
        self._filters = filters or {}

    def run(self):
        try:
            results = self._search_engine.search(
                self._query,
                limit=100,
                filter_formats=self._filters.get("formats"),
                filter_tags=self._filters.get("tags"),
                date_start=self._filters.get("date_start"),
                date_end=self._filters.get("date_end"),
                min_size=self._filters.get("min_size"),
                max_size=self._filters.get("max_size"),
            )
            self.results_ready.emit(results, self._query)
        except Exception as e:
            self.error_occurred.emit(f"搜索失败: {str(e)}")


class IndexWorker(QThread):
    progress = pyqtSignal(int, int, str)
    finished_signal = pyqtSignal(int, int)
    error_occurred = pyqtSignal(str)

    def __init__(
        self,
        search_engine: SearchEngine,
        books: List[BookMeta],
        extract_content: bool = True,
        rebuild: bool = False,
    ):
        super().__init__()
        self._search_engine = search_engine
        self._books = books
        self._extract_content = extract_content
        self._rebuild = rebuild

    def run(self):
        try:
            if self._rebuild:
                indexed, skipped = self._search_engine.rebuild(
                    self._books,
                    progress_callback=lambda c, t, p: self.progress.emit(c, t, p)
                )
            else:
                indexed, skipped = self._search_engine.index_books(
                    self._books,
                    extract_content=self._extract_content,
                    progress_callback=lambda c, t, p: self.progress.emit(c, t, p)
                )
            self.finished_signal.emit(indexed, skipped)
        except Exception as e:
            self.error_occurred.emit(f"索引失败: {str(e)}")


class IndexSingleWorker(QThread):
    finished_signal = pyqtSignal(bool, str)
    progress = pyqtSignal(int, int)

    def __init__(
        self,
        search_engine: SearchEngine,
        book: BookMeta,
        extract_content: bool = True,
    ):
        super().__init__()
        self._search_engine = search_engine
        self._book = book
        self._extract_content = extract_content

    def run(self):
        try:
            result = self._search_engine.index_book(
                self._book,
                extract_content=self._extract_content,
                progress_callback=lambda c, t: self.progress.emit(c, t)
            )
            self.finished_signal.emit(result, self._book.file_path)
        except Exception as e:
            self.finished_signal.emit(False, self._book.file_path)


class OptimizeWorker(QThread):
    finished_signal = pyqtSignal(bool)
    error_occurred = pyqtSignal(str)

    def __init__(self, search_engine: SearchEngine):
        super().__init__()
        self._search_engine = search_engine

    def run(self):
        try:
            result = self._search_engine.optimize()
            self.finished_signal.emit(result)
        except Exception as e:
            self.error_occurred.emit(f"优化失败: {str(e)}")


class CleanupWorker(QThread):
    finished_signal = pyqtSignal(int)
    error_occurred = pyqtSignal(str)

    def __init__(self, search_engine: SearchEngine, existing_paths: List[str]):
        super().__init__()
        self._search_engine = search_engine
        self._existing_paths = existing_paths

    def run(self):
        try:
            removed = self._search_engine.cleanup_orphans(self._existing_paths)
            self.finished_signal.emit(removed)
        except Exception as e:
            self.error_occurred.emit(f"清理失败: {str(e)}")


class SuggestionWorker(QThread):
    suggestions_ready = pyqtSignal(list)

    def __init__(self, search_engine: SearchEngine, prefix: str, limit: int = 10):
        super().__init__()
        self._search_engine = search_engine
        self._prefix = prefix
        self._limit = limit

    def run(self):
        try:
            suggestions = self._search_engine.suggest(self._prefix, self._limit)
            self.suggestions_ready.emit(suggestions)
        except Exception:
            self.suggestions_ready.emit([])


class FileAddWorker(QThread):
    book_parsed = pyqtSignal(object)
    error_occurred = pyqtSignal(str)

    def __init__(self, file_path: str):
        super().__init__()
        self._file_path = file_path
        self._parser = MetadataParser()

    def run(self):
        try:
            book = self._parser.parse(self._file_path)
            self.book_parsed.emit(book)
        except Exception as e:
            self.error_occurred.emit(f"解析文件失败: {str(e)}")
