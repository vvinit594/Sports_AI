from pathlib import Path

from app.core.exceptions import InferenceError
from app.services.ml.dataset_builder import build_training_dataset
from app.services.ml.evaluate import evaluate_binary_probabilities
from app.services.ml.features import FEATURE_NAMES, FEATURE_SCHEMA_VERSION, is_chase_training_state
from app.services.ml.inference import predict_batch, predict_one
from app.services.ml.model_registry import ModelArtifact, ModelMetadata, load_model, save_model
from app.services.ml.train import fit_baseline_models
from tests.ml_helpers import two_innings_chase


def _heuristic_artifact() -> ModelArtifact:
    return ModelArtifact(
        estimator=None,
        metadata=ModelMetadata(
            model_id="test_heuristic",
            model_kind="heuristic",
            feature_schema_version=FEATURE_SCHEMA_VERSION,
            feature_names=FEATURE_NAMES,
            trained_at="2024-01-01T00:00:00+00:00",
            target_definition="test",
        ),
    )


def _labeled_matches():
    matches = []
    for index, (date, winner) in enumerate(
        [
            ("2020-01-01", "Beta"),
            ("2020-01-02", "Alpha"),
            ("2020-01-03", "Beta"),
            ("2020-01-04", "Alpha"),
        ]
    ):
        match, _ = two_innings_chase(
            match_id=f"inf-{index}",
            date=date,
            first_innings_runs=[1, 1, 1, 1, 1, 1],
            chase_runs=[1, 1, 1, 4] if winner == "Beta" else [0] * 12,
            winner=winner,
            outcome={"winner": winner, "by": {"wickets": 3} if winner == "Beta" else {"runs": 6}},
        )
        matches.append(match)
    return matches


def test_heuristic_inference_stays_within_probability_bounds():
    match, states = two_innings_chase(
        match_id="inf-bounds",
        date="2024-01-01",
        first_innings_runs=[1, 1, 1, 1, 1, 1],
        chase_runs=[1, 1, 1],
        winner="Beta",
    )
    artifact = _heuristic_artifact()
    chase = [state for state in states if is_chase_training_state(state)]
    prediction = predict_one(artifact, chase[0], states, match=match)
    assert 0.0 <= prediction.probability <= 1.0


def test_inference_refuses_terminal_and_first_innings_states():
    match, states = two_innings_chase(
        match_id="inf-refuse",
        date="2024-01-01",
        first_innings_runs=[1, 1, 1, 1, 1, 1],
        chase_runs=[7],
        winner="Beta",
    )
    artifact = _heuristic_artifact()
    first = next(state for state in states if state.innings_number == 1 and state.last_delivery)
    finished = next(state for state in states if state.innings_complete)
    try:
        predict_one(artifact, first, states, match=match)
    except InferenceError:
        pass
    else:
        raise AssertionError("first innings should be refused")
    try:
        predict_one(artifact, finished, states, match=match)
    except InferenceError as exc:
        assert "completed" in str(exc) or "terminal" in str(exc)
    else:
        raise AssertionError("terminal state should be refused")


def test_batch_inference_records_errors_without_inventing_probabilities():
    match, states = two_innings_chase(
        match_id="inf-batch",
        date="2024-01-01",
        first_innings_runs=[1, 1, 1, 1, 1, 1],
        chase_runs=[1, 7],
        winner="Beta",
    )
    results = predict_batch(_heuristic_artifact(), states, match=match)
    assert any(result.ok for result in results)
    assert any(result.error for result in results)
    for result in results:
        if result.prediction is not None:
            assert 0.0 <= result.prediction.probability <= 1.0


def test_model_persistence_round_trip(tmp_path: Path):
    dataset = build_training_dataset(_labeled_matches())
    trained = fit_baseline_models(dataset)
    path = tmp_path / "lr.joblib"
    save_model(trained["logistic_regression"].artifact, path)
    loaded = load_model(path)
    match, states = two_innings_chase(
        match_id="inf-0",
        date="2020-01-01",
        first_innings_runs=[1, 1, 1, 1, 1, 1],
        chase_runs=[1, 1, 1, 4],
        winner="Beta",
    )
    chase = next(state for state in states if is_chase_training_state(state))
    original = predict_one(trained["logistic_regression"].artifact, chase, states, match=match)
    restored = predict_one(loaded, chase, states, match=match)
    assert original.probability == restored.probability
    assert loaded.metadata.feature_schema_version == FEATURE_SCHEMA_VERSION


def test_evaluation_helper_computes_held_out_metrics_without_claiming_quality():
    report = evaluate_binary_probabilities(
        [0, 1, 0, 1],
        [0.2, 0.8, 0.4, 0.7],
        match_ids=["a", "a", "b", "b"],
        evaluation_is_meaningful=False,
    )
    assert report.n_rows == 4
    assert report.n_matches == 2
    assert report.log_loss is not None
    assert report.brier_score is not None
    assert report.roc_auc is not None
    assert report.evaluation_is_meaningful is False
    assert 0.0 <= report.accuracy <= 1.0
