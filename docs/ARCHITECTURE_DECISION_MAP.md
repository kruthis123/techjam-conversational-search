# Agent System-Design Study Map

This is the progress index for ARCHITECTING. The hackathon shopping agent is a running example, but each area teaches concepts that transfer to other agentic search and recommendation systems.

Work on one area at a time. Study what information the capability needs, how that information can be represented, which solution families exist, how they affect the whole agent, and what evidence distinguishes them. Avoid code organization and framework wiring unless the user explicitly asks.

| ID | System-design area | Guiding question | Related learning cards | Status | Record |
|---|---|---|---|---|---|
| SD-01 | Catalog knowledge and representations | How can raw product data be transformed into representations useful for retrieval, constraint matching, ranking, questioning, and grounded explanations? | LC-01, LC-04, LC-05 | Synthesized | SDR-001 |
| SD-02 | User intent and constraint understanding | How can a message become explicit needs, hard constraints, soft preferences, negations, uncertainty, and inferred intent? | LC-01, LC-03 | Synthesized | SDR-002 |
| SD-03 | Conversational memory and preference evolution | What should be remembered across turns, and how should evidence, additions, replacements, overrides, and indifference change current intent? | LC-02, LC-07, LC-09 | Synthesized | SDR-003 |
| SD-04 | Candidate retrieval | Which retrieval families can generate high-recall candidates from catalog representations and conversational intent? | LC-04, LC-12, LC-13 | Synthesized | SDR-004 |
| SD-05 | Constraint-aware candidate selection | How should confirmed matches, contradictions, missing metadata, uncertainty, and relaxation interact after retrieval? | LC-03, LC-05, LC-09 | Synthesized | SDR-005 |
| SD-06 | Ranking and reranking | Which relevance, preference, popularity, evidence, and diversity signals should order candidates, and how can unlike scores be combined? | LC-06, LC-12 | Synthesized | SDR-006 |
| SD-07 | Dialogue and next-question policy | How should the agent decide whether to ask, recommend, or do both, and which attribute would provide the most useful information? | LC-02, LC-08 | Synthesized | SDR-007 |
| SD-08 | Personalization | How can historical user information act as a useful prior without overriding current intent or narrowing candidates incorrectly? | LC-01, LC-10 | Synthesized | SDR-008 |
| SD-09 | Agent strategy and orchestration | How can the agent choose and revise reasoning, retrieval, ranking, and dialogue strategies based on uncertainty and observed outcomes? | LC-11, LC-13, LC-14 | Synthesized | SDR-009 |
| SD-10 | Grounded response and explanation | How can recommendations and questions be expressed using supported catalog evidence without inventing product claims? | LC-01, LC-02, LC-14 | Synthesized | SDR-010 |
| SD-11 | Evaluation and learning experiments | How should capability alternatives and the complete agent be evaluated for quality, generalization, conversation efficiency, failure modes, and cost? | LC-00, LC-12, LC-13 | Synthesized | SDR-011 |
| SD-12 | End-to-end conceptual agent | How do the chosen representations, capabilities, decisions, feedback loops, and evaluation signals form one coherent agent system? | LC-00 through LC-14 | Synthesized | SDR-012 |

## Status values

- `Not started`: study has not begun.
- `Active`: this is the current system-design topic.
- `Exploring`: representations and solution families are being learned.
- `Experimenting`: an approved learning experiment is in progress.
- `Synthesized`: the user has recorded a conceptual approach and trade-offs.
- `Open`: alternatives intentionally remain unresolved, with the missing evidence recorded.
- `Blocked`: prerequisite areas are incomplete.

## Per-area completion check

Before moving on, the system-design record should contain:

- the capability's role in the full agent;
- useful input and output information at a conceptual level;
- alternative representations and solution families;
- assumptions, strengths, failure modes, and system-level trade-offs;
- concepts and sources the user needed to research;
- a learning experiment or reason one was unnecessary;
- the user's synthesis, uncertainty, and implications for adjacent capabilities.
