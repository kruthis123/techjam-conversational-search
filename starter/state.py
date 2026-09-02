from __future__ import annotations

import copy
import math
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Iterable, Mapping, Union


MAX_TURNS = 10
VALID_STRENGTHS = {"hard", "soft"}
VALID_MATCH_MODES = {"any", "all"}

SlotScalar = Union[str, int, float, bool]


def _validate_turn(turn: int) -> None:
    if isinstance(turn, bool) or not isinstance(turn, int) or not 1 <= turn <= MAX_TURNS:
        raise ValueError(f"turn must be an integer from 1 to {MAX_TURNS}")


def _validate_scalar(value: SlotScalar, field_name: str) -> None:
    if isinstance(value, str):
        if not value.strip():
            raise ValueError(f"{field_name} must not be empty")
        return
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError(f"{field_name} must be finite")
    if not isinstance(value, (int, float, bool)):
        raise TypeError(f"{field_name} must be a string, number, or boolean")


def _default_normalized_value(value: SlotScalar) -> SlotScalar:
    return value.strip().casefold() if isinstance(value, str) else value


def _validate_slot_name(name: str) -> str:
    normalized = name.strip().casefold()
    if not normalized:
        raise ValueError("slot name must not be empty")
    return normalized


def _validate_match_mode(match_mode: str) -> str:
    normalized = match_mode.strip().casefold()
    if normalized not in VALID_MATCH_MODES:
        raise ValueError(f"match_mode must be one of {sorted(VALID_MATCH_MODES)}")
    return normalized


@dataclass
class SlotValue:
    value: SlotScalar
    normalized_value: SlotScalar
    confidence: float
    strength: str
    source_turn: int
    source_text: str
    active: bool = True
    deactivated_turn: int | None = None
    deactivation_reason: str | None = None

    def __post_init__(self) -> None:
        _validate_scalar(self.value, "value")
        _validate_scalar(self.normalized_value, "normalized_value")
        _validate_turn(self.source_turn)
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")
        self.strength = self.strength.strip().casefold()
        if self.strength not in VALID_STRENGTHS:
            raise ValueError(f"strength must be one of {sorted(VALID_STRENGTHS)}")
        if not isinstance(self.source_text, str):
            raise TypeError("source_text must be a string")

    def deactivate(self, turn: int, reason: str) -> bool:
        _validate_turn(turn)
        if not self.active:
            return False
        self.active = False
        self.deactivated_turn = turn
        self.deactivation_reason = reason.strip() or "unspecified"
        return True


@dataclass
class Slot:
    name: str
    match_mode: str = "any"
    values: list[SlotValue] = field(default_factory=list)
    no_preference: bool = False
    no_preference_turn: int | None = None
    no_preference_source_text: str = ""
    updated_turn: int = 0

    def __post_init__(self) -> None:
        self.name = _validate_slot_name(self.name)
        self.match_mode = _validate_match_mode(self.match_mode)

    @property
    def active_values(self) -> tuple[SlotValue, ...]:
        return tuple(value for value in self.values if value.active)

    def add_value(self, value: SlotValue) -> bool:
        for existing in self.active_values:
            if existing.normalized_value == value.normalized_value:
                changed = (
                    existing.value != value.value
                    or existing.confidence != max(existing.confidence, value.confidence)
                    or existing.strength != "hard" and value.strength == "hard"
                    or existing.source_turn != value.source_turn
                    or existing.source_text != value.source_text
                    or self.no_preference
                )
                existing.value = value.value
                existing.confidence = max(existing.confidence, value.confidence)
                if value.strength == "hard":
                    existing.strength = "hard"
                existing.source_turn = value.source_turn
                existing.source_text = value.source_text
                self._clear_no_preference()
                self.updated_turn = value.source_turn
                return changed

        self.values.append(value)
        self._clear_no_preference()
        self.updated_turn = value.source_turn
        return True

    def deactivate_value(
        self,
        normalized_value: SlotScalar,
        turn: int,
        reason: str,
    ) -> bool:
        changed = False
        for value in self.active_values:
            if value.normalized_value == normalized_value:
                changed = value.deactivate(turn, reason) or changed
        if changed:
            self.updated_turn = turn
        return changed

    def clear_values(self, turn: int, reason: str) -> bool:
        changed = False
        for value in self.active_values:
            changed = value.deactivate(turn, reason) or changed
        if changed:
            self.updated_turn = turn
        return changed

    def mark_no_preference(
        self,
        turn: int,
        source_text: str,
        *,
        clear_existing: bool,
    ) -> bool:
        changed = False
        if clear_existing:
            changed = self.clear_values(turn, "no_preference")
        if (
            not self.no_preference
            or self.no_preference_turn != turn
            or self.no_preference_source_text != source_text
        ):
            self.no_preference = True
            self.no_preference_turn = turn
            self.no_preference_source_text = source_text
            self.updated_turn = turn
            changed = True
        return changed

    def clear_no_preference(self) -> bool:
        if not self.no_preference:
            return False
        self._clear_no_preference()
        return True

    def _clear_no_preference(self) -> None:
        self.no_preference = False
        self.no_preference_turn = None
        self.no_preference_source_text = ""


