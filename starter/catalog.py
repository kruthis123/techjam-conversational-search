from __future__ import annotations

import html
import json
import math
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType
from typing import Iterable, Mapping


SCHEMA_VERSION = "1"
FACET_VERSION = "1"

CategoryPath = tuple[str, ...]

WHITESPACE_RE = re.compile(r"\s+")

COLOR_ALIASES: dict[str, tuple[str, ...]] = {
    "black": ("black",),
    "white": ("white",),
    "gray": ("gray", "grey"),
    "red": ("red",),
    "blue": ("blue",),
    "green": ("green",),
    "yellow": ("yellow",),
    "orange": ("orange",),
    "purple": ("purple",),
    "pink": ("pink",),
    "brown": ("brown",),
    "beige": ("beige",),
    "tan": ("tan",),
    "navy": ("navy", "navy blue"),
    "teal": ("teal",),
    "turquoise": ("turquoise",),
    "burgundy": ("burgundy",),
    "maroon": ("maroon",),
    "ivory": ("ivory",),
    "cream": ("cream",),
    "khaki": ("khaki",),
    "gold": ("gold",),
    "silver": ("silver",),
    "rose gold": ("rose gold",),
    "multicolor": ("multicolor", "multi color", "multi-color"),
}

MATERIAL_ALIASES: dict[str, tuple[str, ...]] = {
    "cotton": ("cotton",),
    "polyester": ("polyester",),
    "spandex": ("spandex", "elastane"),
    "nylon": ("nylon",),
    "leather": ("leather",),
    "faux leather": ("faux leather", "pu leather", "vegan leather"),
    "suede": ("suede",),
    "wool": ("wool",),
    "silk": ("silk",),
    "satin": ("satin",),
    "velvet": ("velvet",),
    "denim": ("denim",),
    "linen": ("linen",),
    "rayon": ("rayon",),
    "viscose": ("viscose",),
    "modal": ("modal",),
    "acrylic": ("acrylic",),
    "rubber": ("rubber",),
    "eva": ("eva", "ethylene vinyl acetate"),
    "polyurethane": ("polyurethane",),
    "stainless steel": ("stainless steel",),
    "gold": ("gold",),
    "silver": ("silver",),
    "gemstone": ("gemstone",),
}


def normalize_text(value: object) -> str:
    """Return a clean, single-line string without changing the source record."""
    if value is None:
        return ""
    text = unicodedata.normalize("NFKC", html.unescape(str(value)))
    return WHITESPACE_RE.sub(" ", text).strip()


def normalize_string_list(value: object) -> tuple[str, ...]:
    if value is None:
        return ()
    items = value if isinstance(value, (list, tuple)) else [value]
    normalized: list[str] = []
    seen: set[str] = set()
    for item in items:
        text = normalize_text(item)
        key = text.casefold()
        if text and key not in seen:
            normalized.append(text)
            seen.add(key)
    return tuple(normalized)


def normalize_category_path(value: object) -> CategoryPath:
    """Normalize category labels while preserving their catalog order."""
    if not isinstance(value, (list, tuple)):
        return ()
    return tuple(text for item in value if (text := normalize_text(item)))


def normalize_float(value: object) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def normalize_int(value: object) -> int | None:
    number = normalize_float(value)
    return int(number) if number is not None and number >= 0 else None


def flatten_details(value: object, prefix: str = "") -> tuple[tuple[str, str], ...]:
    """Flatten nested detail dictionaries into stable dotted keys."""
    if not isinstance(value, dict):
        return ()

    flattened: list[tuple[str, str]] = []
    for raw_key, raw_value in value.items():
        key = normalize_text(raw_key)
        if not key:
            continue
        full_key = f"{prefix}.{key}" if prefix else key
        if isinstance(raw_value, dict):
            flattened.extend(flatten_details(raw_value, full_key))
            continue
        if isinstance(raw_value, (list, tuple)):
            text = ", ".join(filter(None, (normalize_text(item) for item in raw_value)))
        else:
            text = normalize_text(raw_value)
        if text:
            flattened.append((full_key, text))
    return tuple(flattened)


def _compile_alias_pattern(
    aliases: Mapping[str, tuple[str, ...]],
) -> tuple[re.Pattern[str], dict[str, str]]:
    alias_to_value: dict[str, str] = {}
    expressions: list[str] = []
    for canonical, values in aliases.items():
        for alias in values:
            normalized = normalize_text(alias).casefold()
            alias_to_value[normalized.replace("-", " ")] = canonical
            expression = re.escape(normalized).replace(r"\ ", r"[\s-]+")
            expressions.append(expression)
    expressions.sort(key=len, reverse=True)
    return (
        re.compile(r"(?<![a-z0-9])(?:" + "|".join(expressions) + r")(?![a-z0-9])", re.I),
        alias_to_value,
    )


