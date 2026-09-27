from __future__ import annotations

import re
import sqlite3

from starter.retrieval import RetrievalHit


SEARCH_FIELDS = ("title", "categories", "features", "details", "store", "description")


def _text(value: object) -> str:
    if isinstance(value, dict):
        return " ".join(
            f"{key} {_text(item)}" for key, item in value.items()
        )
    if isinstance(value, list):
        return " ".join(_text(item) for item in value)
    if value is None:
        return ""
    return str(value)


class LexicalRetriever:
    def __init__(self, records: dict[str, dict[str, object]]) -> None:
        self._connection = sqlite3.connect(":memory:")
        self._connection.execute(
            """
            CREATE VIRTUAL TABLE products USING fts5(
                parent_asin UNINDEXED,
                title,
                categories,
                features,
                details,
                store,
                description
            )
            """
        )
        rows = (
            (parent_asin, *(_text(record.get(field)) for field in SEARCH_FIELDS))
            for parent_asin, record in records.items()
        )
        self._connection.executemany(
            "INSERT INTO products VALUES (?, ?, ?, ?, ?, ?, ?)",
            rows,
        )

    def search(self, query: str, depth: int) -> tuple[RetrievalHit, ...]:
        if depth <= 0:
            return ()

        tokens = re.findall(r"[^\W_]+", query.casefold())
        if not tokens:
            return ()

        match_query = " OR ".join(f'"{token}"' for token in tokens)
        rows = self._connection.execute(
            """
            SELECT parent_asin, bm25(products) AS score
            FROM products
            WHERE products MATCH ?
            ORDER BY score, parent_asin
            LIMIT ?
            """,
            (match_query, depth),
        )

        return tuple(
            RetrievalHit(parent_asin, rank, -score)
            for rank, (parent_asin, score) in enumerate(rows, start=1)
        )
