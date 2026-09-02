from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, Mapping

from starter.catalog import (
    COLOR_ALIASES,
    COLOR_LOOKUP,
    COLOR_PATTERN,
    MATERIAL_ALIASES,
    MATERIAL_LOOKUP,
    MATERIAL_PATTERN,
    extract_facets,
    normalize_text,
)
from starter.state import SlotScalar, StateView
from starter.vocabulary import (
    CatalogVocabulary,
    CatalogVocabularyBuilder,
    contains_phrase as _contains_phrase,
    normalize_phrase,
)


ATTRIBUTE_PATTERN = re.compile(
    r"\b(category|material|color|size|style|brand|budget|feature|use[\s_-]?case|other)\b",
    re.I,
)
FULL_RESTART_RE = re.compile(
    r"\b(forget (?:everything|all (?:of )?that)|start over|fresh start|restart)\b",
    re.I,
)
OVERRIDE_RE = re.compile(
    r"\b(actually|instead of|rather than|ignore my earlier preference|not .+? anymore)\b",
    re.I,
)
PRIOR_SOFT_OVERRIDE_RE = re.compile(r"\bignore my earlier preference\b", re.I)
EXPLORATION_RE = re.compile(
    r"\b(still exploring|just browsing|not sure|open to ideas|show me ideas|recommend something)\b",
    re.I,
)
HARD_CUE_RE = re.compile(
    r"\b(must|need|require|required|key requirement|what matters|only|under\s+\$?\d)\b",
    re.I,
)
CONSTRAINT_CUE_RE = re.compile(
    r"(?:a key requirement is|for that,? what matters is|what i need is)\s*:\s*(.+)",
    re.I,
)

AUDIENCE_ALIASES = {
    "women": ("women", "woman", "womens", "women's", "female"),
    "men": ("men", "man", "mens", "men's", "male"),
    "girls": ("girls", "girl", "girl's"),
    "boys": ("boys", "boy", "boy's"),
    "baby": ("baby", "babies", "infant", "infants"),
    "unisex": ("unisex",),
}

USE_CASES = (
    "running",
    "hiking",
    "walking",
    "wedding",
    "winter",
    "gym",
    "work",
    "outdoor",
    "beach",
    "travel",
    "swimming",
    "yoga",
)

STYLES = (
    "casual",
    "formal",
    "classic",
    "modern",
    "vintage",
    "bohemian",
    "athletic",
    "minimalist",
)

PROFILE_TAG_TO_SLOT = {
    "comfort": "feature",
    "fit": "feature",
    "style": "feature",
    "weather": "feature",
    "warmth": "feature",
    "performance": "feature",
    "durability": "feature",
    "material": "feature",
}

def _attribute_name(value: str) -> str:
    return normalize_phrase(value).replace(" ", "_")


@dataclass(frozen=True)
class SlotUpdate:
    action: str
    slot_name: str
    values: tuple[SlotScalar, ...]
    normalized_values: tuple[SlotScalar, ...]
    confidence: float
    strength: str
    match_mode: str
    source_text: str


@dataclass(frozen=True)
class ConversationEvent:
    event_type: str
    confidence: float
    reason: str
    attribute: str | None = None
    clear_existing: bool = False
    scope: str = "targeted"


@dataclass(frozen=True)
class ParsedTurn:
    slot_updates: tuple[SlotUpdate, ...]
    events: tuple[ConversationEvent, ...]
    unmatched_constraint_phrases: tuple[str, ...]


@dataclass(frozen=True)
class IntentDecision:
    route: str
    confidence: float
    reasons: tuple[str, ...]
    buying_score: int
    browsing_score: int


@dataclass(frozen=True)
class ProfilePrior:
    slot_name: str
    value: str
    confidence: float = 0.2
    strength: str = "soft"


@dataclass(frozen=True)
class TurnUnderstanding:
    parsed_turn: ParsedTurn
    intent: IntentDecision
    profile_priors: tuple[ProfilePrior, ...]


