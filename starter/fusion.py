from __future__ import annotations

from dataclasses import dataclass
from math import fsum
from typing import Mapping, Sequence

from starter.retrieval import RetrievalHit


RRF_RANK_CONSTANT = 60


@dataclass(frozen=True)
class RouteEvidence:
    route_name: str
    rank: int
    score: float


@dataclass(frozen=True)
class FusedCandidate:
    parent_asin: str
    score: float
    route_evidence: tuple[RouteEvidence, ...]


def apply_candidate_budget(
    candidates: Sequence[FusedCandidate],
    limit: int,
) -> tuple[FusedCandidate, ...]:
    """Return at most limit candidates while preserving fused order."""
    if limit <= 0:
        return ()
    return tuple(candidates[:limit])


def fuse_candidates(
    route_hits: Mapping[str, Sequence[RetrievalHit]],
) -> tuple[FusedCandidate, ...]:
    """Return the complete candidate union in deterministic RRF order."""
    evidence_by_asin: dict[str, list[RouteEvidence]] = {}

    for route_name, hits in route_hits.items():
        for hit in hits:
            evidence_by_asin.setdefault(hit.parent_asin, []).append(
                RouteEvidence(route_name, hit.rank, hit.score)
            )

    candidates = (
        FusedCandidate(
            parent_asin=parent_asin,
            score=fsum(
                1 / (RRF_RANK_CONSTANT + evidence.rank) for evidence in evidence_list
            ),
            route_evidence=tuple(evidence_list),
        )
        for parent_asin, evidence_list in evidence_by_asin.items()
    )
    return tuple(sorted(candidates, key=lambda candidate: (-candidate.score, candidate.parent_asin)))
