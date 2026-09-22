from __future__ import annotations

from dataclasses import dataclass, replace

from starter.intent import ObservedClaim, parse_intent


@dataclass(frozen=True)
class TurnRecord:
    turn: int
    message: str
    ask_attribute: str | None
    unresolved: bool


@dataclass(frozen=True)
class SessionState:
    turns: tuple[TurnRecord, ...] = ()
    active_claims: tuple[ObservedClaim, ...] = ()
    unresolved_turns: tuple[TurnRecord, ...] = ()
    pending_ask_attribute: str | None = None


class SessionStateStore:
    def __init__(self) -> None:
        self._sessions: dict[str, SessionState] = {}

    def reset(self, session_id: str) -> SessionState:
        state = SessionState()
        self._sessions[session_id] = state
        return state

    def record_ask_attribute(
        self,
        session_id: str,
        ask_attribute: str | None,
    ) -> SessionState:
        state = replace(
            self._sessions[session_id],
            pending_ask_attribute=ask_attribute,
        )
        self._sessions[session_id] = state
        return state

    def receive(self, session_id: str, turn: int, message: str) -> SessionState:
        state = self._sessions[session_id]
        parsed = parse_intent(message, state.pending_ask_attribute)
        record = TurnRecord(
            turn=turn,
            message=message,
            ask_attribute=state.pending_ask_attribute,
            unresolved=parsed.unresolved,
        )
        active_claims = list(state.active_claims)

        if not parsed.unresolved:
            for claim in parsed.claims:
                for index, active in enumerate(active_claims):
                    if active.attribute == claim.attribute:
                        active_claims[index] = claim
                        break
                else:
                    active_claims.append(claim)

        unresolved_turns = state.unresolved_turns
        if parsed.unresolved:
            unresolved_turns += (record,)

        state = SessionState(
            turns=state.turns + (record,),
            active_claims=tuple(active_claims),
            unresolved_turns=unresolved_turns,
        )
        self._sessions[session_id] = state
        return state

    def get(self, session_id: str) -> SessionState:
        return self._sessions[session_id]
