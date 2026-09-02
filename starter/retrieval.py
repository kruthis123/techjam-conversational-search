from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass
from typing import Mapping, Sequence

from starter.catalog import Product
from starter.dense import DenseResult
from starter.state import ActiveSlotView, StateView
from starter.vocabulary import normalize_phrase


TOKEN_RE = re.compile(r"[a-z0-9]+", re.IGNORECASE)
STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "but", "by", "for", "from",
    "i", "in", "is", "it", "me", "my", "of", "on", "or", "please", "some",
    "that", "the", "this", "to", "want", "with", "would", "you", "looking",
}
RETRIEVAL_NAMES = ("single_bm25", "multi_route_rrf", "multi_route_structured")
AUDIENCES = {"women", "men", "girls", "boys", "baby", "unisex"}
PRICE_SLOTS = {"min_price", "max_price", "target_price"}

BASELINE_WEIGHTS = (0.0, 6.0, 4.0, 2.5, 2.5, 1.5, 1.0)
ROUTE_WEIGHTS = {
    "current_message": BASELINE_WEIGHTS,
    "category": (0.0, 5.0, 8.0, 0.5, 0.5, 0.5, 0.2),
    "latest_constraint": (0.0, 6.0, 3.0, 4.0, 4.0, 2.0, 2.0),
    "complete_state": (0.0, 6.0, 5.0, 3.0, 3.0, 2.0, 2.0),
    "title_heavy": (0.0, 9.0, 5.0, 1.0, 1.0, 2.0, 0.5),
    "feature_heavy": (0.0, 3.0, 2.0, 7.0, 6.0, 1.0, 5.0),
}


def lexical_terms(text: str) -> tuple[str, ...]:
    terms: list[str] = []
    seen: set[str] = set()
    for token in TOKEN_RE.findall(text):
        value = token.casefold()
        if value in STOPWORDS or len(value) <= 1:
            continue
        if value not in seen:
            terms.append(value)
            seen.add(value)
    return tuple(terms[:40])


@dataclass(frozen=True)
class LexicalQuery:
    name: str
    text: str
    terms: tuple[str, ...]
    field_weights: tuple[float, ...]


@dataclass(frozen=True)
class RouteResult:
    name: str
    candidate_ids: tuple[str, ...]
    scores: tuple[float, ...]
    warning: str | None = None


@dataclass(frozen=True)
class CandidateEvidence:
    parent_asin: str
    fused_score: float
    route_ranks: Mapping[str, int]
    route_contributions: Mapping[str, float]
    compatibility_score: float = 0.0
    matched_constraints: tuple[str, ...] = ()
    contradicted_constraints: tuple[str, ...] = ()


@dataclass(frozen=True)
class RetrievalResult:
    candidates: tuple[CandidateEvidence, ...]
    routes: tuple[RouteResult, ...]
    queries: tuple[LexicalQuery, ...]
    config_name: str
    warnings: tuple[str, ...] = ()

    @property
    def candidate_ids(self) -> tuple[str, ...]:
        return tuple(candidate.parent_asin for candidate in self.candidates)


@dataclass(frozen=True)
class RetrievalConfig:
    name: str
    route_depth: int = 200
    fused_depth: int = 200
    rrf_k: int = 60
    use_structured: bool = False


def retrieval_config(name: str) -> RetrievalConfig:
    normalized = name.strip().casefold()
    if normalized not in RETRIEVAL_NAMES:
        raise ValueError(f"retrieval name must be one of {RETRIEVAL_NAMES}")
    return RetrievalConfig(
        name=normalized,
        route_depth=200 if normalized == "single_bm25" else 400,
        use_structured=normalized == "multi_route_structured",
    )