class MessageParser:
    def __init__(self, vocabulary: CatalogVocabulary) -> None:
        self.vocabulary = vocabulary

    def parse(self, message: str, state: StateView) -> ParsedTurn:
        if not isinstance(message, str):
            raise TypeError("message must be a string")
        normalized = normalize_phrase(message)
        events = self._events(message)
        updates: list[SlotUpdate] = []

        negated_colors = self._negated_facets(message, COLOR_ALIASES)
        negated_materials = self._negated_facets(message, MATERIAL_ALIASES)
        for color in negated_colors:
            updates.append(self._update("deactivate", "color", (color,), message, 0.95, "hard"))
        for material in negated_materials:
            updates.append(
                self._update("deactivate", "material", (material,), message, 0.95, "hard")
            )

        is_exploring = bool(EXPLORATION_RE.search(message))
        strength = "soft" if is_exploring else "hard" if HARD_CUE_RE.search(message) else "soft"
        audience = self._audience(normalized, state)
        if audience and self._contains_explicit_audience(normalized):
            updates.append(self._update("add", "audience", (audience,), message, 0.98, "hard"))

        category = self.vocabulary.match_category(message, audience)
        if category:
            category_value = " > ".join(category)
            updates.append(
                SlotUpdate(
                    action="add",
                    slot_name="category",
                    values=(category_value,),
                    normalized_values=(normalize_phrase(category_value),),
                    confidence=0.95,
                    strength="hard",
                    match_mode="any",
                    source_text=message,
                )
            )

        colors = tuple(
            value
            for value in extract_facets(message, COLOR_PATTERN, COLOR_LOOKUP, COLOR_ALIASES)
            if value not in negated_colors
        )
        materials = tuple(
            value
            for value in extract_facets(
                message, MATERIAL_PATTERN, MATERIAL_LOOKUP, MATERIAL_ALIASES
            )
            if value not in negated_materials
        )
        if colors:
            updates.append(self._update("add", "color", colors, message, 0.98, strength, "any"))
        if materials:
            updates.append(
                self._update("add", "material", materials, message, 0.98, strength, "any")
            )

        updates.extend(self._price_updates(message, strength))
        size = self._size(message)
        if size:
            updates.append(self._update("add", "size", (size,), message, 0.95, strength))

        brand = self.vocabulary.match_brand(message)
        if brand:
            updates.append(self._update("add", "brand", (brand,), message, 0.9, strength))

        use_cases = tuple(value for value in USE_CASES if _contains_phrase(normalized, value))
        styles = tuple(value for value in STYLES if _contains_phrase(normalized, value))
        if use_cases:
            updates.append(
                self._update("add", "use_case", use_cases, message, 0.9, strength, "any")
            )
        if styles:
            updates.append(self._update("add", "style", styles, message, 0.9, strength, "any"))

        constraint_phrases = self._constraint_phrases(message)
        for phrase, phrase_strength in constraint_phrases:
            cleaned_phrase = normalize_text(phrase)
            if normalize_phrase(cleaned_phrase) and not self._phrase_is_covered(phrase, updates):
                updates.append(
                    self._update(
                        "add",
                        "feature",
                        (cleaned_phrase,),
                        phrase,
                        0.85,
                        phrase_strength,
                        "all",
                    )
                )

        return ParsedTurn(
            slot_updates=self._deduplicate_updates(updates),
            events=events,
            unmatched_constraint_phrases=tuple(
                phrase for phrase, _ in constraint_phrases if not self._phrase_is_covered(phrase, updates)
            ),
        )

    def _events(self, message: str) -> tuple[ConversationEvent, ...]:
        events: list[ConversationEvent] = []
        if FULL_RESTART_RE.search(message):
            events.append(ConversationEvent("full_restart", 0.99, "full restart cue", scope="all"))
            return tuple(events)

        no_preference = re.search(
            r"\b(?:do not|don't) have (?:an? )?(additional )?preference for\s+"
            r"(category|material|color|size|style|brand|budget|feature|use[\s_-]?case|other)\b",
            message,
            re.I,
        )
        if no_preference:
            additional = bool(no_preference.group(1))
            events.append(
                ConversationEvent(
                    event_type="no_additional_preference" if additional else "no_preference",
                    confidence=1.0,
                    reason="explicit no-preference response",
                    attribute=_attribute_name(no_preference.group(2)),
                    clear_existing=not additional,
                    scope="attribute",
                )
            )

        if OVERRIDE_RE.search(message):
            events.append(
                ConversationEvent(
                    event_type="intent_override",
                    confidence=0.98,
                    reason="override language detected",
                    scope="prior_soft" if PRIOR_SOFT_OVERRIDE_RE.search(message) else "targeted",
                )
            )
        return tuple(events)

    def _audience(self, message: str, state: StateView) -> str | None:
        for canonical, aliases in AUDIENCE_ALIASES.items():
            if any(_contains_phrase(message, normalize_phrase(alias)) for alias in aliases):
                return canonical
        existing = state.active_constraints.get("audience", ())
        return str(existing[0]) if existing else None

    def _contains_explicit_audience(self, message: str) -> bool:
        return any(
            _contains_phrase(message, normalize_phrase(alias))
            for aliases in AUDIENCE_ALIASES.values()
            for alias in aliases
        )

    def _price_updates(self, message: str, strength: str) -> list[SlotUpdate]:
        lowered = message.casefold()
        updates: list[SlotUpdate] = []
        between = re.search(
            r"\bbetween\s+\$?\s*(\d+(?:\.\d+)?)\s+(?:and|to)\s+\$?\s*(\d+(?:\.\d+)?)",
            lowered,
        )
        if between:
            minimum, maximum = float(between.group(1)), float(between.group(2))
            updates.append(self._update("add", "min_price", (minimum,), message, 0.99, "hard"))
            updates.append(self._update("add", "max_price", (maximum,), message, 0.99, "hard"))
            return updates

        patterns = (
            ("max_price", r"\b(?:under|below|less than|up to)\s+\$?\s*(\d+(?:\.\d+)?)", "hard"),
            ("min_price", r"\b(?:over|above|more than|at least)\s+\$?\s*(\d+(?:\.\d+)?)", "hard"),
            ("target_price", r"\b(?:around|about|budget around)\s+\$?\s*(\d+(?:\.\d+)?)", "soft"),
        )
        for slot_name, pattern, price_strength in patterns:
            match = re.search(pattern, lowered)
            if match:
                updates.append(
                    self._update(
                        "add",
                        slot_name,
                        (float(match.group(1)),),
                        message,
                        0.99,
                        price_strength if price_strength else strength,
                    )
                )
        return updates

    def _size(self, message: str) -> str | None:
        match = re.search(
            r"\bsize\s+(xxs|xs|small|medium|large|xl|xxl|xxxl|\d{1,2}(?:\.\d)?)\b",
            message,
            re.I,
        )
        return normalize_phrase(match.group(1)) if match else None

    def _constraint_phrases(self, message: str) -> tuple[tuple[str, str], ...]:
        match = CONSTRAINT_CUE_RE.search(message)
        if match:
            return tuple(
                (phrase.strip(" ."), "hard")
                for phrase in match.group(1).split(";")
                if phrase.strip(" .")
            )

        parts = re.split(r"\.\s+", message, maxsplit=1)
        if (
            len(parts) == 2
            and re.search(r"\bi(?:'m| am) looking for\b", parts[0], re.I)
            and not EXPLORATION_RE.search(parts[1])
        ):
            phrase = parts[1].strip(" .")
            if phrase:
                return ((phrase, "soft"),)
        return ()

    def _negated_facets(
        self,
        message: str,
        aliases: Mapping[str, tuple[str, ...]],
    ) -> set[str]:
        found: set[str] = set()
        for canonical, values in aliases.items():
            for alias in values:
                expression = re.escape(alias).replace(r"\ ", r"[\s-]+")
                patterns = (
                    rf"\bnot\s+{expression}(?:\s+anymore)?\b",
                    rf"\bno longer\s+{expression}\b",
                    rf"\binstead of\s+{expression}\b",
                )
                if any(re.search(pattern, message, re.I) for pattern in patterns):
                    found.add(canonical)
        return found

    def _phrase_is_covered(self, phrase: str, updates: Iterable[SlotUpdate]) -> bool:
        normalized = normalize_phrase(phrase)
        meaningful = [word for word in normalized.split() if len(word) > 2]
        if len(meaningful) > 4:
            return False
        return any(
            update.slot_name != "feature"
            and any(
                normalize_phrase(value) == normalized
                or _contains_phrase(normalized, normalize_phrase(value))
                for value in update.values
            )
            for update in updates
        )

    def _update(
        self,
        action: str,
        slot_name: str,
        values: tuple[SlotScalar, ...],
        source_text: str,
        confidence: float,
        strength: str,
        match_mode: str = "any",
    ) -> SlotUpdate:
        return SlotUpdate(
            action=action,
            slot_name=slot_name,
            values=values,
            normalized_values=tuple(
                normalize_phrase(value) if isinstance(value, str) else value for value in values
            ),
            confidence=confidence,
            strength=strength,
            match_mode=match_mode,
            source_text=source_text,
        )

    def _deduplicate_updates(self, updates: Iterable[SlotUpdate]) -> tuple[SlotUpdate, ...]:
        result: list[SlotUpdate] = []
        seen: set[tuple[str, str, tuple[SlotScalar, ...]]] = set()
        for update in updates:
            key = (update.action, update.slot_name, update.normalized_values)
            if key not in seen:
                result.append(update)
                seen.add(key)
        return tuple(result)


