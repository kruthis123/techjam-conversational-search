from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


ALLOWED_ATTRIBUTES = frozenset(
    {
        "category",
        "material",
        "color",
        "size",
        "style",
        "brand",
        "budget",
        "feature",
        "use_case",
        "other",
    }
)


@dataclass(frozen=True)
class GuardedResponse:
    response: dict[str, object]
    warnings: tuple[str, ...]


class ResponseGuard:
    """Build a minimal response that always satisfies the Agent contract."""

    def __init__(self, catalog_ids: Iterable[str]) -> None:
        self.catalog_ids = frozenset(catalog_ids)

    def build(
        self,
        *,
        message: object,
        ask_attribute: object,
        recommendation_ids: Iterable[object],
        top_k: int,
    ) -> GuardedResponse:
        warnings: list[str] = []
        safe_message = message if isinstance(message, str) else ""
        if safe_message != message:
            warnings.append("response_guard:message")

        safe_attribute = ask_attribute
        if safe_attribute is not None and safe_attribute not in ALLOWED_ATTRIBUTES:
            safe_attribute = None
            warnings.append("response_guard:ask_attribute")

        limit = min(max(top_k, 0), 100)
        selected: list[dict[str, str]] = []
        seen: set[str] = set()
        for raw_id in recommendation_ids:
            if not isinstance(raw_id, str) or raw_id not in self.catalog_ids:
                warnings.append("response_guard:invalid_asin")
                continue
            if raw_id in seen:
                warnings.append("response_guard:duplicate_asin")
                continue
            selected.append({"parent_asin": raw_id})
            seen.add(raw_id)
            if len(selected) >= limit:
                break

        return GuardedResponse(
            response={
                "message": safe_message,
                "ask_attribute": safe_attribute,
                "recommendations": selected,
                "usage": {"prompt_tokens": 0, "completion_tokens": 0},
            },
            warnings=tuple(dict.fromkeys(warnings)),
        )
