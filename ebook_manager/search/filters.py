from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any


@dataclass
class SearchFilters:
    formats: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    date_start: Optional[datetime] = None
    date_end: Optional[datetime] = None
    min_size: Optional[int] = None
    max_size: Optional[int] = None
    languages: Optional[List[str]] = None
    publishers: Optional[List[str]] = None

    def has_any(self) -> bool:
        return any([
            self.formats,
            self.tags,
            self.date_start,
            self.date_end,
            self.min_size,
            self.max_size,
            self.languages,
            self.publishers,
        ])

    def matches(self, doc: Dict[str, Any]) -> bool:
        if self.formats and doc.get("file_format") not in self.formats:
            return False

        if self.tags and doc.get("tags"):
            doc_tags = set(doc["tags"].split(","))
            if not doc_tags.intersection(set(self.tags)):
                return False

        if self.date_start or self.date_end:
            pub_date = doc.get("publish_date")
            if pub_date is None:
                return False
            if self.date_start and pub_date < self.date_start:
                return False
            if self.date_end and pub_date > self.date_end:
                return False

        if self.min_size or self.max_size:
            file_size = doc.get("file_size", 0)
            if self.min_size and file_size < self.min_size:
                return False
            if self.max_size and file_size > self.max_size:
                return False

        if self.languages and doc.get("language") not in self.languages:
            return False

        if self.publishers and doc.get("publisher") not in self.publishers:
            return False

        return True

    def to_dict(self) -> Dict[str, Any]:
        result = {}
        if self.formats:
            result["formats"] = self.formats
        if self.tags:
            result["tags"] = self.tags
        if self.date_start:
            result["date_start"] = self.date_start
        if self.date_end:
            result["date_end"] = self.date_end
        if self.min_size:
            result["min_size"] = self.min_size
        if self.max_size:
            result["max_size"] = self.max_size
        if self.languages:
            result["languages"] = self.languages
        if self.publishers:
            result["publishers"] = self.publishers
        return result

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "SearchFilters":
        return cls(
            formats=d.get("formats"),
            tags=d.get("tags"),
            date_start=d.get("date_start"),
            date_end=d.get("date_end"),
            min_size=d.get("min_size"),
            max_size=d.get("max_size"),
            languages=d.get("languages"),
            publishers=d.get("publishers"),
        )


def filter_results(results: List[Dict[str, Any]], filters: SearchFilters) -> List[Dict[str, Any]]:
    if not filters.has_any():
        return results

    return [r for r in results if filters.matches(r)]


class FilterBuilder:
    def __init__(self):
        self._filters = SearchFilters()

    def with_formats(self, formats: List[str]) -> "FilterBuilder":
        self._filters.formats = formats
        return self

    def with_tags(self, tags: List[str]) -> "FilterBuilder":
        self._filters.tags = tags
        return self

    def with_date_range(self, start: Optional[datetime] = None, end: Optional[datetime] = None) -> "FilterBuilder":
        self._filters.date_start = start
        self._filters.date_end = end
        return self

    def with_size_range(self, min_size: Optional[int] = None, max_size: Optional[int] = None) -> "FilterBuilder":
        self._filters.min_size = min_size
        self._filters.max_size = max_size
        return self

    def with_languages(self, languages: List[str]) -> "FilterBuilder":
        self._filters.languages = languages
        return self

    def with_publishers(self, publishers: List[str]) -> "FilterBuilder":
        self._filters.publishers = publishers
        return self

    def build(self) -> SearchFilters:
        return self._filters