@dataclass(frozen=True)
class TurnMessage:
    turn: int
    text: str


@dataclass
class ShownProduct:
    parent_asin: str
    revision: int
    first_turn: int
    last_turn: int
    best_rank: int
    display_count: int = 1

    def record(self, turn: int, rank: int) -> None:
        self.last_turn = turn
        self.best_rank = min(self.best_rank, rank)
        self.display_count += 1


@dataclass(frozen=True)
class RevisionEvent:
    revision: int
    turn: int
    reason: str


@dataclass(frozen=True)
class ClarificationRecord:
    attribute: str
    revision: int
    turn: int


@dataclass(frozen=True)
class ActiveValueView:
    normalized_value: SlotScalar
    confidence: float
    strength: str
    source_turn: int


@dataclass(frozen=True)
class ActiveSlotView:
    name: str
    match_mode: str
    values: tuple[ActiveValueView, ...]


@dataclass(frozen=True)
class StateView:
    session_id: str
    turn: int
    search_revision: int
    context_version: int
    active_slots: Mapping[str, ActiveSlotView]
    active_constraints: Mapping[str, tuple[SlotScalar, ...]]
    no_preference_attributes: tuple[str, ...]
    asked_attributes: tuple[str, ...]
    shown_product_ids: tuple[str, ...]
    user_profile: Mapping[str, object]
    initial_route: str | None


