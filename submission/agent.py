"""Official submission entry point."""

from __future__ import annotations

import os
import sys
from pathlib import Path

BUNDLE_ROOT = Path(__file__).resolve().parent
SOURCE_ROOT = BUNDLE_ROOT if (BUNDLE_ROOT / "starter").is_dir() else BUNDLE_ROOT.parent
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from starter.agent import Agent as CoreAgent


DEFAULT_MODEL_DIRECTORY = (
    SOURCE_ROOT / "models" / "cross-encoder-ms-marco-MiniLM-L4-v2"
)


class Agent(CoreAgent):
    """Resolve bundled assets, then delegate to the tested core agent."""

    def __init__(self, catalog_path: str | Path | None = None, **kwargs: object) -> None:
        resolved_catalog = catalog_path or os.environ.get(
            "TECHJAM_CATALOG_PATH", "data/catalog.jsonl"
        )
        kwargs.setdefault("reranker_model_directory", DEFAULT_MODEL_DIRECTORY)
        super().__init__(catalog_path=resolved_catalog, **kwargs)


__all__ = ["Agent"]
