"""Build the chase-win training table from official Cricsheet JSON."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.services.ml.dataset_builder import (
    build_training_dataset,
    load_matches_from_dir,
    write_dataset,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        default=str(ROOT.parent / "data" / "raw" / "cricsheet" / "samples"),
    )
    parser.add_argument(
        "--output",
        default=str(ROOT.parent / "data" / "processed" / "ml"),
    )
    args = parser.parse_args()
    matches = load_matches_from_dir(args.input)
    dataset = build_training_dataset(matches)
    paths = write_dataset(dataset, args.output)
    summary = {
        "usable_matches": dataset.audit.completed_usable_matches,
        "examples": len(dataset.examples),
        "train_matches": list(dataset.train_match_ids),
        "validation_matches": list(dataset.validation_match_ids),
        "test_matches": list(dataset.test_match_ids),
        "evaluation_is_meaningful": dataset.evaluation_is_meaningful,
        "evaluation_limitation": dataset.evaluation_limitation,
        "paths": {name: str(path) for name, path in paths.items()},
    }
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
