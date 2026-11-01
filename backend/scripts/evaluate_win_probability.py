"""Evaluate a persisted chase-win artifact on the chronological test split."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.services.ml.dataset_builder import build_training_dataset, load_matches_from_dir
from app.services.ml.evaluate import evaluate_binary_probabilities, write_calibration_plot
from app.services.ml.model_registry import load_model


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True, help="Path to a Joblib artifact")
    parser.add_argument(
        "--input",
        default=str(ROOT.parent / "data" / "raw" / "cricsheet" / "samples"),
    )
    parser.add_argument("--split", default="test", choices=("train", "validation", "test"))
    parser.add_argument("--plot", default="", help="Optional calibration PNG path")
    args = parser.parse_args()

    artifact = load_model(args.model)
    dataset = build_training_dataset(load_matches_from_dir(args.input))
    examples = dataset.examples_for(args.split)
    proba = [float(artifact.predict_proba(example.features)) for example in examples]
    report = evaluate_binary_probabilities(
        [example.label for example in examples],
        proba,
        match_ids=[example.source_match_id for example in examples],
        evaluation_is_meaningful=dataset.evaluation_is_meaningful and args.split == "test",
    )
    print(report.model_dump_json(indent=2))
    if args.plot:
        write_calibration_plot(
            [example.label for example in examples],
            proba,
            args.plot,
            title=f"{artifact.metadata.model_id} {args.split} calibration",
        )


if __name__ == "__main__":
    main()
