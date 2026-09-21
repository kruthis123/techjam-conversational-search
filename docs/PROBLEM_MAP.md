# Problem Map

This map decomposes the official problem into learning-sized questions. It deliberately does not define modules, technologies, or an architecture.

Work on one card at a time. A card is complete when you can explain it in your own words, compare plausible solution families, and record your conclusion or remaining uncertainty.

| ID | Small question | You should be able to explain | Status |
|---|---|---|---|
| LC-00 | What exactly is evaluated? | Session lifecycle, output contract, hit, rank, turn, misses, scenario metrics, and composite score | Complete |
| LC-01 | What information exists? | Catalog fields, session inputs, user profile, unavailable/private information, and leakage risks | Complete |
| LC-02 | How does the simulated conversation evolve? | `ask_attribute`, customer replies, termination, Buying, Browsing, Intent Override, and Boundary behavior | Complete |
| LC-03 | What must be understood from a user message? | Product need, hard versus soft preferences, ambiguity, negation, replacement, and uncertainty | Complete |
| LC-04 | How can a large catalog produce candidates? | Exact, lexical, structured, semantic, graph/taxonomy, and hybrid search families and their recall risks | Complete |
| LC-05 | How can hard constraints be applied safely? | Parsing, normalization, missing metadata, contradictions, relaxation, and false exclusion | Complete |
| LC-06 | How can candidates be ordered? | Scoring signals, fusion, learned versus rule-based ranking, reranking, calibration, and MRR effects | Complete |
| LC-07 | What state must survive across turns? | Observations, beliefs, active preferences, provenance, confidence, history compression, and reset semantics | Complete |
| LC-08 | When is a clarification worth a turn? | Candidate uncertainty, information gain, question cost, attribute availability, and recommend-versus-ask choices | Complete |
| LC-09 | How should replaced or absent preferences behave? | Intent override detection, stale-state invalidation, boundary replies, and recovery | Complete |
| LC-10 | How can the aggregate user profile help safely? | Prior versus evidence, weak personalization, conflict resolution, cold start, and over-personalization | Complete |
| LC-11 | How can strategy change at runtime? | Signals for choosing or switching behaviors, fallbacks, failure detection, and deterministic control | Complete |
| LC-12 | How will public results predict private results? | Train/dev discipline, ablations, scenario slices, error taxonomy, leakage prevention, and confidence intervals | Complete |
| LC-13 | What operational constraints matter? | Latency, memory, offline execution, dependency/model cost, token reporting, determinism, and reproducibility | Complete |
| LC-14 | How will your decisions become a coherent system? | Boundaries, interfaces, data flow, ownership, failure paths, observability, and test seams | Complete |

## Rule for adding cards

Split a card when it requires more than one session to understand or contains two decisions that could be made independently. New cards describe questions, not proposed components.
