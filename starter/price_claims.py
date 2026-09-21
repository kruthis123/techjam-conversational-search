from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PriceClaim:
    parent_asin: str
    value: int | float
    source_field: str = "price"


def price_claim(record: dict[str, object]) -> PriceClaim | None:
    """Return a source-linked claim when the raw price is numeric."""
    value = record.get("price")
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None

    return PriceClaim(parent_asin=record["parent_asin"], value=value)
