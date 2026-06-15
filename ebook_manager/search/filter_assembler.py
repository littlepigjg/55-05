from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import date


@dataclass
class AdvancedSearchCriteria:
    title: Optional[str] = None
    author: Optional[str] = None
    publisher: Optional[str] = None
    description: Optional[str] = None
    search_content: bool = True
    formats: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    date_start: Optional[date] = None
    date_end: Optional[date] = None
    min_size_bytes: Optional[int] = None
    max_size_bytes: Optional[int] = None
    languages: List[str] = field(default_factory=list)
    isbns: List[str] = field(default_factory=list)

    def has_any_keyword(self) -> bool:
        return any([
            self.title,
            self.author,
            self.publisher,
            self.description,
        ])

    def has_any_filter(self) -> bool:
        return any([
            self.formats,
            self.tags,
            self.date_start,
            self.date_end,
            self.min_size_bytes,
            self.max_size_bytes,
            self.languages,
            self.isbns,
        ])

    def has_any(self) -> bool:
        return self.has_any_keyword() or self.has_any_filter()

    def to_query_string(self) -> str:
        parts = []
        if self.title:
            parts.append(f"title:({self.title.strip()})")
        if self.author:
            parts.append(f"author:({self.author.strip()})")
        if self.publisher:
            parts.append(f"publisher:({self.publisher.strip()})")
        if self.description:
            parts.append(f"description:({self.description.strip()})")
        return " AND ".join(parts)

    def to_search_params(self) -> Dict[str, Any]:
        return {
            "filter_formats": self.formats if self.formats else None,
            "filter_tags": self.tags if self.tags else None,
            "date_start": self.date_start,
            "date_end": self.date_end,
            "min_size": self.min_size_bytes,
            "max_size": self.max_size_bytes,
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query": self.to_query_string(),
            "formats": self.formats,
            "tags": self.tags,
            "date_start": self.date_start,
            "date_end": self.date_end,
            "min_size": self.min_size_bytes,
            "max_size": self.max_size_bytes,
            "languages": self.languages,
            "isbns": self.isbns,
            "search_content": self.search_content,
            "criteria": {
                "title": self.title,
                "author": self.author,
                "publisher": self.publisher,
                "description": self.description,
            }
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "AdvancedSearchCriteria":
        criteria = d.get("criteria", {})
        return cls(
            title=criteria.get("title"),
            author=criteria.get("author"),
            publisher=criteria.get("publisher"),
            description=criteria.get("description"),
            search_content=d.get("search_content", True),
            formats=d.get("formats", []),
            tags=d.get("tags", []),
            date_start=d.get("date_start"),
            date_end=d.get("date_end"),
            min_size_bytes=d.get("min_size"),
            max_size_bytes=d.get("max_size"),
            languages=d.get("languages", []),
            isbns=d.get("isbns", []),
        )


class FilterAssembler:
    @staticmethod
    def build_query_string(
        title: str = "",
        author: str = "",
        publisher: str = "",
        description: str = "",
    ) -> str:
        parts = []
        if title and title.strip():
            parts.append(f"title:({title.strip()})")
        if author and author.strip():
            parts.append(f"author:({author.strip()})")
        if publisher and publisher.strip():
            parts.append(f"publisher:({publisher.strip()})")
        if description and description.strip():
            parts.append(f"description:({description.strip()})")
        return " AND ".join(parts)

    @staticmethod
    def collect_selected_items(list_widget) -> List[str]:
        selected = []
        for i in range(list_widget.count()):
            item = list_widget.item(i)
            if item.isSelected():
                data = item.data(32)
                if data is not None:
                    selected.append(data)
        return selected

    @staticmethod
    def parse_date_checkbox(checkbox, date_edit) -> Optional[date]:
        if checkbox.isChecked():
            return date_edit.date().toPyDate()
        return None

    @staticmethod
    def parse_size_checkbox(checkbox, spin_box, multiplier: int = 1024 * 1024) -> Optional[int]:
        if checkbox.isChecked():
            return spin_box.value() * multiplier
        return None

    @staticmethod
    def assemble_filters(
        title: str = "",
        author: str = "",
        publisher: str = "",
        description: str = "",
        search_content: bool = True,
        selected_formats: Optional[List[str]] = None,
        selected_tags: Optional[List[str]] = None,
        date_start: Optional[date] = None,
        date_end: Optional[date] = None,
        min_size: Optional[int] = None,
        max_size: Optional[int] = None,
    ) -> Dict[str, Any]:
        query = FilterAssembler.build_query_string(title, author, publisher, description)

        return {
            "query": query,
            "formats": selected_formats or [],
            "tags": selected_tags or [],
            "date_start": date_start,
            "date_end": date_end,
            "min_size": min_size,
            "max_size": max_size,
        }

    @staticmethod
    def assemble_criteria(
        title: str = "",
        author: str = "",
        publisher: str = "",
        description: str = "",
        search_content: bool = True,
        formats: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
        date_start: Optional[date] = None,
        date_end: Optional[date] = None,
        min_size_bytes: Optional[int] = None,
        max_size_bytes: Optional[int] = None,
        languages: Optional[List[str]] = None,
        isbns: Optional[List[str]] = None,
    ) -> AdvancedSearchCriteria:
        return AdvancedSearchCriteria(
            title=title.strip() if title else None,
            author=author.strip() if author else None,
            publisher=publisher.strip() if publisher else None,
            description=description.strip() if description else None,
            search_content=search_content,
            formats=formats or [],
            tags=tags or [],
            date_start=date_start,
            date_end=date_end,
            min_size_bytes=min_size_bytes,
            max_size_bytes=max_size_bytes,
            languages=languages or [],
            isbns=isbns or [],
        )


class SelectedItemsTracker:
    def __init__(self):
        self._selected: set = set()

    def save(self, list_widget) -> None:
        self._selected.clear()
        for i in range(list_widget.count()):
            item = list_widget.item(i)
            if item.isSelected():
                data = item.data(32)
                if data is not None:
                    self._selected.add(data)

    def update(self, list_widget) -> None:
        visible_items = set()
        for i in range(list_widget.count()):
            item = list_widget.item(i)
            data = item.data(32)
            if data is not None:
                visible_items.add(data)
                if item.isSelected():
                    self._selected.add(data)
                else:
                    self._selected.discard(data)

        for item in list(self._selected):
            if item not in visible_items:
                pass

    def restore(self, list_widget) -> None:
        for i in range(list_widget.count()):
            item = list_widget.item(i)
            data = item.data(32)
            if data is not None and data in self._selected:
                item.setSelected(True)
            else:
                item.setSelected(False)

    def add(self, value: str) -> None:
        self._selected.add(value)

    def remove(self, value: str) -> None:
        self._selected.discard(value)

    def clear(self) -> None:
        self._selected.clear()

    def get_selected(self) -> List[str]:
        return sorted(self._selected)

    def __contains__(self, item: str) -> bool:
        return item in self._selected

    def __len__(self) -> int:
        return len(self._selected)


def convert_mb_to_bytes(mb: float) -> int:
    return int(mb * 1024 * 1024)


def convert_bytes_to_mb(bytes_val: int) -> float:
    return bytes_val / (1024 * 1024)


def format_file_size(bytes_val: int) -> str:
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if bytes_val < 1024:
            return f"{bytes_val:.1f} {unit}"
        bytes_val /= 1024
    return f"{bytes_val:.1f} PB"
