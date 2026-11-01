"""Audit Cricsheet files for Phase 2 chase-win training eligibility."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.services.ml.dataset_builder import audit_matches, load_matches_from_dir


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        default=str(ROOT.parent / "data" / "raw" / "cricsheet" / "samples"),
        help="Directory of official Cricsheet JSON files",
    )
    parser.add_argument(
        "--output",
        default="",
        help="Optional JSON path for the audit report",
    )
    args = parser.parse_args()
    matches = load_matches_from_dir(args.input)
    audit = audit_matches(matches)
    print(audit.model_dump_json(indent=2))
    if args.output:
        path = Path(args.output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(audit.model_dump_json(indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
