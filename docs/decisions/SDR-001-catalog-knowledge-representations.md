# SDR-001: Catalog knowledge and representations

- Status: `Synthesized`
- Author: `User`
- Date: `2026-09-15`
- System-design area: `SD-01`
- Related learning cards: `LC-01`, `LC-04`, `LC-05`
- Case-study references: `docs/competition_specification.md`

## System question

How can raw product-catalog data be transformed into representations useful for retrieval, constraint matching, ranking, selecting useful questions, and producing grounded explanations?

## Why this capability matters

Every later capability sees the catalog through some representation. A representation that is useful for keyword retrieval may be poor for semantic similarity or hard-constraint checks. The system may therefore need complementary views rather than one universally best representation.

## Information available

The case-study catalog exposes product identifier, title, features, description, price, categories, details, average rating, rating count, and store. These are observed catalog fields. Normalized attributes, embeddings, taxonomy links, aliases, and inferred properties would be derived representations and must retain provenance. Unsupported properties remain unknown.

## Useful representations

To explore:

- raw fielded product documents;
- normalized structured attributes or facets;
- lexical index representations;
- dense vector embeddings;
- sparse learned representations;
- category hierarchies or product taxonomies;
- entity and attribute graphs;
- multiple complementary representations joined by product identity.

For each representation, determine what it preserves, what it loses, and whether it supports retrieval, exact constraints, ranking, question selection, and explanation.

## Solution families to learn

- information-retrieval document and field modeling;
- faceted search and attribute normalization;
- lexical retrieval such as inverted indexes and BM25-style scoring;
- dense embedding retrieval and vector similarity;
- sparse neural retrieval;
- hybrid retrieval and score fusion;
- taxonomies, ontologies, and knowledge graphs for product relationships.

## What I need to research

- Concepts and vocabulary: document representation, field weighting, normalization, facets, inverted index, embeddings, sparse vectors, taxonomy, ontology, knowledge graph, provenance.
- Algorithms or system patterns: lexical, dense, sparse, hybrid, faceted, and graph-assisted product search.
- Sources: introductory information-retrieval material, primary papers for learned retrieval methods, and system descriptions of faceted product search.
- Questions the research must answer:
  - Which representations support high recall when user and catalog wording differ?
  - Which representations support reliable hard-constraint checks?
  - How can missing versus contradictory attributes remain distinguishable?
  - Which representations can justify a recommendation using catalog evidence?
  - When are multiple representations complementary rather than redundant?

## Comparison criteria

To be confirmed by the user after the representation families are taught. Candidate criteria include retrieval recall, constraint reliability, information loss, support for multiple downstream capabilities, explainability, preprocessing effort, update cost, latency, memory, and data requirements.

## Study sequence

1. Distinguish raw evidence, derived representations, indexes, retrieval methods, and ranking signals.
2. Compare fielded text, normalized facets, lexical vectors, dense vectors, learned sparse or multi-vector representations, and taxonomy/graph representations.
3. Map each representation to retrieval, constraint matching, ranking, question selection, and grounded explanation.
4. Use a toy catalog to expose information preserved, lost, or invented by each representation.
5. Record the user's conceptual multi-representation strategy or unresolved alternatives.

## Worked example or thought experiment

Fictional query: "I need an everyday bag for a rainy commute. Nylon only, fits a 15-inch laptop, under $80."

Fictional products:

- A: title "RainShield commuter backpack"; details explicitly state nylon, water-resistant, 15-inch sleeve, and price $72.
- B: title "Urban daypack"; description says "coated shell"; details explicitly state polyester, 16-inch sleeve, and price $60; water resistance is unspecified.
- C: title "Lightweight laptop bag"; details explicitly state nylon, not waterproof, 15-inch sleeve, and price $55.

The exercise will compare what raw fielded text, normalized facets, lexical terms, dense vectors, and taxonomy links can retrieve or establish. "Coated shell" must not silently become a supported water-resistant claim.

### User's first paper-exercise answers

