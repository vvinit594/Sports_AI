from pathlib import Path

from app.services.ml.dataset_builder import (
    audit_matches,
    build_training_dataset,
    load_matches_from_dir,
)

SAMPLE_DIR = (
    Path(__file__).resolve().parents[2] / "data" / "raw" / "cricsheet" / "samples"
)


def test_official_sample_audit_counts():
    matches = load_matches_from_dir(SAMPLE_DIR)
    audit = audit_matches(matches)
    assert audit.total_matches == 15
    assert audit.valid_t20_matches == 15
    assert audit.completed_usable_matches == 11
    assert audit.abandoned_or_no_result == 1
    assert audit.tied_matches == 2
    assert audit.dls_or_method_matches == 1
    assert audit.unsupported_match_formats == 0
    assert audit.super_over_or_eliminator_matches == 0
    assert audit.missing_or_invalid_binary_outcomes == 0
    assert audit.incomplete_or_unsupported == 0
    assert (
        audit.completed_usable_matches
        + audit.unsupported_match_formats
        + audit.abandoned_or_no_result
        + audit.tied_matches
        + audit.dls_or_method_matches
        + audit.super_over_or_eliminator_matches
        + audit.missing_or_invalid_binary_outcomes
        + audit.incomplete_or_unsupported
        == audit.total_matches
    )
    assert audit.usable_delivery_states == 1268
    assert "1082625" in audit.excluded_match_ids
    assert "1082648" in audit.excluded_match_ids
    assert "1216517" in audit.excluded_match_ids
    assert "1359519" in audit.excluded_match_ids


def test_official_sample_split_is_not_a_meaningful_evaluation():
    dataset = build_training_dataset(load_matches_from_dir(SAMPLE_DIR))
    assert dataset.evaluation_is_meaningful is False
    assert dataset.evaluation_limitation is not None
    assert (
        len(dataset.train_match_ids)
        + len(dataset.validation_match_ids)
        + len(dataset.test_match_ids)
        == 11
    )
    assert set(dataset.train_match_ids).isdisjoint(dataset.test_match_ids)
