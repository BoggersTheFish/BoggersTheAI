"""CLI for deterministic TS-AI constraint-field reasoning."""

from __future__ import annotations

import argparse
import json

from .constraint_fields import compare_concept_fields, export_receipt, verify_analogy


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compare and verify canonical constraint-field concept examples."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    compare_parser = subparsers.add_parser("compare", help="Compare two concept fields.")
    compare_parser.add_argument("source")
    compare_parser.add_argument("target")
    compare_parser.add_argument("--receipt", action="store_true", help="Print only the audit receipt.")

    analogy_parser = subparsers.add_parser(
        "verify-analogy",
        help="Verify whether a source-to-target analogy is structurally valid.",
    )
    analogy_parser.add_argument("source")
    analogy_parser.add_argument("target")
    analogy_parser.add_argument("--receipt", action="store_true", help="Print only the audit receipt.")

    args = parser.parse_args()
    if args.command == "compare":
        result = compare_concept_fields(args.source, args.target)
    else:
        result = verify_analogy(args.source, args.target)

    payload = export_receipt(result) if args.receipt else result
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
