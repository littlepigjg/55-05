import os
import json
import re
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Callable, Tuple
from whoosh import index, scoring
from whoosh.fields import Schema, TEXT, ID, KEYWORD, NUMERIC, DATETIME
from whoosh.query import Every
from whoosh.highlight import HtmlFormatter, ContextFragmenter, Highlighter
from whoosh.writing import AsyncWriter, BufferedWriter

from .analyzers import chinese_analyzer
from .content_extractor import ContentExtractor
from .filters import SearchFilters, FilterBuilder, filter_results
from .query_builder import QueryBuilder
from ..models import BookMeta


class SearchEngine:
    INDEX_DIR_NAME = ".ebook_index"
    META_FILE = "index_meta.json"

    def __init__(self, base_dir: Optional[str] = None):
        if base_dir is None:
            base_dir = str(Path.home() / ".ebook_manager")
        self.base_dir = Path(base_dir)
        self.index_dir = self.base_dir / self.INDEX_DIR_NAME
        self.meta_file = self.base_dir / self.META_FILE
        self.ix = None
        self._content_extractor = ContentExtractor()
        self._schema = self._create_schema()
        self._init_index()
        self._load_meta()

    def _create_schema(self) -> Schema:
        analyzer = chinese_analyzer()
        return Schema(
            id=ID(unique=True, stored=True),
            file_path=ID(stored=True, unique=True),
            title=TEXT(stored=True, analyzer=analyzer),
            author=TEXT(stored=True, analyzer=analyzer),
            description=TEXT(stored=True, analyzer=analyzer),
            content_body=TEXT(analyzer=analyzer, stored=False),
            publisher=TEXT(stored=True, analyzer=analyzer),
            publish_date=DATETIME(stored=True, sortable=True),
            isbn=ID(stored=True),
            language=ID(stored=True),
            file_format=ID(stored=True, field_boost=1.5),
            file_size=NUMERIC(stored=True, sortable=True),
            tags=KEYWORD(stored=True, commas=True, analyzer=analyzer),
            cover_path=TEXT(stored=True),
            indexed_at=DATETIME(stored=True, sortable=True),
            file_mtime=NUMERIC(stored=True),
            file_hash=ID(stored=True),
        )

    def _init_index(self):
        self.index_dir.mkdir(parents=True, exist_ok=True)
        if index.exists_in(str(self.index_dir)):
            self.ix = index.open_dir(str(self.index_dir))
        else:
            self.ix = index.create_in(str(self.index_dir), self._schema)

    def _init_query_builder(self):
        self._query_builder = QueryBuilder(self._schema)

    def _load_meta(self):
        self._meta = {"indexed_files": {}, "last_optimize": None, "total_docs": 0}
        if self.meta_file.exists():
            try:
                with open(self.meta_file, "r", encoding="utf-8") as f:
                    self._meta = json.load(f)
            except Exception:
                pass
        if "indexed_files" not in self._meta:
            self._meta["indexed_files"] = {}

    def _save_meta(self):
        self.base_dir.mkdir(parents=True, exist_ok=True)
        with open(self.meta_file, "w", encoding="utf-8") as f:
            json.dump(self._meta, f, ensure_ascii=False, indent=2)

    def _get_file_hash(self, file_path: str) -> str:
        try:
            stat = os.stat(file_path)
            return hashlib.md5(f"{file_path}_{stat.st_mtime}_{stat.st_size}".encode()).hexdigest()
        except Exception:
            return ""

    def _needs_index(self, file_path: str) -> Tuple[bool, str]:
        file_hash = self._get_file_hash(file_path)
        existing = self._meta["indexed_files"].get(file_path, {})
        if existing.get("file_hash") == file_hash and existing.get("status") == "indexed":
            return False, file_hash
        return True, file_hash

    def _book_to_document(self, book: BookMeta, file_hash: str, content_body: str = "") -> dict:
        doc = {
            "id": hashlib.md5(book.file_path.encode()).hexdigest(),
            "file_path": book.file_path,
            "title": book.title or "",
            "author": book.author or "",
            "description": book.description or "",
            "content_body": content_body,
            "publisher": book.publisher or "",
            "isbn": book.isbn or "",
            "language": book.language or "",
            "file_format": book.file_format or "",
            "file_size": book.file_size or 0,
            "tags": ",".join(book.tags) if book.tags else "",
            "cover_path": book.cover_path or "",
            "indexed_at": datetime.now(),
            "file_mtime": os.path.getmtime(book.file_path) if os.path.exists(book.file_path) else 0,
            "file_hash": file_hash,
        }
        if book.publish_date:
            try:
                if re.match(r"^\d{4}-\d{2}-\d{2}$", book.publish_date):
                    doc["publish_date"] = datetime.strptime(book.publish_date, "%Y-%m-%d")
                elif re.match(r"^\d{4}$", book.publish_date):
                    doc["publish_date"] = datetime.strptime(book.publish_date, "%Y")
            except Exception:
                pass
        return doc

    def index_book(
        self,
        book: BookMeta,
        extract_content: bool = True,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> bool:
        needs_index, file_hash = self._needs_index(book.file_path)
        if not needs_index:
            return False

        content_body = ""
        if extract_content:
            content_body = self._content_extractor.extract(book.file_path, progress_callback)

        doc = self._book_to_document(book, file_hash, content_body)

        try:
            with AsyncWriter(self.ix) as writer:
                writer.update_document(**doc)

            self._meta["indexed_files"][book.file_path] = {
                "file_hash": file_hash,
                "status": "indexed",
                "indexed_at": datetime.now().isoformat(),
                "has_content": bool(content_body),
            }
            self._save_meta()
            return True
        except Exception:
            return False

    def index_books(
        self,
        books: List[BookMeta],
        extract_content: bool = True,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
    ) -> Tuple[int, int]:
        total = len(books)
        indexed = 0
        skipped = 0

        with BufferedWriter(self.ix, period=10, limit=100) as writer:
            for i, book in enumerate(books):
                if progress_callback:
                    progress_callback(i + 1, total, book.file_path)

                needs_index, file_hash = self._needs_index(book.file_path)
                if not needs_index:
                    skipped += 1
                    continue

                content_body = ""
                if extract_content:
                    content_body = self._content_extractor.extract(book.file_path)

                doc = self._book_to_document(book, file_hash, content_body)

                try:
                    writer.update_document(**doc)
                    self._meta["indexed_files"][book.file_path] = {
                        "file_hash": file_hash,
                        "status": "indexed",
                        "indexed_at": datetime.now().isoformat(),
                        "has_content": bool(content_body),
                    }
                    indexed += 1
                except Exception:
                    skipped += 1

            writer.flush()

        self._save_meta()
        return indexed, skipped

    def remove_from_index(self, file_path: str) -> bool:
        try:
            with AsyncWriter(self.ix) as writer:
                writer.delete_by_term("file_path", file_path)

            if file_path in self._meta["indexed_files"]:
                del self._meta["indexed_files"][file_path]
                self._save_meta()
            return True
        except Exception:
            return False

    def _build_filters(
        self,
        filter_formats: Optional[List[str]] = None,
        filter_tags: Optional[List[str]] = None,
        date_start: Optional[datetime] = None,
        date_end: Optional[datetime] = None,
        min_size: Optional[int] = None,
        max_size: Optional[int] = None,
        extra_filters: Optional[SearchFilters] = None,
    ) -> SearchFilters:
        builder = FilterBuilder()

        if filter_formats:
            builder.with_formats(filter_formats)
        if filter_tags:
            builder.with_tags(filter_tags)
        if date_start or date_end:
            builder.with_date_range(date_start, date_end)
        if min_size or max_size:
            builder.with_size_range(min_size, max_size)

        if extra_filters and extra_filters.has_any():
            if extra_filters.formats:
                builder.with_formats(extra_filters.formats)
            if extra_filters.tags:
                builder.with_tags(extra_filters.tags)
            if extra_filters.date_start or extra_filters.date_end:
                builder.with_date_range(extra_filters.date_start, extra_filters.date_end)
            if extra_filters.min_size or extra_filters.max_size:
                builder.with_size_range(extra_filters.min_size, extra_filters.max_size)
            if extra_filters.languages:
                builder.with_languages(extra_filters.languages)
            if extra_filters.publishers:
                builder.with_publishers(extra_filters.publishers)

        return builder.build()

    def search(
        self,
        query_str: str = "",
        limit: int = 50,
        filter_formats: Optional[List[str]] = None,
        filter_tags: Optional[List[str]] = None,
        date_start: Optional[datetime] = None,
        date_end: Optional[datetime] = None,
        min_size: Optional[int] = None,
        max_size: Optional[int] = None,
        filters: Optional[SearchFilters] = None,
    ) -> List[Dict]:
        has_query = bool(query_str and query_str.strip())
        search_filters = self._build_filters(
            filter_formats, filter_tags,
            date_start, date_end,
            min_size, max_size,
            filters
        )

        if not has_query and not search_filters.has_any():
            return []

        try:
            query = self._query_builder.build(query_str) if has_query else Every()

            with self.ix.searcher(weighting=scoring.BM25F(B=0.75, K1=1.5, content_B=1.0)) as searcher:
                limit_for_search = max(limit, 1000) if search_filters.has_any() else limit
                results = searcher.search(query, limit=limit_for_search, terms=True)
                hit_list = [self._hit_to_result(hit) for hit in results]

                if search_filters.has_any():
                    hit_list = filter_results(hit_list, search_filters)
                    hit_list = hit_list[:limit]

                return hit_list
        except Exception:
            return []

    def search_with_filters(
        self,
        query_str: str = "",
        filters: Optional[SearchFilters] = None,
        limit: int = 50,
    ) -> List[Dict]:
        return self.search(
            query_str=query_str,
            limit=limit,
            filters=filters,
        )

    def _hit_to_result(self, hit) -> Dict:
        result = dict(hit)
        result["score"] = hit.score
        result["matched_terms"] = list(hit.matched_terms()) if hit.matched_terms() else []
        if "publish_date" in result and result["publish_date"]:
            result["publish_date"] = result["publish_date"].strftime("%Y-%m-%d")
        if "indexed_at" in result and result["indexed_at"]:
            result["indexed_at"] = result["indexed_at"].strftime("%Y-%m-%d %H:%M:%S")
        return result

    def get_highlighted_text(
        self,
        file_path: str,
        query_str: str,
        max_chars: int = 500,
        surround: int = 50,
    ) -> Optional[str]:
        if not query_str or not query_str.strip():
            return None

        query = self._query_builder.build(query_str)

        with self.ix.searcher() as searcher:
            results = searcher.search(query, limit=1, terms=True, filter=lambda d: d["file_path"] == file_path)
            if results:
                hit = results[0]
                highlighter = Highlighter(
                    formatter=HtmlFormatter("em", classname="search-highlight"),
                    fragmenter=ContextFragmenter(max_chars, surround),
                )
                try:
                    highlighted = highlighter.highlight_hit(hit, "description") or ""
                    if not highlighted:
                        highlighted = highlighter.highlight_hit(hit, "title") or ""
                    return highlighted
                except Exception:
                    return None
        return None

    def suggest(self, prefix: str, limit: int = 10) -> List[str]:
        if len(prefix) < 2:
            return []

        suggestions = []
        try:
            with self.ix.reader() as reader:
                for field in ["title", "author", "tags"]:
                    try:
                        terms = reader.field_terms(field)
                        for term in terms:
                            if term.startswith(prefix) and term not in suggestions:
                                suggestions.append(term)
                                if len(suggestions) >= limit:
                                    return suggestions
                    except Exception:
                        continue
        except Exception:
            pass
        return suggestions

    def get_all_tags(self) -> List[str]:
        tags = set()
        try:
            with self.ix.reader() as reader:
                for term in reader.field_terms("tags"):
                    if term:
                        tags.add(term)
        except Exception:
            pass
        return sorted(tags)

    def get_all_formats(self) -> List[str]:
        formats = set()
        try:
            with self.ix.reader() as reader:
                for term in reader.field_terms("file_format"):
                    if term:
                        formats.add(term)
        except Exception:
            pass
        return sorted(formats)

    def get_stats(self) -> Dict:
        try:
            with self.ix.reader() as reader:
                return {
                    "total_docs": reader.doc_count(),
                    "has_content": sum(
                        1 for d in reader.all_stored_fields() if d.get("content_body")
                    ),
                    "index_size": sum(
                        os.path.getsize(os.path.join(self.index_dir, f))
                        for f in os.listdir(self.index_dir)
                        if os.path.isfile(os.path.join(self.index_dir, f))
                    ),
                    "last_optimize": self._meta.get("last_optimize"),
                }
        except Exception:
            return {"total_docs": 0, "has_content": 0, "index_size": 0, "last_optimize": None}

    def optimize(self) -> bool:
        try:
            self.ix.optimize()
            self._meta["last_optimize"] = datetime.now().isoformat()
            self._save_meta()
            return True
        except Exception:
            return False

    def rebuild(self, books: List[BookMeta], progress_callback: Optional[Callable] = None) -> Tuple[int, int]:
        self._meta["indexed_files"] = {}
        self._save_meta()
        self.ix.close()

        import shutil
        shutil.rmtree(self.index_dir, ignore_errors=True)
        self._init_index()

        return self.index_books(books, extract_content=True, progress_callback=progress_callback)

    def cleanup_orphans(self, existing_file_paths: List[str]) -> int:
        removed = 0
        indexed_paths = list(self._meta["indexed_files"].keys())

        for indexed_path in indexed_paths:
            if indexed_path not in existing_file_paths:
                self.remove_from_index(indexed_path)
                removed += 1

        return removed

    def close(self):
        if self.ix:
            self.ix.close()