COLOR_PATTERN, COLOR_LOOKUP = _compile_alias_pattern(COLOR_ALIASES)
MATERIAL_PATTERN, MATERIAL_LOOKUP = _compile_alias_pattern(MATERIAL_ALIASES)


def extract_facets(
    text: str,
    pattern: re.Pattern[str],
    lookup: Mapping[str, str],
    canonical_order: Iterable[str],
) -> tuple[str, ...]:
    found = {
        lookup[normalize_text(match.group().replace("-", " ")).casefold()]
        for match in pattern.finditer(text)
    }
    return tuple(value for value in canonical_order if value in found)


def _join_nonempty(parts: Iterable[str], separator: str = " ") -> str:
    return separator.join(part for part in parts if part)


def _brand_from_details(details: tuple[tuple[str, str], ...], store: str) -> str:
    for key, value in details:
        if key.rsplit(".", 1)[-1].casefold() == "brand":
            return value
    return store


@dataclass(frozen=True)
class Product:
    parent_asin: str
    title: str
    categories: CategoryPath
    features: tuple[str, ...]
    description: tuple[str, ...]
    details: tuple[tuple[str, str], ...]
    price: float | None
    average_rating: float | None
    rating_number: int | None
    store: str
    brand: str
    materials: tuple[str, ...]
    colors: tuple[str, ...]

    @property
    def categories_text(self) -> str:
        return " > ".join(self.categories)

    @property
    def features_text(self) -> str:
        return " ".join(self.features)

    @property
    def description_text(self) -> str:
        return " ".join(self.description)

    @property
    def details_text(self) -> str:
        return " ".join(f"{key}: {value}" for key, value in self.details)

    @property
    def lexical_text(self) -> str:
        return _join_nonempty(
            (
                self.title,
                self.categories_text,
                self.brand,
                self.features_text,
                self.details_text,
                self.description_text,
            )
        )

    @property
    def dense_text(self) -> str:
        return _join_nonempty(
            (
                f"Title: {self.title}" if self.title else "",
                f"Category: {self.categories_text}" if self.categories else "",
                f"Brand: {self.brand}" if self.brand else "",
                f"Features: {self.features_text}" if self.features else "",
                f"Description: {self.description_text}" if self.description else "",
            ),
            separator="\n",
        )

    @classmethod
    def from_source(cls, record: Mapping[str, object]) -> Product:
        parent_asin = normalize_text(record.get("parent_asin"))
        if not parent_asin:
            raise ValueError("product is missing parent_asin")

        title = normalize_text(record.get("title"))
        categories = normalize_category_path(record.get("categories"))
        features = normalize_string_list(record.get("features"))
        description = normalize_string_list(record.get("description"))
        details = flatten_details(record.get("details"))
        store = normalize_text(record.get("store"))
        brand = _brand_from_details(details, store)
        facet_text = _join_nonempty(
            (
                title,
                " ".join(features),
                " ".join(description),
                " ".join(value for _, value in details),
            )
        )

        return cls(
            parent_asin=parent_asin,
            title=title,
            categories=categories,
            features=features,
            description=description,
            details=details,
            price=normalize_float(record.get("price")),
            average_rating=normalize_float(record.get("average_rating")),
            rating_number=normalize_int(record.get("rating_number")),
            store=store,
            brand=brand,
            materials=extract_facets(
                facet_text, MATERIAL_PATTERN, MATERIAL_LOOKUP, MATERIAL_ALIASES
            ),
            colors=extract_facets(facet_text, COLOR_PATTERN, COLOR_LOOKUP, COLOR_ALIASES),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "parent_asin": self.parent_asin,
            "title": self.title,
            "categories": list(self.categories),
            "features": list(self.features),
            "description": list(self.description),
            "details": [list(item) for item in self.details],
            "price": self.price,
            "average_rating": self.average_rating,
            "rating_number": self.rating_number,
            "store": self.store,
            "brand": self.brand,
            "materials": list(self.materials),
            "colors": list(self.colors),
        }

    @classmethod
    def from_dict(cls, record: Mapping[str, object]) -> Product:
        details_value = record.get("details", [])
        details = tuple(
            (normalize_text(item[0]), normalize_text(item[1]))
            for item in details_value
            if isinstance(item, (list, tuple)) and len(item) == 2
        )
        return cls(
            parent_asin=normalize_text(record.get("parent_asin")),
            title=normalize_text(record.get("title")),
            categories=normalize_category_path(record.get("categories")),
            features=normalize_string_list(record.get("features")),
            description=normalize_string_list(record.get("description")),
            details=details,
            price=normalize_float(record.get("price")),
            average_rating=normalize_float(record.get("average_rating")),
            rating_number=normalize_int(record.get("rating_number")),
            store=normalize_text(record.get("store")),
            brand=normalize_text(record.get("brand")),
            materials=normalize_string_list(record.get("materials")),
            colors=normalize_string_list(record.get("colors")),
        )