class QueryCompiler:
    def compile(self, user_message: str, state: StateView) -> tuple[LexicalQuery, ...]:
        current_text = user_message
        category_text = self._slot_text(state, ("category", "audience"))
        latest_text = self._latest_slot_text(state)
        complete_text = self._slot_text(state, tuple(state.active_slots))
        feature_text = self._slot_text(
            state,
            ("feature", "use_case", "style", "material", "color"),
        )

        inputs = (
            ("current_message", current_text),
            ("category", category_text),
            ("latest_constraint", latest_text),
            ("complete_state", complete_text),
            ("title_heavy", complete_text or current_text),
            ("feature_heavy", " ".join(filter(None, (feature_text, current_text)))),
        )
        queries: list[LexicalQuery] = []
        for name, text in inputs:
            terms = lexical_terms(text)
            if terms:
                queries.append(LexicalQuery(name, text, terms, ROUTE_WEIGHTS[name]))
        return tuple(queries)

    def _slot_text(self, state: StateView, names: Sequence[str]) -> str:
        values: list[str] = []
        for name in names:
            slot = state.active_slots.get(name)
            if slot is None:
                continue
            values.extend(str(value.normalized_value) for value in slot.values)
        return " ".join(values)

    def _latest_slot_text(self, state: StateView) -> str:
        values = [
            str(value.normalized_value)
            for slot in state.active_slots.values()
            for value in slot.values
            if value.source_turn == state.turn
        ]
        return " ".join(values)


@dataclass(frozen=True)
class _ProductFacts:
    product: Product
    category: str
    audience: frozenset[str]
    brand: str
    text: str


def reciprocal_rank_fusion(
    routes: Sequence[RouteResult],
    route_weights: Mapping[str, float],
    rrf_k: int,
) -> dict[str, tuple[float, dict[str, int], dict[str, float]]]:
    fused: dict[str, tuple[float, dict[str, int], dict[str, float]]] = {}
    for route in routes:
        weight = route_weights.get(route.name, 1.0)
        for rank, parent_asin in enumerate(route.candidate_ids, start=1):
            contribution = weight / (rrf_k + rank)
            score, ranks, contributions = fused.get(parent_asin, (0.0, {}, {}))
            ranks[route.name] = rank
            contributions[route.name] = contribution
            fused[parent_asin] = (score + contribution, ranks, contributions)
    return fused


def fuse_lexical_and_dense(
    lexical: RetrievalResult,
    dense: DenseResult,
    *,
    route: str,
    catalog_order: Mapping[str, int],
    variant: str = "hybrid_dense",
    fused_depth: int = 200,
    rrf_k: int = 60,
) -> RetrievalResult:
    """Combine ranked evidence without mixing BM25 and cosine score scales."""
    if variant not in {"dense_only", "hybrid_dense"}:
        raise ValueError("variant must be dense_only or hybrid_dense")

    dense_route = RouteResult("dense", dense.candidate_ids, dense.scores)
    dense_view_routes = tuple(
        RouteResult(
            f"dense_{item.name}",
            item.candidate_ids,
            item.scores,
        )
        for item in dense.routes
        if len(dense.routes) > 1
    )
    if variant == "dense_only":
        routes = (dense_route,)
        weights = {"dense": 1.0}
    else:
        lexical_route = RouteResult(
            "lexical_fused",
            lexical.candidate_ids,
            tuple(candidate.fused_score for candidate in lexical.candidates),
        )
        routes = (lexical_route, dense_route)
        if route == "browsing":
            weights = {"lexical_fused": 1.0, "dense": 1.4}
        else:
            weights = {"lexical_fused": 1.4, "dense": 0.7}

    fused = reciprocal_rank_fusion(routes, weights, rrf_k)
    lexical_evidence = {
        candidate.parent_asin: candidate for candidate in lexical.candidates
    }
    evidence: list[CandidateEvidence] = []
    for parent_asin, (score, ranks, contributions) in fused.items():
        original = lexical_evidence.get(parent_asin)
        route_ranks = dict(original.route_ranks) if original else {}
        route_ranks.update(ranks)
        evidence.append(
            CandidateEvidence(
                parent_asin=parent_asin,
                fused_score=round(score, 8),
                route_ranks=route_ranks,
                route_contributions={
                    name: round(value, 8) for name, value in contributions.items()
                },
                compatibility_score=(original.compatibility_score if original else 0.0),
                matched_constraints=(original.matched_constraints if original else ()),
                contradicted_constraints=(
                    original.contradicted_constraints if original else ()
                ),
            )
        )
    evidence.sort(
        key=lambda item: (
            -item.fused_score,
            min(item.route_ranks.values(), default=10**9),
            catalog_order.get(item.parent_asin, 10**9),
            item.parent_asin,
        )
    )
    return RetrievalResult(
        candidates=tuple(evidence[:fused_depth]),
        routes=lexical.routes + (dense_route,) + dense_view_routes,
        queries=lexical.queries,
        config_name=variant,
        warnings=lexical.warnings,
    )


