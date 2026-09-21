from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CategoryClaim:
    parent_asin: str
    value: str
    source_field: str = "categories"


def category_claims(record: dict[str, object]) -> tuple[CategoryClaim, ...]:
    """Return ordered, normalized claims for the raw categories."""
    claims = []
    seen = set()

    for category in record["categories"]:
        value = category.strip().casefold()
        if value in seen:
            continue
        seen.add(value)
        claims.append(CategoryClaim(record["parent_asin"], value))

    return tuple(claims)
