# M1 experiment: Inspect the catalog representation baseline

## Decision owner

The user runs and interprets this experiment. Codex has verified the implementation but must not choose the winning representation.

## What was implemented

- `starter/catalog.py` preserves each raw catalog object and indexes it by `parent_asin`.
- `starter/price_claims.py` emits a small immutable claim for numeric prices and abstains for missing or string prices.
- `starter/category_claims.py` trims and case-folds category text, removes repeated values within one product, and preserves category order.
- Each derived claim identifies its source field. Raw records are never modified.

No material aliases, taxonomy, generic claim framework, string-price parser, index, or Agent integration exists yet.

## Fixed records

| Purpose | `parent_asin` |
| --- | --- |
| Numeric price | `B07KCFS4VC` |
| Null price | `B07K34RX5J` |
| Em-dash price | `B01N0I8BFI` |
| Lower-bound string price | `B00NMVPTHS` |
| Repeated category | `B08MCH6YCV` |

## Run the inspection

From the repository root, run:

```bash
python3.12 - <<'PY'
from starter.catalog import load_catalog
from starter.category_claims import category_claims
from starter.price_claims import price_claim

records = load_catalog("data/catalog.jsonl")
asins = [
    "B07KCFS4VC",
    "B07K34RX5J",
    "B01N0I8BFI",
    "B00NMVPTHS",
    "B08MCH6YCV",
]

for asin in asins:
    record = records[asin]
    print("\n", asin)
    print("raw price:     ", repr(record["price"]))
    print("price claim:   ", price_claim(record))
    print("raw categories:", record["categories"])
    print("category claims:", category_claims(record))
PY
```

Then read these three files in order:

1. `starter/catalog.py`
2. `starter/price_claims.py`
3. `starter/category_claims.py`

## Questions to answer

1. **Price abstention:** Should string prices remain unsupported for this baseline, or should `from 12.99` become a lower-bound price claim? The fixed catalog contains only five `from N.NN` values.
2. **Category normalization:** For `B08MCH6YCV`, is turning both occurrences of `Shoes` into one `shoes` claim appropriate for later facet retrieval?
3. **Representation shape:** After reading both claim modules, choose one:
   - keep the two small task-specific claim types;
   - replace them with one generic claim carrying attribute, value, and source field;
   - defer this choice until retrieval needs a common interface.
4. **Understandability:** Can you explain, without reading the tests, where each derived value came from and why raw catalog truth remains unchanged?

## Decision to report

Reply with:

```text
Price strings: keep unsupported / parse lower bound
Repeated categories: deduplicate / preserve
Claim representation: separate / generic / defer
Reasoning: ...
```

M1 remains open until this decision is recorded. No M2 implementation should begin before then.

## User result

Recorded on `2026-09-21`:

- Price strings: keep unsupported.
- Repeated categories: deduplicate.
- Claim representation: keep separate task-specific claim types.
- Reasoning: the claims are transparently constructed from the product's raw `price` and `categories` JSON fields.

The experiment therefore accepts the implemented price and category behavior without a code change. On `2026-09-21`, the user approved matching the roadmap gate to this simplified learning scope, so M1 is complete. The broader alias, unit, component, conflict, and compatibility audit remains deferred until evidence requires it.