def fuse_lexical_and_dense_rescue(
    lexical: RetrievalResult,
    dense: DenseResult,
    *,
    state: StateView,
    structured_scorer: StructuredScorer,
    catalog_order: Mapping[str, int],
    rescue_depth: int = 20,
    rerank_anchor_depth: int = 40,
) -> RetrievalResult:
    """Put verified dense-only candidates inside the semantic rerank head."""
    if rescue_depth < 0 or rerank_anchor_depth < 0:
        raise ValueError("rescue and anchor depths must not be negative")
    lexical_ids = set(lexical.candidate_ids)
    hard_slots = {
        name
        for name, slot in state.active_slots.items()
        if any(value.strength == "hard" for value in slot.values)
    }
    dense_rank = {
        parent_asin: rank
        for rank, parent_asin in enumerate(dense.candidate_ids, start=1)
    }
    verified: list[CandidateEvidence] = []
    for parent_asin in dense.candidate_ids:
        if parent_asin in lexical_ids or parent_asin not in catalog_order:
            continue
        compatibility, matched, contradicted = structured_scorer.score(
            parent_asin, state
        )
        if hard_slots & set(contradicted):
            continue
        rank = dense_rank[parent_asin]
        contribution = 1.0 / (60 + rank)
        verified.append(
            CandidateEvidence(
                parent_asin=parent_asin,
                fused_score=round(contribution + 0.004 * compatibility, 8),
                route_ranks={"dense_rescue": rank},
                route_contributions={"dense_rescue": round(contribution, 8)},
                compatibility_score=compatibility,
                matched_constraints=matched,
                contradicted_constraints=contradicted,
            )
        )
    verified.sort(
        key=lambda item: (
            -item.compatibility_score,
            item.route_ranks["dense_rescue"],
            catalog_order[item.parent_asin],
        )
    )
    rescues = tuple(verified[:rescue_depth])

    anchor_depth = min(rerank_anchor_depth, len(lexical.candidates))
    candidates = (
        lexical.candidates[:anchor_depth]
        + rescues
        + lexical.candidates[anchor_depth:]
    )
    dense_route = RouteResult("dense", dense.candidate_ids, dense.scores)
    dense_view_routes = tuple(
        RouteResult(f"dense_{item.name}", item.candidate_ids, item.scores)
        for item in dense.routes
        if len(dense.routes) > 1
    )
    return RetrievalResult(
        candidates=candidates,
        routes=lexical.routes + (dense_route,) + dense_view_routes,
        queries=lexical.queries,
        config_name="hybrid_dense_rescue",
        warnings=lexical.warnings,
    )


