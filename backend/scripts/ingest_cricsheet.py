"""Ingest Cricsheet JSON files into normalized match records."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.services.ingestion import parse_cricsheet_file
from app.services.match_engine import validate_match


def main() -> int:
    parser = argparse.ArgumentParser(description="Normalize Cricsheet T20 match files")
    parser.add_argument(
        "--input",
        type=Path,
        required=True,
        help="Directory containing Cricsheet JSON files",
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Directory for normalized matches and validation reports",
    )
    args = parser.parse_args()

    files = sorted(args.input.glob("*.json"))
    if not files:
        print(f"No JSON files found in {args.input}")
        return 1

    matches_dir = args.output / "matches"
    reports_dir = args.output / "validation"
    matches_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    summary = []
    failures = 0
    for file_path in files:
        raw = json.loads(file_path.read_text(encoding="utf-8"))
        match = parse_cricsheet_file(file_path)
        report = validate_match(match, raw=raw)
        (matches_dir / f"{match.source_match_id}.json").write_text(
            match.model_dump_json(indent=2),
            encoding="utf-8",
        )
        (reports_dir / f"{match.source_match_id}.json").write_text(
            report.model_dump_json(indent=2),
            encoding="utf-8",
        )
        summary.append(
            {
                "source_match_id": match.source_match_id,
                "ok": report.ok,
                "innings": len(match.innings),
                "deliveries": len(match.deliveries),
                "errors": len(report.errors),
                "warnings": len(report.warnings),
            }
        )
        status = "OK" if report.ok else "FAIL"
        print(
            f"{status} {file_path.name} deliveries={len(match.deliveries)} errors={len(report.errors)}"
        )
        if not report.ok:
            failures += 1

    (args.output / "summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    print(f"Processed {len(files)} matches, {failures} failed validation")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
