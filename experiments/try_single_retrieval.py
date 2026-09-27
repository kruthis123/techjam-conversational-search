from __future__ import annotations

import argparse
import json

from starter.catalog import load_catalog


def positive_int(value: str) -> int:
    depth = int(value)
    if depth <= 0:
        raise argparse.ArgumentTypeError("depths must be positive integers")
    return depth


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Try one retrieval route at several candidate depths"
    )
    parser.add_argument("route", choices=("lexical", "facet", "dense"))
    parser.add_argument("parent_asin", help="target product ID used only for diagnostics")
    parser.add_argument("--query", required=True, help="retrieval query text")
    parser.add_argument(
        "--depths",
        nargs="+",
        required=True,
        type=positive_int,
        help="one or more positive candidate depths",
    )
    parser.add_argument(
        "--catalog",
        default="data/catalog.jsonl",
        help="JSONL catalog path (default: %(default)s)",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    catalog = load_catalog(args.catalog)

    if args.route == "lexical":
        from starter.lexical_retrieval import LexicalRetriever

        retriever = LexicalRetriever(catalog)
    elif args.route == "facet":
        from starter.facet_retrieval import FacetRetriever

        retriever = FacetRetriever(catalog)
    else:
        from starter.dense_retrieval import DenseRetriever

        retriever = DenseRetriever(catalog)

    results = []
    for depth in args.depths:
        hits = retriever.search(args.query, depth)
        target_rank = next(
            (hit.rank for hit in hits if hit.parent_asin == args.parent_asin),
            None,
        )
        results.append(
            {
                "depth": depth,
                "target_rank": target_rank,
                "hits": [
                    {
                        "parent_asin": hit.parent_asin,
                        "rank": hit.rank,
                        "score": hit.score,
                    }
                    for hit in hits
                ],
            }
        )

    print(
        json.dumps(
            {
                "route": args.route,
                "target_parent_asin": args.parent_asin,
                "query": args.query,
                "results": results,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