class StructuredScorer:
    def __init__(self, facts_by_id: Mapping[str, _ProductFacts]) -> None:
        self.facts_by_id = facts_by_id

    def score(
        self,
        parent_asin: str,
        state: StateView,
    ) -> tuple[float, tuple[str, ...], tuple[str, ...]]:
        facts = self.facts_by_id[parent_asin]
        product = facts.product
        score = 0.0
        matched: list[str] = []
        contradicted: list[str] = []

        category_values = self._values(state, "category")
        if category_values:
            if facts.category in category_values:
                score += 2.0
                matched.append("category")
            elif facts.category:
                score -= 1.5
                contradicted.append("category")

        audience_values = set(self._values(state, "audience"))
        if audience_values and facts.audience:
            if audience_values & facts.audience:
                score += 1.0
                matched.append("audience")
            else:
                score -= 1.0
                contradicted.append("audience")

        score = self._facet_score(
            state, "material", set(product.materials), score, matched, contradicted
        )
        score = self._facet_score(
            state, "color", set(product.colors), score, matched, contradicted
        )

        brand_values = set(self._values(state, "brand"))
        if brand_values and facts.brand:
            if facts.brand in brand_values:
                score += 1.5
                matched.append("brand")
            else:
                score -= 1.0
                contradicted.append("brand")

        score = self._price_score(state, product, score, matched, contradicted)
        for name in ("size", "style", "use_case", "feature"):
            values = self._values(state, name)
            if values and any(
                all(term in facts.text for term in lexical_terms(value))
                for value in values
            ):
                score += 0.6
                matched.append(name)
        return round(score, 4), tuple(matched), tuple(contradicted)

    def _facet_score(
        self,
        state: StateView,
        name: str,
        product_values: set[str],
        score: float,
        matched: list[str],
        contradicted: list[str],
    ) -> float:
        slot = state.active_slots.get(name)
        if slot is None or not product_values:
            return score
        wanted = {str(value.normalized_value) for value in slot.values}
        is_match = wanted <= product_values if slot.match_mode == "all" else bool(
            wanted & product_values
        )
        strength = "hard" if any(value.strength == "hard" for value in slot.values) else "soft"
        if is_match:
            matched.append(name)
            return score + (1.5 if strength == "hard" else 0.8)
        contradicted.append(name)
        return score - (1.2 if strength == "hard" else 0.5)

    def _price_score(
        self,
        state: StateView,
        product: Product,
        score: float,
        matched: list[str],
        contradicted: list[str],
    ) -> float:
        if product.price is None or not PRICE_SLOTS & set(state.active_slots):
            return score
        minimum = self._first_number(state, "min_price")
        maximum = self._first_number(state, "max_price")
        target = self._first_number(state, "target_price")
        compatible = True
        if minimum is not None and product.price < minimum:
            compatible = False
        if maximum is not None and product.price > maximum:
            compatible = False
        if target is not None and abs(product.price - target) > max(10.0, target * 0.35):
            compatible = False
        if compatible:
            matched.append("budget")
            return score + 1.0
        contradicted.append("budget")
        return score - 1.0

    def _values(self, state: StateView, name: str) -> tuple[str, ...]:
        slot = state.active_slots.get(name)
        if slot is None:
            return ()
        return tuple(str(value.normalized_value) for value in slot.values)

    def _first_number(self, state: StateView, name: str) -> float | None:
        values = self._values(state, name)
        if not values:
            return None
        try:
            return float(values[0])
        except ValueError:
            return None


