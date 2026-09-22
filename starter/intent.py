from __future__ import annotations

from dataclasses import dataclass
import re


MATERIALS = ("cotton", "polyester", "nylon", "leather", "wool", "spandex", "silk", "rayon", "fabric")


@dataclass(frozen=True)
class ObservedClaim:
    attribute: str
    value: str | None
    stance: str


@dataclass(frozen=True)
class IntentParse:
    claims: tuple[ObservedClaim, ...]
    unresolved: bool = False


def _classify(value: str) -> str:
    lowered = value.lower()
    if "budget" in lowered or re.search(r"(?:\$|<=|under)\s*\d", lowered):
        return "budget"
    if any(material in lowered for material in MATERIALS):
        return "material"
    if any(word in lowered for word in ("color", "black", "white", "blue", "red", "pink", "green")):
        return "color"
    if any(word in lowered for word in ("size", "sizing", "width", "wide", "narrow")):
        return "size"
    if any(word in lowered for word in ("department", "style", "fit", "sleeve", "neck")):
        return "style"
    if any(word in lowered for word in ("hiking", "running", "gym", "winter", "outdoor", "work")):
        return "use_case"
    return "feature"


def parse_intent(message: str, ask_attribute: str | None = None) -> IntentParse:
    """Parse one documented simulator message into observed claims."""
    looking_for = "I'm looking for "
    key_requirement = ". A key requirement is: "
    browsing_end = ", but I'm still exploring."
    override_start = "Actually, ignore my earlier preference. What I need is: "
    preference_start = "For that, what matters is: "

    if message.startswith(override_start) and message.endswith("."):
        value = message[len(override_start):-1]
        claim = ObservedClaim(_classify(value), value, "required")
        return IntentParse((claim,))

    if message.startswith(looking_for):
        body = message[len(looking_for):]
        if key_requirement in body and body.endswith("."):
            category, value = body[:-1].split(key_requirement, 1)
            return IntentParse((
                ObservedClaim("category", category, "required"),
                ObservedClaim(_classify(value), value, "required"),
            ))
        if body.endswith(browsing_end):
            category = body[:-len(browsing_end)]
            return IntentParse((ObservedClaim("category", category, "required"),))
        if ". " in body:
            category, value = body.split(". ", 1)
            return IntentParse((
                ObservedClaim("category", category, "required"),
                ObservedClaim(_classify(value), value, "preferred"),
            ))

    if ask_attribute:
        if message == f"I don't have a preference for {ask_attribute}; please use your judgment.":
            return IntentParse((ObservedClaim(ask_attribute, None, "indifferent"),))
        if message == f"I don't have an additional preference for {ask_attribute}.":
            return IntentParse((ObservedClaim(ask_attribute, None, "indifferent"),))
        if message.startswith(preference_start) and message.endswith("."):
            value = message[len(preference_start):-1]
            return IntentParse((ObservedClaim(ask_attribute, value, "preferred"),))
        if message:
            return IntentParse((ObservedClaim(ask_attribute, message, "preferred"),))

    return IntentParse((), unresolved=True)
