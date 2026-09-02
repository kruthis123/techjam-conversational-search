from __future__ import annotations

from starter.state import SessionState
from starter.understanding import SlotUpdate, TurnUnderstanding


CATEGORY_DEPENDENT_SLOTS = ("size", "style", "use_case", "feature", "brand")
SINGLE_VALUE_SLOTS = {
    "audience",
    "brand",
    "size",
    "min_price",
    "max_price",
    "target_price",
}


class MemoryUpdater:
    """Translate parser output into explicit SessionState operations."""

    def apply(self, state: SessionState, understanding: TurnUnderstanding) -> tuple[str, ...]:
        parsed = understanding.parsed_turn
        turn = state.current_turn
        actions: list[str] = []
        events = {event.event_type: event for event in parsed.events}
        override = events.get("intent_override")

        if "full_restart" in events:
            state.full_restart(turn=turn)
            actions.append("full_restart")

        category_updates = [
            update
            for update in parsed.slot_updates
            if update.slot_name == "category" and update.action == "add"
        ]
        category_changed = bool(
            category_updates
            and tuple(category_updates[0].normalized_values)
            != tuple(state.active_constraints().get("category", ()))
        )

        if override and not (category_changed and category_updates):
            state.start_new_search_revision(turn=turn, reason="intent_override")
            actions.append("new_search_revision")

        if override and override.scope == "prior_soft":
            self._deactivate_soft_preferences(state, turn, actions)

        for update in parsed.slot_updates:
            if update.action == "deactivate":
                for value in update.normalized_values:
                    state.deactivate_slot_value(
                        update.slot_name,
                        value,
                        turn=turn,
                        reason="targeted_override",
                    )
                    actions.append(f"deactivate:{update.slot_name}")
            elif update.action == "clear":
                state.clear_slot(update.slot_name, turn=turn, reason="parsed_clear")
                actions.append(f"clear:{update.slot_name}")
            elif update.action == "replace":
                self._replace_update(state, update, turn, "parsed_replace")
                actions.append(f"replace:{update.slot_name}")

        category_handled = self._apply_category(
            state,
            category_updates,
            category_changed,
            override is not None,
            turn,
            actions,
        )

        for update in parsed.slot_updates:
            if update.action != "add" or update.slot_name == "category" and category_handled:
                continue
            current = tuple(state.active_constraints().get(update.slot_name, ()))
            if (
                update.slot_name in SINGLE_VALUE_SLOTS
                and current
                and tuple(update.normalized_values) != current
            ):
                self._replace_update(state, update, turn, "new_explicit_value")
                actions.append(f"replace:{update.slot_name}")
            else:
                self._add_update(state, update, turn)
                actions.append(f"add:{update.slot_name}")

        for event in parsed.events:
            if event.event_type in {"no_preference", "no_additional_preference"} and event.attribute:
                state.mark_no_preference(
                    event.attribute,
                    turn=turn,
                    source_text=event.reason,
                    clear_existing=event.clear_existing,
                )
                actions.append(f"no_preference:{event.attribute}")
        return tuple(actions)

    def _deactivate_soft_preferences(
        self,
        state: SessionState,
        turn: int,
        actions: list[str],
    ) -> None:
        for name, slot in tuple(state.active_slot_views().items()):
            if name in {"category", "audience"}:
                continue
            for value in slot.values:
                if value.strength == "soft":
                    state.deactivate_slot_value(
                        name,
                        value.normalized_value,
                        turn=turn,
                        reason="generic_intent_override",
                    )
                    actions.append(f"deactivate_soft:{name}")

    def _apply_category(
        self,
        state: SessionState,
        updates: list[SlotUpdate],
        changed: bool,
        is_override: bool,
        turn: int,
        actions: list[str],
    ) -> bool:
        if not updates:
            return False
        update = updates[0]
        current = tuple(state.active_constraints().get("category", ()))
        if changed and is_override:
            state.replace_category(
                update.values[0],
                normalized_value=update.normalized_values[0],
                turn=turn,
                source_text=update.source_text,
                invalidate_slots=CATEGORY_DEPENDENT_SLOTS,
                confidence=update.confidence,
                strength=update.strength,
            )
            actions.append("replace_category_with_revision")
        elif current and tuple(update.normalized_values) != current:
            self._replace_update(state, update, turn, "category_refinement")
            actions.append("refine_category")
        else:
            self._add_update(state, update, turn)
            actions.append("add:category")
        return True

    def _replace_update(
        self,
        state: SessionState,
        update: SlotUpdate,
        turn: int,
        reason: str,
    ) -> None:
        state.replace_slot(
            update.slot_name,
            update.values,
            normalized_values=update.normalized_values,
            turn=turn,
            source_text=update.source_text,
            confidence=update.confidence,
            strength=update.strength,
            match_mode=update.match_mode,
            reason=reason,
        )

    def _add_update(self, state: SessionState, update: SlotUpdate, turn: int) -> None:
        for value, normalized_value in zip(update.values, update.normalized_values):
            state.add_slot_value(
                update.slot_name,
                value,
                normalized_value=normalized_value,
                turn=turn,
                source_text=update.source_text,
                confidence=update.confidence,
                strength=update.strength,
                match_mode=update.match_mode,
            )