1. "normalized facets - bag, nylon, fits 15 inch laptop, under $80. Original text - everyday bag for rainy commute"
2. "dense embedding, multi vector representation, taxonomy and ontology if combined with ai powered keyword generation, sparse learned representations, hybrid representation, knowledge graphs (if formed to contain synonym nodes)"
3. "facets and inverted indexes if products can map back to attributes also, taxonomy and ontology, knowledge graph, hybrid representation"

### Facilitator feedback

- The first answer describes the interpreted query rather than the fictional Urban daypack. The product's observed or normalized catalog facts are `product_type=daypack/bag`, `material=polyester`, `laptop_sleeve=16-inch`, `price=60`, and `water_resistance=unknown`; its original title and "coated shell" description should remain available. On the query side, nylon, 15-inch fit, and budget under $80 are constraints, while everyday rainy commute is use-case text. Search depends on aligning these two representations without confusing them.
- Dense, learned sparse, multi-vector, taxonomy/ontology, graph-assisted, and hybrid representations can all help retrieve semantic or related matches. Retrieval does not make this product eligible: its observed polyester material contradicts the hard nylon requirement. Query or keyword expansion is a retrieval-time technique rather than an inherent property of a taxonomy.
- Facets make candidate attribute coverage, variation, and missingness directly measurable for question selection. An inverted index can map attribute terms back to products, while taxonomies and graphs can support relationships and abstraction. A hybrid representation is useful only when the system defines which view supplies evidence for each decision.

### User's initial system-design direction

1. "raw catalog fields must remain the source of truth"
2. "facets (sparsed learned representations), embeddings (multi view representations), taxonomy links, graph relationships - all precomputed. Start with first 2, analyze performance and then move to building the other 2"
3. "Every representation can have a standard provenance representation to denote whether it is observed normalized or inferred and capabilities can score based on this property"

### Facilitator refinement

- Keeping raw catalog fields as the factual source of truth is a clear conceptual choice. Derived views must remain linked to the source evidence rather than replacing it.
- Facets and learned sparse representations are different: facets are canonical attribute-value facts, while learned sparse representations are weighted vocabulary dimensions produced by a retrieval model.
- A dense embedding is one representation view. "Multi-view" means retaining complementary views such as raw text, facets, lexical or learned sparse vectors, dense embeddings, taxonomy links, and graph relationships; it is not another name for embeddings.
- The staged idea is testable: begin with normalized facets and dense embeddings, measure downstream gaps, and add taxonomy or graph representations only when evidence shows that they address those gaps. The role of ordinary lexical representations remains unresolved and should be compared rather than omitted implicitly.
- Provenance should normally attach to an individual value or relationship. One product may have observed material, normalized color, and inferred use case simultaneously. Embedding similarity is a retrieval or ranking signal rather than a factual claim and should not be treated as observed product evidence.

### User's refinement of the staged strategy

1. Include normalized facets, a basic lexical representation, and dense embeddings in the first stage.
2. Use provenance differently according to the needs of each downstream capability rather than applying one universal provenance score.
3. Use low recall as the general signal for considering taxonomy links or graph relationships.

### Remaining refinement

Low recall must be classified by cause before adding a representation:

- Taxonomy links are candidates when misses arise from category hierarchy, aliases, broader/narrower concepts, or category-specific vocabulary.
- Graph relationships are candidates when misses require explicit relational or multi-hop knowledge, such as product-to-use-case, compatibility, or attribute relationships not recoverable from text, facets, embeddings, or taxonomy.
- Low recall caused by poor tokenization, weak lexical weighting, unsuitable embeddings, or bad query representation should be addressed in those areas rather than used to justify a taxonomy or graph.

The relevant evidence is marginal recall improvement on the failure slice, balanced against representation construction, maintenance, latency, and unsupported-edge risk.

### Open comparison: single-vector versus multi-view dense representation

The user asked whether to replace one product-level dense embedding with LLM-generated product views that are embedded separately.

These are not mutually exclusive representation families: a multi-view design normally stores several dense embeddings per product. Three alternatives should be distinguished:

