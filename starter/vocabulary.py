from __future__ import annotations

import re
from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping

from starter.catalog import (
    CategoryPath,
    flatten_details,
    normalize_category_path,
    normalize_text,
)


WORD_RE = re.compile(r"[a-z0-9]+")
CATEGORY_SYNONYMS = {
    "house shoe": "slipper",
    "house shoes": "slipper",
    "sneaker": "athletic shoe",
    "sneakers": "athletic shoe",
    "tee": "t shirt",
    "tees": "t shirt",
}
GENERIC_CATEGORY_LABELS = {
    "clothing",
    "clothing shoe jewelry",
    "clothing shoes jewelry",
    "women",
    "men",
    "girls",
    "boys",
    "baby",
}
GENERIC_BRAND_ALIASES = {
    "amazon",
    "brand",
    "clothing",
    "fashion",
    "for",
    "generic",
    "jewelry",
    "men",
    "outdoor",
    "shoes",
    "store",
    "the",
    "women",
}


def normalize_phrase(value: object) -> str:
    text = normalize_text(value).casefold()
    replacements = {
        "women's": "women",
        "womens": "women",
        "men's": "men",
        "mens": "men",
        "girl's": "girls",
        "boy's": "boys",
        "t-shirts": "t shirts",
        "t-shirt": "t shirt",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return " ".join(WORD_RE.findall(text))


def contains_phrase(text: str, phrase: str) -> bool:
    return bool(re.search(rf"(?<![a-z0-9]){re.escape(phrase)}(?![a-z0-9])", text))


def _phrase_forms(value: str) -> tuple[str, ...]:
    normalized = normalize_phrase(value)
    singular_words: list[str] = []
    for word in normalized.split():
        if word.endswith("ies") and len(word) > 4:
            word = word[:-3] + "y"
        elif word.endswith("s") and not word.endswith(("ss", "us")) and len(word) > 3:
            word = word[:-1]
        singular_words.append(word)
    singular = " ".join(singular_words)
    return (normalized, singular) if singular and singular != normalized else (normalized,)


@dataclass(frozen=True)
class CatalogVocabulary:
    category_paths: tuple[CategoryPath, ...]
    paths_by_alias: Mapping[str, tuple[CategoryPath, ...]]
    maximum_category_words: int
    brands_by_alias: Mapping[str, str]
    implicit_brands_by_alias: Mapping[str, str]
    maximum_brand_words: int

    def match_category(
        self,
        message: str,
        audience: str | None = None,
    ) -> CategoryPath | None:
        normalized = normalize_phrase(message)
        for source, replacement in CATEGORY_SYNONYMS.items():
            normalized = normalized.replace(source, replacement)

        words = normalized.split()
        matched_aliases: list[str] = []
        for width in range(1, min(self.maximum_category_words, len(words)) + 1):
            for start in range(len(words) - width + 1):
                alias = " ".join(words[start : start + width])
                if (
                    alias in self.paths_by_alias
                    and alias not in GENERIC_CATEGORY_LABELS
                    and alias not in matched_aliases
                ):
                    matched_aliases.append(alias)
        if not matched_aliases:
            return None

        candidates: dict[CategoryPath, int] = {}
        for alias in matched_aliases:
            for path in self.paths_by_alias[alias]:
                score = 3 if alias in _phrase_forms(path[-1]) else 1
                candidates[path] = candidates.get(path, 0) + score

        if audience:
            matching_audience = {
                path: score + 4
                for path, score in candidates.items()
                if any(normalize_phrase(part) == audience for part in path)
            }
            if matching_audience:
                candidates = matching_audience

        path_order = {path: index for index, path in enumerate(self.category_paths)}
        return max(
            candidates,
            key=lambda path: (candidates[path], len(path), -path_order[path]),
        )

    def match_brand(self, message: str) -> str | None:
        words = normalize_phrase(message).split()
        explicit_brand_cue = bool(re.search(r"\bbrand\b", message, re.I))
        brands = self.brands_by_alias if explicit_brand_cue else self.implicit_brands_by_alias
        best: tuple[int, str] | None = None
        for width in range(1, min(self.maximum_brand_words, len(words)) + 1):
            for start in range(len(words) - width + 1):
                phrase = " ".join(words[start : start + width])
                brand = brands.get(phrase)
                if brand and not explicit_brand_cue and not re.search(
                    rf"(?<![A-Za-z0-9]){re.escape(brand)}(?![A-Za-z0-9])",
                    message,
                ):
                    continue
                if brand and (best is None or width > best[0]):
                    best = (width, brand)
        return best[1] if best else None


class CatalogVocabularyBuilder:
    def __init__(self) -> None:
        self._paths: dict[CategoryPath, None] = {}
        self._brands: dict[str, str] = {}
        self._brand_counts: dict[str, int] = {}

    def observe(self, product: Mapping[str, object]) -> None:
        path = normalize_category_path(product.get("categories"))
        if path:
            for depth in range(1, len(path) + 1):
                self._paths.setdefault(path[:depth], None)

        brands = [normalize_text(product.get("store"))]
        for key, value in flatten_details(product.get("details")):
            if key.rsplit(".", 1)[-1].casefold() == "brand":
                brands.append(value)
        observed_aliases: set[str] = set()
        for brand in brands:
            alias = normalize_phrase(brand)
            word_count = len(alias.split())
            if (
                brand
                and alias not in GENERIC_BRAND_ALIASES
                and 1 <= word_count <= 5
                and len(alias) <= 50
                and alias not in observed_aliases
            ):
                self._brands.setdefault(alias, brand)
                self._brand_counts[alias] = self._brand_counts.get(alias, 0) + 1
                observed_aliases.add(alias)

    def build(self) -> CatalogVocabulary:
        paths_by_alias: dict[str, list[CategoryPath]] = {}
        for path in self._paths:
            for label in path:
                for alias in _phrase_forms(label):
                    paths = paths_by_alias.setdefault(alias, [])
                    if path not in paths:
                        paths.append(path)
        frozen_paths = {alias: tuple(paths) for alias, paths in paths_by_alias.items()}
        implicit_brands = {
            alias: brand
            for alias, brand in self._brands.items()
            if self._brand_counts.get(alias, 0) >= 2
        }
        return CatalogVocabulary(
            category_paths=tuple(self._paths),
            paths_by_alias=MappingProxyType(frozen_paths),
            maximum_category_words=max(
                (len(alias.split()) for alias in frozen_paths),
                default=1,
            ),
            brands_by_alias=MappingProxyType(dict(self._brands)),
            implicit_brands_by_alias=MappingProxyType(implicit_brands),
            maximum_brand_words=max(
                (len(alias.split()) for alias in self._brands),
                default=1,
            ),
        )