class IntentRouter:
    def route(self, message: str, parsed: ParsedTurn, state: StateView) -> IntentDecision:
        buying_score = 0
        browsing_score = 0
        reasons: list[str] = []

        if EXPLORATION_RE.search(message):
            browsing_score += 3
            reasons.append("explicit exploration cue")
        if HARD_CUE_RE.search(message):
            buying_score += 2
            reasons.append("hard requirement cue")

        slots = {update.slot_name for update in parsed.slot_updates if update.action == "add"}
        concrete_slots = slots & {
            "material", "color", "size", "brand", "min_price", "max_price", "target_price"
        }
        if "category" in slots:
            buying_score += 2
            reasons.append("specific catalog category")
        if concrete_slots:
            buying_score += len(concrete_slots)
            reasons.append("concrete product constraints")
        if len(concrete_slots) >= 2:
            buying_score += 1

        active_names = set(state.active_constraints)
        if len(active_names & {"category", "material", "color", "size", "brand"}) >= 2:
            buying_score += 1
            reasons.append("accumulated state is specific")
        if "use_case" in slots and "category" not in slots and "category" not in active_names:
            browsing_score += 1
            reasons.append("scenario without product category")
        if not slots and not active_names:
            browsing_score += 1
            reasons.append("no concrete constraints")

        route = "browsing" if browsing_score > buying_score else "buying"
        margin = abs(buying_score - browsing_score)
        confidence = min(0.99, 0.55 + 0.08 * margin)
        if buying_score == browsing_score:
            confidence = 0.5
        return IntentDecision(
            route=route,
            confidence=round(confidence, 2),
            reasons=tuple(reasons) or ("default route",),
            buying_score=buying_score,
            browsing_score=browsing_score,
        )


def profile_priors(profile: Mapping[str, object]) -> tuple[ProfilePrior, ...]:
    tags = profile.get("preference_tags")
    if not isinstance(tags, list):
        return ()
    priors: list[ProfilePrior] = []
    seen: set[str] = set()
    for tag in tags:
        normalized = normalize_phrase(tag)
        if normalized and normalized not in seen:
            priors.append(
                ProfilePrior(
                    slot_name=PROFILE_TAG_TO_SLOT.get(normalized, "feature"),
                    value=normalized,
                )
            )
            seen.add(normalized)
    return tuple(priors)


class UnderstandingEngine:
    def __init__(self, vocabulary: CatalogVocabulary) -> None:
        self.parser = MessageParser(vocabulary)
        self.router = IntentRouter()

    def understand(self, message: str, state: StateView) -> TurnUnderstanding:
        parsed = self.parser.parse(message, state)
        intent = self.router.route(message, parsed, state)
        return TurnUnderstanding(parsed, intent, profile_priors(state.user_profile))