@dataclass
class SessionState:
    session_id: str
    user_profile: dict[str, object]
    slots: dict[str, Slot] = field(default_factory=dict)
    messages: list[TurnMessage] = field(default_factory=list)
    shown_products: dict[tuple[int, str], ShownProduct] = field(default_factory=dict)
    search_revision: int = 1
    context_version: int = 0
    revision_history: list[RevisionEvent] = field(default_factory=list)
    clarification_history: list[ClarificationRecord] = field(default_factory=list)
    initial_route: str | None = None
    derived_cache: dict[str, object] = field(default_factory=dict, repr=False)

    def __post_init__(self) -> None:
        if not self.session_id.strip():
            raise ValueError("session_id must not be empty")

    @property
    def current_turn(self) -> int:
        return self.messages[-1].turn if self.messages else 0

    def record_turn(self, turn: int, user_message: str) -> None:
        _validate_turn(turn)
        if not isinstance(user_message, str):
            raise TypeError("user_message must be a string")
        expected_turn = self.current_turn + 1
        if turn != expected_turn:
            raise ValueError(f"expected turn {expected_turn}, received turn {turn}")
        self.messages.append(TurnMessage(turn, user_message))
        self._context_changed()

    def set_initial_route(self, route: str) -> None:
        normalized = route.strip().casefold()
        if normalized not in {"buying", "browsing"}:
            raise ValueError("route must be buying or browsing")
        if self.initial_route is None:
            self.initial_route = normalized
            self._context_changed()

    def add_slot_value(
        self,
        name: str,
        value: SlotScalar,
        *,
        turn: int,
        source_text: str,
        normalized_value: SlotScalar | None = None,
        confidence: float = 1.0,
        strength: str = "soft",
        match_mode: str | None = None,
    ) -> None:
        self._require_current_turn(turn)
        slot = self._get_or_create_slot(name, match_mode)
        normalized = _default_normalized_value(
            value if normalized_value is None else normalized_value
        )
        changed = slot.add_value(
            SlotValue(
                value=value,
                normalized_value=normalized,
                confidence=confidence,
                strength=strength,
                source_turn=turn,
                source_text=source_text,
            )
        )
        if changed:
            self._context_changed()

    def deactivate_slot_value(
        self,
        name: str,
        normalized_value: SlotScalar,
        *,
        turn: int,
        reason: str = "user_override",
        new_revision: bool = False,
    ) -> None:
        self._require_current_turn(turn)
        normalized_name = _validate_slot_name(name)
        normalized_value = _default_normalized_value(normalized_value)
        changed = False
        slot = self.slots.get(normalized_name)
        if slot is not None:
            changed = slot.deactivate_value(normalized_value, turn, reason)
        if new_revision:
            self._advance_revision(turn, reason)
            changed = True
        if changed:
            self._context_changed()

    def clear_slot(
        self,
        name: str,
        *,
        turn: int,
        reason: str = "cleared",
        new_revision: bool = False,
    ) -> None:
        self._require_current_turn(turn)
        normalized_name = _validate_slot_name(name)
        changed = False
        slot = self.slots.get(normalized_name)
        if slot is not None:
            changed = slot.clear_values(turn, reason)
            changed = slot.clear_no_preference() or changed
        if new_revision:
            self._advance_revision(turn, reason)
            changed = True
        if changed:
            self._context_changed()

    def replace_slot(
        self,
        name: str,
        values: Iterable[SlotScalar],
        *,
        turn: int,
        source_text: str,
        normalized_values: Iterable[SlotScalar] | None = None,
        confidence: float = 1.0,
        strength: str = "soft",
        match_mode: str | None = None,
        reason: str = "replaced",
        new_revision: bool = False,
    ) -> None:
        self._require_current_turn(turn)
        raw_values = tuple(values)
        if not raw_values:
            raise ValueError("replace_slot requires at least one value")
        normalized = (
            tuple(_default_normalized_value(value) for value in raw_values)
            if normalized_values is None
            else tuple(_default_normalized_value(value) for value in normalized_values)
        )
        if len(raw_values) != len(normalized):
            raise ValueError("values and normalized_values must have the same length")

        slot = self._get_or_create_slot(name, match_mode)
        slot.clear_values(turn, reason)
        slot.clear_no_preference()
        for value, normalized_value in zip(raw_values, normalized):
            slot.add_value(
                SlotValue(
                    value=value,
                    normalized_value=normalized_value,
                    confidence=confidence,
                    strength=strength,
                    source_turn=turn,
                    source_text=source_text,
                )
            )
        if new_revision:
            self._advance_revision(turn, reason)
        self._context_changed()

    def mark_no_preference(
        self,
        name: str,
        *,
        turn: int,
        source_text: str,
        clear_existing: bool = False,
    ) -> None:
        self._require_current_turn(turn)
        slot = self._get_or_create_slot(name)
        if slot.mark_no_preference(
            turn,
            source_text,
            clear_existing=clear_existing,
        ):
            self._context_changed()

    def replace_category(
        self,
        value: SlotScalar,
        *,
        turn: int,
        source_text: str,
        normalized_value: SlotScalar | None = None,
        invalidate_slots: Iterable[str] = (),
        confidence: float = 1.0,
        strength: str = "hard",
    ) -> None:
        self._require_current_turn(turn)
        self._advance_revision(turn, "category_override")
        names = {_validate_slot_name(name) for name in invalidate_slots}
        names.add("category")
        for name in names:
            slot = self.slots.get(name)
            if slot is not None:
                slot.clear_values(turn, "category_override")
                slot.clear_no_preference()

        category = self._get_or_create_slot("category", "any")
        category.add_value(
            SlotValue(
                value=value,
                normalized_value=(
                    _default_normalized_value(value)
                    if normalized_value is None
                    else _default_normalized_value(normalized_value)
                ),
                confidence=confidence,
                strength=strength,
                source_turn=turn,
                source_text=source_text,
            )
        )
        self._context_changed()

    def full_restart(self, *, turn: int, reason: str = "full_restart") -> None:
        self._require_current_turn(turn)
        self._advance_revision(turn, reason)
        for slot in self.slots.values():
            slot.clear_values(turn, reason)
            slot.clear_no_preference()
        self._context_changed()

    def start_new_search_revision(
        self,
        *,
        turn: int,
        reason: str = "intent_override",
    ) -> None:
        self._require_current_turn(turn)
        self._advance_revision(turn, reason)
        self._context_changed()

    def record_shown_products(self, *, turn: int, ranked_ids: Iterable[str]) -> None:
        self._require_current_turn(turn)
        changed = False
        seen: set[str] = set()
        for rank, raw_parent_asin in enumerate(ranked_ids, start=1):
            parent_asin = str(raw_parent_asin).strip()
            if not parent_asin or parent_asin in seen:
                continue
            seen.add(parent_asin)
            key = (self.search_revision, parent_asin)
            shown = self.shown_products.get(key)
            if shown is None:
                self.shown_products[key] = ShownProduct(
                    parent_asin=parent_asin,
                    revision=self.search_revision,
                    first_turn=turn,
                    last_turn=turn,
                    best_rank=rank,
                )
            else:
                shown.record(turn, rank)
            changed = True
        if changed:
            self._context_changed()

    def record_clarification(self, *, turn: int, attribute: str) -> None:
        self._require_current_turn(turn)
        normalized = _validate_slot_name(attribute)
        if normalized in self.current_revision_asked_attributes():
            return
        self.clarification_history.append(
            ClarificationRecord(normalized, self.search_revision, turn)
        )
        self._context_changed()

    def active_constraints(self) -> Mapping[str, tuple[SlotScalar, ...]]:
        constraints = {
            name: tuple(value.normalized_value for value in slot.active_values)
            for name, slot in self.slots.items()
            if slot.active_values
        }
        return MappingProxyType(constraints)

    def active_slot_views(self) -> Mapping[str, ActiveSlotView]:
        views = {
            name: ActiveSlotView(
                name=name,
                match_mode=slot.match_mode,
                values=tuple(
                    ActiveValueView(
                        normalized_value=value.normalized_value,
                        confidence=value.confidence,
                        strength=value.strength,
                        source_turn=value.source_turn,
                    )
                    for value in slot.active_values
                ),
            )
            for name, slot in self.slots.items()
            if slot.active_values
        }
        return MappingProxyType(views)

    def no_preference_attributes(self) -> tuple[str, ...]:
        return tuple(name for name, slot in self.slots.items() if slot.no_preference)

    def current_revision_shown_ids(self) -> tuple[str, ...]:
        return tuple(
            product.parent_asin
            for (revision, _), product in self.shown_products.items()
            if revision == self.search_revision
        )

    def current_revision_asked_attributes(self) -> tuple[str, ...]:
        return tuple(
            record.attribute
            for record in self.clarification_history
            if record.revision == self.search_revision
        )

    def retrieval_view(self) -> StateView:
        return StateView(
            session_id=self.session_id,
            turn=self.current_turn,
            search_revision=self.search_revision,
            context_version=self.context_version,
            active_slots=self.active_slot_views(),
            active_constraints=self.active_constraints(),
            no_preference_attributes=self.no_preference_attributes(),
            asked_attributes=self.current_revision_asked_attributes(),
            shown_product_ids=self.current_revision_shown_ids(),
            user_profile=MappingProxyType(copy.deepcopy(self.user_profile)),
            initial_route=self.initial_route,
        )

    def cache_derived(self, key: str, value: object) -> None:
        if not key:
            raise ValueError("cache key must not be empty")
        self.derived_cache[key] = value

    def get_cached(self, key: str, default: object = None) -> object:
        return self.derived_cache.get(key, default)

    def _get_or_create_slot(self, name: str, match_mode: str | None = None) -> Slot:
        normalized_name = _validate_slot_name(name)
        slot = self.slots.get(normalized_name)
        if slot is None:
            slot = Slot(normalized_name, match_mode or "any")
            self.slots[normalized_name] = slot
        elif match_mode is not None:
            slot.match_mode = _validate_match_mode(match_mode)
        return slot

    def _require_current_turn(self, turn: int) -> None:
        _validate_turn(turn)
        if turn != self.current_turn:
            raise ValueError(
                f"state update turn {turn} does not match current turn {self.current_turn}"
            )

    def _advance_revision(self, turn: int, reason: str) -> None:
        self.search_revision += 1
        self.revision_history.append(
            RevisionEvent(self.search_revision, turn, reason.strip() or "unspecified")
        )

    def _context_changed(self) -> None:
        self.context_version += 1
        self.derived_cache.clear()


class SessionStore:
    def __init__(self) -> None:
        self.sessions: dict[str, SessionState] = {}

    def reset(self, session_id: str, user_profile: Mapping[str, object]) -> SessionState:
        if not isinstance(session_id, str) or not session_id.strip():
            raise ValueError("session_id must not be empty")
        state = SessionState(session_id, copy.deepcopy(dict(user_profile)))
        self.sessions[session_id] = state
        return state

    def get(self, session_id: str) -> SessionState:
        try:
            return self.sessions[session_id]
        except KeyError as error:
            raise RuntimeError(f'session "{session_id}" was not initialized') from error

    def remove(self, session_id: str) -> None:
        self.sessions.pop(session_id, None)
