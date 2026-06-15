import re
from typing import List, Optional, Dict, Any
from whoosh.qparser import QueryParser, MultifieldParser, PhrasePlugin, FuzzyTermPlugin
from whoosh.qparser import syntax
from whoosh.query import Every, And, Or, Term, Prefix


class QueryBuilder:
    DEFAULT_SEARCH_FIELDS = [
        "title", "author", "description",
        "content_body", "tags", "publisher"
    ]

    FIELD_BOOSTS = {
        "title": 3.0,
        "author": 2.0,
        "description": 1.5,
        "tags": 1.2,
        "publisher": 1.0,
        "content_body": 1.0,
    }

    def __init__(self, schema):
        self._schema = schema
        self._field_boosts = dict(self.FIELD_BOOSTS)

    def build(self, query_str: str, fieldnames: Optional[List[str]] = None) -> Any:
        if not query_str or not query_str.strip():
            return Every()

        fields = fieldnames or self.DEFAULT_SEARCH_FIELDS

        parser = MultifieldParser(
            fields,
            schema=self._schema,
            group=syntax.OrGroup,
            fieldboosts=self._field_boosts,
        )
        parser.add_plugin(PhrasePlugin())
        parser.add_plugin(FuzzyTermPlugin())

        return parser.parse(query_str)

    def build_field_query(self, field: str, query_str: str) -> Any:
        if not query_str or not query_str.strip():
            return Every()

        parser = QueryParser(field, schema=self._schema)
        parser.add_plugin(PhrasePlugin())
        parser.add_plugin(FuzzyTermPlugin())
        return parser.parse(query_str)

    def build_combined_query(
        self,
        query_str: str = "",
        field_queries: Optional[Dict[str, str]] = None,
        fieldnames: Optional[List[str]] = None,
    ) -> Any:
        queries = []

        if query_str and query_str.strip():
            queries.append(self.build(query_str, fieldnames))

        if field_queries:
            for field, qs in field_queries.items():
                if qs and qs.strip():
                    queries.append(self.build_field_query(field, qs))

        if not queries:
            return Every()

        if len(queries) == 1:
            return queries[0]

        return And(queries)

    def set_field_boost(self, field: str, boost: float):
        self._field_boosts[field] = boost

    def suggest_query(self, prefix: str, field: str = "title", limit: int = 10) -> List[str]:
        if not prefix or len(prefix) < 2:
            return []
        return []


def build_advanced_query_string(
    title: str = "",
    author: str = "",
    publisher: str = "",
    description: str = "",
    isbn: str = "",
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
    if isbn and isbn.strip():
        parts.append(f"isbn:({isbn.strip()})")

    return " AND ".join(parts)


def extract_keywords(query_str: str) -> List[str]:
    if not query_str:
        return []

    query_str = re.sub(r'[~*"()]', ' ', query_str)
    query_str = re.sub(r'\b(AND|OR|NOT)\b', ' ', query_str, flags=re.IGNORECASE)
    query_str = re.sub(r'\w+:', ' ', query_str)
    keywords = [k.strip() for k in query_str.split() if k.strip() and len(k.strip()) >= 2]
    return keywords


def has_content_query(query_str: str) -> bool:
    if not query_str or not query_str.strip():
        return False

    if query_str.strip().startswith("title:") or \
       query_str.strip().startswith("author:") or \
       query_str.strip().startswith("publisher:") or \
       query_str.strip().startswith("description:") or \
       query_str.strip().startswith("tags:") or \
       query_str.strip().startswith("isbn:"):
        return True

    return bool(query_str.strip())


def create_every_query():
    return Every()


def is_every_query(query) -> bool:
    return isinstance(query, Every)