@dataclass(frozen=True)
class CategoryOntology:
    children_by_path: Mapping[CategoryPath, tuple[CategoryPath, ...]]
    product_ids_by_path: Mapping[CategoryPath, tuple[str, ...]]

    @property
    def paths(self) -> tuple[CategoryPath, ...]:
        return tuple(self.product_ids_by_path)

    def children(self, path: CategoryPath = ()) -> tuple[CategoryPath, ...]:
        return self.children_by_path.get(path, ())

    def product_ids(self, path: CategoryPath = ()) -> tuple[str, ...]:
        return self.product_ids_by_path.get(path, ())

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": SCHEMA_VERSION,
            "nodes": [
                {
                    "path": list(path),
                    "children": [list(child) for child in self.children(path)],
                    "product_ids": list(product_ids),
                }
                for path, product_ids in self.product_ids_by_path.items()
            ],
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, object]) -> CategoryOntology:
        if value.get("schema_version") != SCHEMA_VERSION:
            raise ValueError("ontology schema version does not match")
        children: dict[CategoryPath, tuple[CategoryPath, ...]] = {}
        products: dict[CategoryPath, tuple[str, ...]] = {}
        for node in value.get("nodes", []):
            if not isinstance(node, dict):
                continue
            path = normalize_category_path(node.get("path"))
            child_paths = tuple(
                normalize_category_path(child) for child in node.get("children", [])
            )
            product_ids = normalize_string_list(node.get("product_ids"))
            children[path] = child_paths
            products[path] = product_ids
        return cls(MappingProxyType(children), MappingProxyType(products))


def build_category_ontology(products: Iterable[Product]) -> CategoryOntology:
    children: dict[CategoryPath, list[CategoryPath]] = {(): []}
    product_ids: dict[CategoryPath, list[str]] = {(): []}

    for product in products:
        product_ids[()].append(product.parent_asin)
        parent: CategoryPath = ()
        for depth in range(1, len(product.categories) + 1):
            path = product.categories[:depth]
            product_ids.setdefault(path, []).append(product.parent_asin)
            children.setdefault(path, [])
            siblings = children.setdefault(parent, [])
            if path not in siblings:
                siblings.append(path)
            parent = path

    return CategoryOntology(
        children_by_path=MappingProxyType(
            {path: tuple(paths) for path, paths in children.items()}
        ),
        product_ids_by_path=MappingProxyType(
            {path: tuple(ids) for path, ids in product_ids.items()}
        ),
    )


@dataclass(frozen=True)
class Catalog:
    products: tuple[Product, ...]
    ontology: CategoryOntology
    schema_version: str = SCHEMA_VERSION
    by_id: Mapping[str, Product] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        products_by_id: dict[str, Product] = {}
        for product in self.products:
            if not product.parent_asin:
                raise ValueError("product is missing parent_asin")
            if product.parent_asin in products_by_id:
                raise ValueError(f"duplicate parent_asin: {product.parent_asin}")
            products_by_id[product.parent_asin] = product
        object.__setattr__(self, "by_id", MappingProxyType(products_by_id))

    def __len__(self) -> int:
        return len(self.products)

    def get(self, parent_asin: str) -> Product | None:
        return self.by_id.get(parent_asin)


def catalog_from_products(
    products: Iterable[Product], ontology: CategoryOntology | None = None
) -> Catalog:
    product_tuple = tuple(products)
    return Catalog(product_tuple, ontology or build_category_ontology(product_tuple))


def load_source_catalog(path: str | Path) -> Catalog:
    source_path = Path(path)
    products: list[Product] = []
    seen: set[str] = set()

    with source_path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
                product = Product.from_source(record)
            except (json.JSONDecodeError, TypeError, ValueError) as error:
                raise ValueError(f"invalid product at line {line_number}: {error}") from error
            if product.parent_asin in seen:
                raise ValueError(
                    f"duplicate parent_asin at line {line_number}: {product.parent_asin}"
                )
            seen.add(product.parent_asin)
            products.append(product)

    return catalog_from_products(products)
