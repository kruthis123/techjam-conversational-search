from __future__ import annotations

from dataclasses import dataclass

from starter.intent import ObservedClaim


@dataclass(frozen=True)
class RetrievalHit:
    parent_asin: str
    rank: int
    score: float

    def __post_init__(self) -> None:
        if self.rank < 1:
            raise ValueError("rank must be at least 1")


def build_retrieval_query(claims: tuple[ObservedClaim, ...]) -> str:
    """Join distinct active claim values in their stored order."""
    values = []
    seen = set()

    for claim in claims:
        value = claim.value.strip() if claim.value else ""
        if claim.stance == "indifferent" or not value or value in seen:
            continue
        seen.add(value)
        values.append(value)

    return " ".join(values)
