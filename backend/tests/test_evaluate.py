from app.services.ml.evaluate import MATCH_LEVEL_AGGREGATION, evaluate_binary_probabilities


def test_match_level_metrics_give_each_match_equal_weight():
    # Ten deliveries from a chase win, two from a chase loss, all with the
    # same predicted probability. Delivery-level accuracy is dominated by the
    # long match; match-level accuracy is 0.5.
    y_true = [1] * 10 + [0] * 2
    y_proba = [0.6] * 12
    match_ids = ["long"] * 10 + ["short"] * 2
    report = evaluate_binary_probabilities(
        y_true,
        y_proba,
        match_ids=match_ids,
        evaluation_is_meaningful=False,
    )
    assert report.n_rows == 12
    assert report.n_matches == 2
    assert report.accuracy == 10 / 12
    assert report.match_level is not None
    assert report.match_level.aggregation == MATCH_LEVEL_AGGREGATION
    assert report.match_level.n_matches == 2
    assert report.match_level.n_positive_matches == 1
    assert report.match_level.n_negative_matches == 1
    assert report.match_level.accuracy == 0.5
    assert report.match_level.roc_auc is not None
    assert any("mean delivery probability" in note.lower() or "mean_delivery" in note for note in report.notes)


def test_delivery_level_metrics_remain_available_as_diagnostics():
    report = evaluate_binary_probabilities(
        [0, 0, 1, 1],
        [0.2, 0.4, 0.8, 0.7],
        match_ids=["a", "a", "b", "b"],
        evaluation_is_meaningful=False,
    )
    assert report.log_loss is not None
    assert report.brier_score is not None
    assert report.evaluation_is_meaningful is False
    assert report.match_level is not None
    assert report.match_level.n_matches == 2
    assert report.match_level.n_positive_matches == 1
    assert report.match_level.n_negative_matches == 1