class LexicalRetriever:
    def __init__(
        self,
        connection: sqlite3.Connection,
        products: Sequence[Product],
        config: RetrievalConfig,
    ) -> None:
        self.connection = connection
        self.products = tuple(products)
        self.config = config
        self.query_compiler = QueryCompiler()
        self.catalog_order = {
            product.parent_asin: index for index, product in enumerate(self.products)
        }
        self.facts_by_id = self._build_facts()
        self.category_index, self.facet_indexes = self._build_structured_indexes()
        self.structured_scorer = StructuredScorer(self.facts_by_id)

    def retrieve(
        self,
        user_message: str,
        state: StateView,
        route: str,
        config: RetrievalConfig | None = None,
        *,
        route_weights: Mapping[str, float] | None = None,
        enabled_routes: Sequence[str] | None = None,
    ) -> RetrievalResult:
        selected = config or self.config
        queries = self.query_compiler.compile(user_message, state)
        if selected.name == "single_bm25":
            queries = tuple(query for query in queries if query.name == "current_message")
        elif enabled_routes:
            enabled = set(enabled_routes)
            queries = tuple(query for query in queries if query.name in enabled)
        route_results = [self._run_query(query, selected.route_depth) for query in queries]

        if selected.use_structured and (
            not enabled_routes or "structured" in enabled_routes
        ):
            structured = self._structured_route(state, selected.route_depth)
            if structured.candidate_ids:
                route_results.append(structured)

        selected_weights = (
            self._validated_route_weights(route_weights)
            if route_weights is not None
            else self._fusion_weights(route)
        )
        fused = reciprocal_rank_fusion(route_results, selected_weights, selected.rrf_k)
        evidence: list[CandidateEvidence] = []
        for parent_asin, (rrf_score, ranks, contributions) in fused.items():
            compatibility = 0.0
            matched: tuple[str, ...] = ()
            contradicted: tuple[str, ...] = ()
            if selected.use_structured:
                compatibility, matched, contradicted = self.structured_scorer.score(
                    parent_asin, state
                )
            final_score = rrf_score + 0.004 * compatibility
            evidence.append(
                CandidateEvidence(
                    parent_asin=parent_asin,
                    fused_score=round(final_score, 8),
                    route_ranks=dict(ranks),
                    route_contributions={
                        name: round(value, 8) for name, value in contributions.items()
                    },
                    compatibility_score=compatibility,
                    matched_constraints=matched,
                    contradicted_constraints=contradicted,
                )
            )
        evidence.sort(
            key=lambda item: (
                -item.fused_score,
                min(item.route_ranks.values(), default=10**9),
                self.catalog_order.get(item.parent_asin, 10**9),
                item.parent_asin,
            )
        )
        warnings = tuple(
            result.warning for result in route_results if result.warning is not None
        )
        return RetrievalResult(
            candidates=tuple(evidence[: selected.fused_depth]),
            routes=tuple(route_results),
            queries=queries,
            config_name=selected.name,
            warnings=warnings,
        )

    def fallback(
        self,
        user_message: str,
        state: StateView,
        route: str,
    ) -> RetrievalResult:
        return self.retrieve(user_message, state, route, retrieval_config("single_bm25"))

    def catalog_fallback(self, state: StateView, limit: int = 200) -> RetrievalResult:
        """Return category-local popularity, or global popularity as a last resort."""
        candidate_ids: Sequence[str] = ()
        for category in self._state_values(state, "category"):
            candidate_ids = self.category_index.get(category, ())
            if candidate_ids:
                break
        if not candidate_ids:
            candidate_ids = tuple(self.catalog_order)

        ranked = sorted(
            candidate_ids,
            key=lambda parent_asin: (
                -(self.facts_by_id[parent_asin].product.rating_number or 0),
                -(self.facts_by_id[parent_asin].product.average_rating or 0.0),
                self.catalog_order[parent_asin],
                parent_asin,
            ),
        )[:limit]
        candidates = tuple(
            CandidateEvidence(
                parent_asin=parent_asin,
                fused_score=round(1.0 / rank, 8),
                route_ranks={"catalog_popularity": rank},
                route_contributions={"catalog_popularity": round(1.0 / rank, 8)},
            )
            for rank, parent_asin in enumerate(ranked, start=1)
        )
        route = RouteResult(
            "catalog_popularity",
            tuple(ranked),
            tuple(candidate.fused_score for candidate in candidates),
        )
        return RetrievalResult(
            candidates=candidates,
            routes=(route,),
            queries=(),
            config_name="catalog_popularity_fallback",
        )

    @staticmethod
    def empty_result() -> RetrievalResult:
        return RetrievalResult((), (), (), "empty_fallback")

    def _run_query(self, query: LexicalQuery, limit: int) -> RouteResult:
        expression = " OR ".join(f'"{term}"' for term in query.terms)
        weights = ", ".join(str(value) for value in query.field_weights)
        try:
            rows = self.connection.execute(
                "SELECT parent_asin, bm25(products, " + weights + ") AS score "
                "FROM products WHERE products MATCH ? ORDER BY score LIMIT ?",
                (expression, limit),
            ).fetchall()
        except sqlite3.Error as error:
            return RouteResult(query.name, (), (), f"{query.name}:{type(error).__name__}")
        return RouteResult(
            query.name,
            tuple(str(row[0]) for row in rows),
            tuple(float(row[1]) for row in rows),
        )

    def _structured_route(self, state: StateView, limit: int) -> RouteResult:
        candidate_ids = self._structured_candidate_ids(state)
        ranked: list[tuple[str, float, int]] = []
        state_terms = set(
            lexical_terms(
                " ".join(
                    str(value)
                    for values in state.active_constraints.values()
                    for value in values
                )
            )
        )
        for parent_asin in candidate_ids:
            score, _, _ = self.structured_scorer.score(parent_asin, state)
            overlap = sum(
                term in self.facts_by_id[parent_asin].text for term in state_terms
            )
            ranked.append((parent_asin, score + overlap * 0.1, self.catalog_order[parent_asin]))
        ranked.sort(key=lambda item: (-item[1], item[2], item[0]))
        selected = ranked[:limit]
        return RouteResult(
            "structured",
            tuple(item[0] for item in selected),
            tuple(-item[1] for item in selected),
        )

    def _structured_candidate_ids(self, state: StateView) -> tuple[str, ...]:
        category_values = self._state_values(state, "category")
        for value in category_values:
            category_ids = self.category_index.get(value)
            if category_ids:
                return category_ids

        found: set[str] = set()
        for name in ("audience", "material", "color", "brand"):
            index = self.facet_indexes[name]
            for value in self._state_values(state, name):
                found.update(index.get(value, ()))
        return tuple(sorted(found, key=lambda item: self.catalog_order[item]))

    def _build_facts(self) -> dict[str, _ProductFacts]:
        result: dict[str, _ProductFacts] = {}
        for product in self.products:
            category = normalize_phrase(product.categories_text)
            category_terms = set(category.split())
            result[product.parent_asin] = _ProductFacts(
                product=product,
                category=category,
                audience=frozenset(category_terms & AUDIENCES),
                brand=normalize_phrase(product.brand),
                text=product.lexical_text.casefold(),
            )
        return result

    def _build_structured_indexes(
        self,
    ) -> tuple[dict[str, tuple[str, ...]], dict[str, dict[str, tuple[str, ...]]]]:
        categories: dict[str, list[str]] = {}
        facets: dict[str, dict[str, list[str]]] = {
            "audience": {},
            "material": {},
            "color": {},
            "brand": {},
        }
        for parent_asin, facts in self.facts_by_id.items():
            categories.setdefault(facts.category, []).append(parent_asin)
            values = {
                "audience": facts.audience,
                "material": facts.product.materials,
                "color": facts.product.colors,
                "brand": (facts.brand,) if facts.brand else (),
            }
            for name, items in values.items():
                for value in items:
                    facets[name].setdefault(str(value), []).append(parent_asin)
        return (
            {name: tuple(ids) for name, ids in categories.items()},
            {
                name: {value: tuple(ids) for value, ids in index.items()}
                for name, index in facets.items()
            },
        )

    def _fusion_weights(self, route: str) -> dict[str, float]:
        if route == "browsing":
            return {
                "current_message": 1.2,
                "category": 1.4,
                "latest_constraint": 1.0,
                "complete_state": 1.0,
                "title_heavy": 0.8,
                "feature_heavy": 1.3,
                "structured": 1.0,
            }
        return {
            "current_message": 1.0,
            "category": 0.9,
            "latest_constraint": 1.4,
            "complete_state": 1.5,
            "title_heavy": 1.3,
            "feature_heavy": 1.0,
            "structured": 1.2,
        }

    def _validated_route_weights(
        self, route_weights: Mapping[str, float]
    ) -> dict[str, float]:
        validated: dict[str, float] = {}
        for raw_name, raw_weight in route_weights.items():
            name = str(raw_name).strip()
            weight = float(raw_weight)
            if not name:
                raise ValueError("route weight name must not be empty")
            if weight < 0:
                raise ValueError("route weights must not be negative")
            validated[name] = weight
        return validated

    def _state_values(self, state: StateView, name: str) -> tuple[str, ...]:
        slot: ActiveSlotView | None = state.active_slots.get(name)
        if slot is None:
            return ()
        return tuple(str(value.normalized_value) for value in slot.values)
