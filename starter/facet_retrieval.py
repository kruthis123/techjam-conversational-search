from __future__ import annotations

import re

from starter.category_claims import category_claims
from starter.retrieval import RetrievalHit


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[^\W_]+", text.casefold()))


class FacetRetriever:
    def __init__(self, records: dict[str, dict[str, object]]) -> None:
        self._products_by_token: dict[str, set[str]] = {}

        for record in records.values():
            for claim in category_claims(record):
                for token in _tokens(claim.value):
                    self._products_by_token.setdefault(token, set()).add(
                        claim.parent_asin
                    )

    def search(self, query: str, depth: int) -> tuple[RetrievalHit, ...]:
        if depth <= 0:
            return ()

        scores: dict[str, int] = {}
        for token in _tokens(query):
            for parent_asin in self._products_by_token.get(token, ()):
                scores[parent_asin] = scores.get(parent_asin, 0) + 1

        ordered = sorted(scores.items(), key=lambda item: (-item[1], item[0]))
        return tuple(
            RetrievalHit(parent_asin, rank, float(score))
            for rank, (parent_asin, score) in enumerate(ordered[:depth], start=1)
        )
