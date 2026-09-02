"""Label-free multi-turn demonstration for the packaged agent."""

from __future__ import annotations

import json
import os

from agent import Agent


MESSAGES = (
    "I'm looking for footwear, but I'm still exploring.",
    "I don't have a material preference; please use your judgment.",
    "Let's focus on women's slippers for wearing at home.",
    "Keep them under $40 and make comfort the priority.",
    "Actually, I need men's waterproof hiking boots under $120.",
    "Size 10, preferably leather.",
)

PROFILE = {
    "purchase_frequency": "occasional",
    "average_prior_rating": 4.2,
    "rating_style": "balanced",
    "preference_tags": ["comfort", "durable"],
    "summary": "Usually values comfortable, durable products.",
}


def main() -> None:
    catalog_path = os.environ.get("TECHJAM_CATALOG_PATH", "data/catalog.jsonl")
    agent = Agent(catalog_path)
    session_id = "submission_demo"
    agent.reset(session_id, PROFILE)

    for turn, message in enumerate(MESSAGES, start=1):
        response = agent.respond(session_id, message, turn, 10)
        trace = agent.get_last_trace(session_id)
        summary = {
            "turn": turn,
            "user": message,
            "route": trace.get("inferred_route"),
            "active_slots": trace.get("active_slots"),
            "search_revision": trace.get("search_revision"),
            "ask_attribute": response.get("ask_attribute"),
            "message": response.get("message"),
            "recommendations": [
                item["parent_asin"] for item in response.get("recommendations", [])
            ],
            "fallback_used": trace.get("fallback_used"),
        }
        print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