1. One dense vector produced from a field-labeled product document.
2. Several deterministic dense views produced from existing fields or source-bound segments, such as title/category, features/details, and description/use-case text.
3. Several LLM-generated views, such as proposed use cases, audience, or style, each linked to supporting source text and marked as inferred when not directly observed.

More views can preserve fine-grained aspects that a single vector dilutes, but they can also increase false positives, storage, indexing work, score-fusion complexity, and query latency. LLM-generated views add variation and possible unsupported information, so they must not become factual evidence for hard constraints or explanations merely because their vectors match.

The planned learning comparison is staged:

- establish a one-vector dense baseline;
- compare deterministic field/view embeddings against it;
- test LLM-generated views only if error analysis shows that deterministic views still miss important query aspects.

Use identical query slices for category, exact attribute, paraphrase/use case, brand/model, and mixed constraints. Compare Recall@K, ranking quality or false-positive rate, vectors per product, index size, preprocessing cost, and query latency.

Research evidence:

- Dense dual-encoder retrieval demonstrates the one-query-vector/one-document-vector baseline: https://arxiv.org/abs/2004.04906
- ColBERT demonstrates fine-grained multi-vector late interaction and its quality-cost trade-off: https://arxiv.org/abs/2004.12832
- Product descriptions can contain verbose or irrelevant sentences, so treating all description content equally may hurt matching: https://arxiv.org/abs/1907.06330
- Generative query or document expansion is not universally beneficial and can introduce noise: https://aclanthology.org/2024.findings-eacl.134/
- Industrial embedding-based product retrieval reports relevance failures and uses component-wise evaluation rather than assuming embedding complexity is automatically better: https://arxiv.org/abs/2106.09297

## Learning experiment

The first experiment is a paper representation audit over the fictional products above. For each representation, record which facts are directly recoverable, which semantic matches are plausible, which hard constraints can be verified, and which values remain unknown.

A later toy or offline benchmark may compare raw text, normalized facets, lexical representations, and embeddings over the same small catalog and fixed queries. It will be proposed only if the paper audit cannot distinguish their roles.

## My synthesis

Accepted by the user on `2026-09-16`:

- Raw catalog fields remain the factual source of truth, and original text remains available for grounding and explanation.
- The initial derived views are normalized facets, a basic lexical representation, and dense embeddings.
- Provenance attaches to individual claims or relationships. Downstream capabilities interpret observed, normalized, inferred, unknown, and similarity evidence according to their own risk: retrieval may use weak signals, hard filtering requires reliable facts, ranking may use weaker evidence with reduced influence, and explanations require traceable support.
- Dense representation will be studied through a staged comparison:
  1. establish one field-labelled dense vector per product as the baseline;
  2. compare deterministic, source-bound multi-view vectors against that baseline;
  3. test LLM-generated views only if error analysis shows that deterministic views still miss important semantics.
- LLM-generated views remain inferred retrieval signals linked to source evidence; they do not establish hard product facts.
- Representation alternatives are compared on fixed query slices using recall, false positives or ranking quality, index size, preprocessing cost, and latency.
- Taxonomy links are considered when recall failures arise from category hierarchy, aliases, or broader/narrower concepts.
- Graph relationships are considered when recall failures require explicit relational or multi-hop knowledge.
- Learned sparse and token-level multi-vector retrieval remain open for comparison in `SD-04`, where retrieval strategies are studied directly.

The user accepted this synthesis without selecting an implementation technology.

## Connections to the rest of the agent

- Information required from upstream capabilities: raw catalog fields and trustworthy product identity.
- Information supplied to downstream capabilities: searchable product representations, structured evidence, similarity signals, and provenance.
- New questions created for later areas: how user intent should be represented so it can query these catalog views, and how retrieval and ranking should combine their evidence.

## Architecture critic feedback

Awaiting user synthesis.

## Revisit conditions

Revisit when later retrieval, ranking, dialogue, or explanation needs cannot be supported by the selected catalog representations.
