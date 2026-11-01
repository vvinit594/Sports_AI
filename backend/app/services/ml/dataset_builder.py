"""Construct delivery-level chase-win training examples from Phase 1 states.

Labels are match-level: 1 if the chasing team won the regulation match.
Splits are match-level and chronological. Deliveries from one match never
appear in more than one split.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from pathlib import Path

import pandas as pd
from pydantic import BaseModel, ConfigDict

from app.core.constants import T20_MATCH_TYPES
from app.core.exceptions import DatasetError
from app.schemas.match import NormalizedMatch
from app.schemas.state import MatchState
from app.services.ingestion import parse_cricsheet_file
from app.services.match_engine import MatchStateEngine
from app.services.ml.features import (
    FEATURE_NAMES,
    FEATURE_SCHEMA_VERSION,
    FeatureVector,
    extract_feature_vector,
    is_chase_training_state,
)

TRAIN_FRACTION = 0.70
VALIDATION_FRACTION = 0.15
TEST_FRACTION = 0.15
MIN_MATCHES_FOR_THREE_WAY_SPLIT = 3
MIN_MATCHES_FOR_MEANINGFUL_EVAL = 50
MIN_TEST_MATCHES_FOR_MEANINGFUL_EVAL = 8


class DatasetAudit(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    total_matches: int
    valid_t20_matches: int
    completed_usable_matches: int
    unsupported_match_formats: int = 0
    abandoned_or_no_result: int
    tied_matches: int
    dls_or_method_matches: int
    super_over_or_eliminator_matches: int
    missing_or_invalid_binary_outcomes: int = 0
    incomplete_or_unsupported: int
    usable_delivery_states: int
    source_deliveries: int
    reconstructed_states: int
    excluded_match_ids: tuple[str, ...] = ()
    usable_match_ids: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()


class TrainingExample(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    source_match_id: str
    match_date: str
    sequence: int
    label: int
    split: str | None = None
    features: FeatureVector


class TrainingDataset(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: str = FEATURE_SCHEMA_VERSION
    examples: tuple[TrainingExample, ...] = ()
    audit: DatasetAudit
    train_match_ids: tuple[str, ...] = ()
    validation_match_ids: tuple[str, ...] = ()
    test_match_ids: tuple[str, ...] = ()
    evaluation_is_meaningful: bool = False
    evaluation_limitation: str | None = None

    def examples_for(self, split: str) -> tuple[TrainingExample, ...]:
        return tuple(example for example in self.examples if example.split == split)

    def to_frame(self, split: str | None = None) -> pd.DataFrame:
        rows = []
        selected = self.examples if split is None else self.examples_for(split)
        for example in selected:
            row = {
                "source_match_id": example.source_match_id,
                "match_date": example.match_date,
                "sequence": example.sequence,
                "label": example.label,
                "split": example.split,
                "schema_version": example.features.schema_version,
            }
            row.update(example.features.values)
            rows.append(row)
        columns = [
            "source_match_id",
            "match_date",
            "sequence",
            "label",
            "split",
            "schema_version",
            *FEATURE_NAMES,
        ]
        return pd.DataFrame(rows, columns=columns)


def match_date(match: NormalizedMatch) -> str:
    if match.info.dates:
        return match.info.dates[0]
    return ""


def chase_win_label(match: NormalizedMatch) -> tuple[int | None, str | None]:
    """Return (label, exclusion_reason). Label is 1 if the chasing team won."""

    outcome = match.info.outcome
    if match.info.match_type not in T20_MATCH_TYPES:
        return None, "unsupported_match_type"
    if outcome.result in {"no result", "abandoned"}:
        return None, "no_result"
    if outcome.result == "tie":
        return None, "tie"
    if outcome.result == "draw":
        return None, "draw"
    if outcome.method:
        return None, f"method:{outcome.method}"
    if outcome.eliminator or outcome.bowl_out_winner:
        return None, "eliminator_or_bowl_out"
    if not outcome.winner:
        return None, "no_winner"

    chase = [
        innings
        for innings in match.innings
        if innings.innings_number == 2 and not innings.is_super_over
    ]
    if not chase:
        return None, "no_regulation_chase"
    if any(innings.is_super_over for innings in match.innings):
        return None, "super_over_present"

    chasing_team = chase[0].batting_team
    if chase[0].target is None or chase[0].target.runs is None:
        return None, "missing_chase_target"
    if outcome.winner == chasing_team:
        return 1, None
    if outcome.winner in match.info.teams:
        return 0, None
    return None, "winner_not_in_teams"


def chronological_match_split(
    matches: Sequence[tuple[str, str]],
    *,
    train_fraction: float = TRAIN_FRACTION,
    validation_fraction: float = VALIDATION_FRACTION,
) -> dict[str, tuple[str, ...]]:
    """Split unique matches by date, then id. No match appears in two splits."""

    if train_fraction <= 0 or validation_fraction < 0:
        raise DatasetError("split fractions must be non-negative and train > 0")
    if train_fraction + validation_fraction >= 1:
        raise DatasetError("train + validation must leave a test remainder")

    unique: dict[str, str] = {}
    for match_id, date in matches:
        if match_id in unique and unique[match_id] != date:
            raise DatasetError(f"match {match_id} has conflicting dates")
        unique[match_id] = date

    ordered = sorted(unique.items(), key=lambda item: (item[1], item[0]))
    ids = [match_id for match_id, _ in ordered]
    count = len(ids)
    if count == 0:
        return {"train": (), "validation": (), "test": ()}
    if count < MIN_MATCHES_FOR_THREE_WAY_SPLIT:
        return {"train": tuple(ids), "validation": (), "test": ()}

    train_end = int(count * train_fraction)
    validation_end = int(count * (train_fraction + validation_fraction))
    train_end = max(1, min(train_end, count - 2))
    validation_end = max(train_end + 1, min(validation_end, count - 1))
    return {
        "train": tuple(ids[:train_end]),
        "validation": tuple(ids[train_end:validation_end]),
        "test": tuple(ids[validation_end:]),
    }


def audit_matches(matches: Sequence[NormalizedMatch]) -> DatasetAudit:
    usable_ids: list[str] = []
    excluded_ids: list[str] = []
    notes: list[str] = []
    counts = {
        "unsupported_match_formats": 0,
        "abandoned_or_no_result": 0,
        "tied_matches": 0,
        "dls_or_method_matches": 0,
        "super_over_or_eliminator_matches": 0,
        "missing_or_invalid_binary_outcomes": 0,
        "incomplete_or_unsupported": 0,
    }
    usable_states = 0
    source_deliveries = 0
    reconstructed_states = 0
    valid_t20 = 0

    for match in matches:
        source_deliveries += len(match.deliveries)
        states = MatchStateEngine(match).reconstruct()
        reconstructed_states += len(states)
        if match.info.match_type in T20_MATCH_TYPES:
            valid_t20 += 1
        label, reason = chase_win_label(match)
        if label is None:
            excluded_ids.append(match.source_match_id)
            _tally_exclusion(counts, reason)
            notes.append(f"{match.source_match_id}:{reason}")
            continue
        usable_ids.append(match.source_match_id)
        usable_states += sum(1 for state in states if is_chase_training_state(state))

    if valid_t20 <= MIN_MATCHES_FOR_MEANINGFUL_EVAL:
        notes.append(
            f"sample has {valid_t20} T20/IT20 matches; a reliable T20 win-probability "
            f"model needs hundreds of completed matches, not a {valid_t20}-file sample"
        )

    return DatasetAudit(
        total_matches=len(matches),
        valid_t20_matches=valid_t20,
        completed_usable_matches=len(usable_ids),
        unsupported_match_formats=counts["unsupported_match_formats"],
        abandoned_or_no_result=counts["abandoned_or_no_result"],
        tied_matches=counts["tied_matches"],
        dls_or_method_matches=counts["dls_or_method_matches"],
        super_over_or_eliminator_matches=counts["super_over_or_eliminator_matches"],
        missing_or_invalid_binary_outcomes=counts["missing_or_invalid_binary_outcomes"],
        incomplete_or_unsupported=counts["incomplete_or_unsupported"],
        usable_delivery_states=usable_states,
        source_deliveries=source_deliveries,
        reconstructed_states=reconstructed_states,
        excluded_match_ids=tuple(excluded_ids),
        usable_match_ids=tuple(usable_ids),
        notes=tuple(notes),
    )


def build_training_dataset(
    matches: Sequence[NormalizedMatch],
    *,
    train_fraction: float = TRAIN_FRACTION,
    validation_fraction: float = VALIDATION_FRACTION,
) -> TrainingDataset:
    audit = audit_matches(matches)
    labeled: list[tuple[NormalizedMatch, int, list[MatchState]]] = []
    for match in matches:
        label, _reason = chase_win_label(match)
        if label is None:
            continue
        states = MatchStateEngine(match).reconstruct()
        labeled.append((match, label, states))

    split = chronological_match_split(
        [(match.source_match_id, match_date(match)) for match, _, _ in labeled],
        train_fraction=train_fraction,
        validation_fraction=validation_fraction,
    )
    split_lookup = {match_id: name for name, ids in split.items() for match_id in ids}

    examples: list[TrainingExample] = []
    for match, label, states in labeled:
        for state in states:
            if not is_chase_training_state(state):
                continue
            features = extract_feature_vector(
                state,
                states,
                match=match,
                balls_per_over=match.info.balls_per_over,
            )
            examples.append(
                TrainingExample(
                    source_match_id=match.source_match_id,
                    match_date=match_date(match),
                    sequence=state.sequence,
                    label=label,
                    split=split_lookup.get(match.source_match_id),
                    features=features,
                )
            )

    _assert_no_split_leakage(examples)
    meaningful, limitation = _evaluation_quality(split, labeled)
    return TrainingDataset(
        examples=tuple(examples),
        audit=audit,
        train_match_ids=split["train"],
        validation_match_ids=split["validation"],
        test_match_ids=split["test"],
        evaluation_is_meaningful=meaningful,
        evaluation_limitation=limitation,
    )


def load_matches_from_dir(path: str | Path) -> list[NormalizedMatch]:
    directory = Path(path)
    files = sorted(directory.glob("*.json"))
    if not files:
        raise DatasetError(f"no Cricsheet JSON files in {directory}")
    return [parse_cricsheet_file(file) for file in files]


def write_dataset(dataset: TrainingDataset, output_dir: str | Path) -> dict[str, Path]:
    directory = Path(output_dir)
    directory.mkdir(parents=True, exist_ok=True)
    frame_path = directory / "training_examples.csv"
    split_path = directory / "split.json"
    audit_path = directory / "audit.json"
    dataset.to_frame().to_csv(frame_path, index=False)
    split_path.write_text(
        TrainingDataset.model_validate(
            {
                **dataset.model_dump(exclude={"examples", "audit"}),
                "examples": [],
                "audit": dataset.audit.model_dump(),
            }
        ).model_dump_json(indent=2),
        encoding="utf-8",
    )
    audit_path.write_text(dataset.audit.model_dump_json(indent=2), encoding="utf-8")
    return {"examples": frame_path, "split": split_path, "audit": audit_path}


def exclusion_category(reason: str | None) -> str:
    """Map a label-exclusion reason to one mutually exclusive audit bucket."""

    if reason == "unsupported_match_type":
        return "unsupported_match_formats"
    if reason in {"no_result", "abandoned"}:
        return "abandoned_or_no_result"
    if reason == "tie":
        return "tied_matches"
    if reason and reason.startswith("method:"):
        return "dls_or_method_matches"
    if reason in {"eliminator_or_bowl_out", "super_over_present"}:
        return "super_over_or_eliminator_matches"
    if reason in {"no_winner", "winner_not_in_teams", "missing_chase_target", "draw"}:
        return "missing_or_invalid_binary_outcomes"
    return "incomplete_or_unsupported"


def _tally_exclusion(counts: dict[str, int], reason: str | None) -> None:
    counts[exclusion_category(reason)] += 1


def _assert_no_split_leakage(examples: Sequence[TrainingExample]) -> None:
    seen: dict[str, str] = {}
    for example in examples:
        if example.split is None:
            raise DatasetError(f"{example.source_match_id} has no split assignment")
        previous = seen.get(example.source_match_id)
        if previous is None:
            seen[example.source_match_id] = example.split
        elif previous != example.split:
            raise DatasetError(
                f"{example.source_match_id} leaked across {previous} and {example.split}"
            )


def _evaluation_quality(
    split: dict[str, tuple[str, ...]],
    labeled: Sequence[tuple[NormalizedMatch, int, list[MatchState]]],
) -> tuple[bool, str | None]:
    n_usable = len(labeled)
    n_test = len(split["test"])
    if (
        n_usable < MIN_MATCHES_FOR_MEANINGFUL_EVAL
        or n_test < MIN_TEST_MATCHES_FOR_MEANINGFUL_EVAL
    ):
        return (
            False,
            (
                f"Only {n_usable} usable matches and {n_test} test matches. "
                "A chronological 70/15/15 report is implemented, but metrics from "
                "this sample are pipeline-verification numbers, not a production "
                "evaluation. Acquire a larger official Cricsheet T20 corpus first."
            ),
        )
    return True, None


def iter_json_paths(paths: Iterable[str | Path]) -> list[Path]:
    return [Path(path) for path in paths]
