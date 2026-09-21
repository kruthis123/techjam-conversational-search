from __future__ import annotations

import json
from pathlib import Path


def load_catalog(path: str | Path) -> dict[str, dict[str, object]]:
    """Load raw catalog records keyed by their unique ``parent_asin``."""
    catalog_path = Path(path)
    records: dict[str, dict[str, object]] = {}

    with catalog_path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue

            try:
                record = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(
                    f"{catalog_path}: line {line_number}: malformed JSON: {error.msg}"
                ) from None

            if not isinstance(record, dict):
                raise ValueError(
                    f"{catalog_path}: line {line_number}: expected a JSON object"
                )

            parent_asin = record.get("parent_asin")
            if not isinstance(parent_asin, str) or not parent_asin.strip():
                raise ValueError(
                    f"{catalog_path}: line {line_number}: "
                    "parent_asin must be a non-empty string"
                )
            if parent_asin in records:
                raise ValueError(
                    f"{catalog_path}: line {line_number}: "
                    f"duplicate parent_asin {parent_asin!r}"
                )

            records[parent_asin] = record

    return records
