"""Fit baseline chase-win models and persist Joblib artifacts."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.services.ml.dataset_builder import build_training_dataset, load_matches_from_dir
from app.services.ml.evaluate import write_calibration_plot
from app.services.ml.model_registry import save_model
from app.services.ml.train import fit_baseline_models


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        default=str(ROOT.parent / "data" / "raw" / "cricsheet" / "samples"),
    )
    parser.add_argument(
        "--output",
        default=str(ROOT / "models" / "artifacts"),
    )
    args = parser.parse_args()
    matches = load_matches_from_dir(args.input)
    dataset = build_training_dataset(matches)
    trained = fit_baseline_models(dataset)
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)

    metrics: dict[str, object] = {
        "evaluation_is_meaningful": dataset.evaluation_is_meaningful,
        "evaluation_limitation": dataset.evaluation_limitation,
        "train_match_ids": list(dataset.train_match_ids),
        "validation_match_ids": list(dataset.validation_match_ids),
        "test_match_ids": list(dataset.test_match_ids),
        "models": {},
    }
    for name, result in trained.items():
        artifact_path = output / f"{result.artifact.metadata.model_id}.joblib"
        if name != "heuristic":
            save_model(result.artifact, artifact_path)
        else:
            save_model(result.artifact, artifact_path)
        metrics["models"][name] = {
            "artifact": str(artifact_path),
            "metadata": result.artifact.metadata.model_dump(),
            "reports": {split: report.model_dump() for split, report in result.report.items()},
        }
        test_examples = dataset.examples_for("test")
        if test_examples:
            write_calibration_plot(
                [example.label for example in test_examples],
                [float(result.artifact.predict_proba(example.features)) for example in test_examples],
                output / f"{name}_test_calibration.png",
                title=f"{name} test calibration (not a production evaluation)",
            )

    metrics_path = output / "metrics.json"
    metrics_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    print(json.dumps({"metrics": str(metrics_path), **{k: metrics[k] for k in (
        "evaluation_is_meaningful",
        "evaluation_limitation",
        "train_match_ids",
        "validation_match_ids",
        "test_match_ids",
    )}}, indent=2))
    for name, payload in metrics["models"].items():
        reports = payload["reports"]
        print(f"\n{name}")
        for split, report in reports.items():
            print(
                f"  {split}: n={report['n_rows']} matches={report['n_matches']} "
                f"log_loss={report['log_loss']} brier={report['brier_score']} "
                f"auc={report['roc_auc']} acc={report['accuracy']} "
                f"meaningful={report['evaluation_is_meaningful']}"
            )


if __name__ == "__main__":
    main()
