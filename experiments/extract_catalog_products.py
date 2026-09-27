from __future__ import annotations

import argparse
import json
from pathlib import Path

from starter.catalog import load_catalog


SAVED_PARENT_ASINS = [
    "B09PYB7B6Z",
    "B0B6FZH11D",
    "B01EX670LS",
    "B09JC4FKXL",
    "B07TS5Q2G6",
    "B010AI7T2S",
    "B013Q214QW",
    "B06Y69YN9M",
    "B00RKW35S0",
    "B07S85N55P",
    "B07DL6FDPX",
    "B09LV2N6CM",
    "B078Q424MT",
    "B0140NWUGE",
    "B072PTLN1L",
    "B07ZBY23VF",
    "B0185S1S5Y",
    "B07RPV75CN",
    "B086ZXZ8CX",
    "B00VX0HZEK",
    "B00CPZ15NO",
    "B07ZKZNMJ5",
    "B07CVVF3G2",
    "B09LH42SCL",
    "B08T9BLC57",
    "B07ZSX4W15",
    "B08L1YYC69",
    "B01EYU2NNI",
    "B09JKP6HTS",
    "B01IGYIPFI",
    "B08R41PBY9",
    "B01DS32E9U",
    "B09C4KLG2L",
    "B09C8H33CM",
    "B078G14ZLQ",
    "B00U9PQP1Y",
    "B08CGJ3Z3M",
    "B00H1RMI4G",
    "B075KXNBNF",
    "B0BCHMS67C",
    "B0B3MQKT6F",
    "B01IGXIBCG",
    "B00ET7Q3PQ",
    "B088NN4MVR",
    "B0B7GDF3VM",
    "B078VV63XX",
    "B08QSFL94N",
    "B0768LTBW6",
    "B09Q64L77P",
    "B083WG73FZ",
    "B06XHZ7WDQ",
]


def extract_products(
    catalog: dict[str, dict[str, object]],
    parent_asins: list[str],
    excluded_fields: list[str],
) -> list[dict[str, object]]:
    missing = [parent_asin for parent_asin in parent_asins if parent_asin not in catalog]
    if missing:
        raise ValueError(f"missing parent_asin: {', '.join(missing)}")

    excluded = set(excluded_fields)
    return [
        {
            field: value
            for field, value in catalog[parent_asin].items()
            if field not in excluded
        }
        for parent_asin in parent_asins
    ]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Write selected raw catalog products as readable JSON"
    )
    parser.add_argument(
        "parent_asins",
        nargs="*",
        help="one or more parent_asin values in requested order",
    )
    parser.add_argument(
        "--catalog",
        default="data/catalog.jsonl",
        help="JSONL catalog path (default: %(default)s)",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="required output path for the indented JSON array",
    )
    parser.add_argument(
        "--exclude",
        nargs="*",
        default=[],
        help="zero or more top-level field names to omit",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    catalog = load_catalog(args.catalog)
    try:
        parent_asins = args.parent_asins or SAVED_PARENT_ASINS
        products = extract_products(catalog, parent_asins, args.exclude)
    except ValueError as error:
        parser.error(str(error))

    output = json.dumps(products, indent=2) + "\n"
    Path(args.output).write_text(output, encoding="utf-8")


if __name__ == "__main__":
    main()
