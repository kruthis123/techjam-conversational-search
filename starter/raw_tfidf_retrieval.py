from __future__ import annotations

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import normalize

from starter.dense_retrieval import _document
from starter.retrieval import RetrievalHit


class RawTfidfRetriever:
    def __init__(self, records: dict[str, dict[str, object]]) -> None:
        self._parent_asins = tuple(records)
        documents = [_document(record) for record in records.values()]

        self._vectorizer = TfidfVectorizer(max_features=20_000)
        self._vectors = normalize(self._vectorizer.fit_transform(documents))

    def search(self, query: str, depth: int) -> tuple[RetrievalHit, ...]:
        if depth <= 0 or not query.strip():
            return ()

        query_vector = normalize(self._vectorizer.transform([query]))
        if query_vector.nnz == 0:
            return ()

        scores = (self._vectors @ query_vector.T).toarray().ravel()
        ordered = sorted(
            zip(self._parent_asins, scores, strict=True),
            key=lambda item: (-item[1], item[0]),
        )
        return tuple(
            RetrievalHit(parent_asin, rank, float(score))
            for rank, (parent_asin, score) in enumerate(ordered[:depth], start=1)
        )
