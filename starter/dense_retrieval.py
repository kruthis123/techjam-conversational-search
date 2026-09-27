from __future__ import annotations

from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import normalize

from starter.retrieval import RetrievalHit


SEARCH_FIELDS = ("title", "categories", "features", "details", "store", "description")


def _text(value: object) -> str:
    if isinstance(value, dict):
        return " ".join(f"{key} {_text(item)}" for key, item in value.items())
    if isinstance(value, list):
        return " ".join(_text(item) for item in value)
    if value is None:
        return ""
    return str(value)


def _document(record: dict[str, object]) -> str:
    return " ".join(
        f"{field}: {_text(record.get(field))}" for field in SEARCH_FIELDS
    )


class DenseRetriever:
    def __init__(
        self,
        records: dict[str, dict[str, object]],
        dimensions: int = 64,
    ) -> None:
        self._parent_asins = tuple(records)
        documents = [_document(record) for record in records.values()]

        self._vectorizer = TfidfVectorizer(max_features=20_000)
        tfidf = self._vectorizer.fit_transform(documents)
        dimensions = min(dimensions, tfidf.shape[0], tfidf.shape[1])
        self._svd = TruncatedSVD(n_components=dimensions, random_state=0)
        self._vectors = normalize(self._svd.fit_transform(tfidf))

    def search(self, query: str, depth: int) -> tuple[RetrievalHit, ...]:
        if depth <= 0 or not query.strip():
            return ()

        query_tfidf = self._vectorizer.transform([query])
        if query_tfidf.nnz == 0:
            return ()

        query_vector = normalize(self._svd.transform(query_tfidf))[0]
        scores = self._vectors @ query_vector
        ordered = sorted(
            zip(self._parent_asins, scores, strict=True),
            key=lambda item: (-item[1], item[0]),
        )

        return tuple(
            RetrievalHit(parent_asin, rank, float(score))
            for rank, (parent_asin, score) in enumerate(ordered[:depth], start=1)
        )
