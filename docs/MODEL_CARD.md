# PulseIQ Model Card — Chase Win Probability (Phase 2)

## Status

This is a **pipeline and baseline architecture**, not a production T20
win-probability model.

The repository sample has 15 official matches, 11 of which can be labeled.
Metrics produced from that split are real held-out numbers, but they are
**pipeline-verification metrics**. They are not evidence that the model
generalizes.

XGBoost is not included. The sample does not justify another boosting
dependency.

## Target

Predict `P(chasing team wins)` on an active regulation second-innings state.

- Label `1`: chasing team won the match
- Label `0`: chasing team lost

See `docs/DATASET.md` for exclusions (ties, no-results, D/L, super overs).

## Models

| Kind | Role |
| --- | --- |
| Deterministic heuristic | Resource / required-rate sigmoid. Not fitted. |
| Logistic regression | Simple linear baseline with `StandardScaler`. |
| Random forest | Constrained tree baseline (`max_depth=6`, `min_samples_leaf=20`). |

Shared configuration:

- Feature schema `chase_wp_v1`
- Random seed `42`
- Class weight `balanced`
- Match-level chronological 70/15/15 split
- Fitted on train matches only
- Validation is diagnostic only; it is not used for model selection
- Test data is never used during fitting

## Evaluation

Delivery-level log loss, Brier, ROC-AUC, accuracy, and ECE remain as
diagnostics. They overweight matches with more deliveries.

Match-level metrics aggregate each match once as the **mean of its delivery
probabilities**, paired with the match label. Report `n_matches`,
`n_positive_matches`, and `n_negative_matches`. These figures are not
calibrated ball-by-ball performance and are not used to select a model.

## Inference

`predict_one` / `predict_batch` in `app.services.ml.inference`.

Returns a probability in `[0, 1]` or raises `InferenceError`.

Inference is refused for:

- completed innings or matches
- terminal / inactive / post-terminal states
- first innings and super overs
- incomplete or non-finite feature vectors

Artifacts are Joblib files plus `ModelMetadata` (schema version, feature
names, match ids, hyperparameters, and an `evaluation_is_meaningful` flag).

## Moment detection

`app.services.intelligence.moment_detector` is deterministic. It does not
train a second classifier.

A moment may be emitted when:

- `|p_after - p_before|` exceeds `probability_swing_threshold` (default 0.08)
- a counting wicket falls in a high-pressure chase
- a major scoring event occurs
- required run rate shifts by at least `chase_equation_rrr_delta`

Cooldown (`cooldown_deliveries`, default 6) is the gap in delivery sequence
numbers after the last emitted moment. Inputs must belong to one match.
Conflicting duplicate predictions are rejected; identical duplicates are
deduplicated. Predictions without a matching state are rejected. Caller
order does not change results.

## Known limitations

- 11 labeled matches are not a T20 population.
- Delivery rows from one match share one label, so delivery-level AUC is
  inflated by within-match correlation. Use match-level mean probability
  when comparing matches.
- No player, venue, toss, or competition features.
- D/L and super-over matches are excluded rather than modeled.
- The heuristic coefficients are documented constants, not learned.
- Calibration from two test matches is not interpretable.

## Reproducibility

```powershell
.\.venv\Scripts\Activate.ps1
pip install -r backend\requirements.txt
cd backend
python -m pytest
cd ..
python backend\scripts\audit_dataset.py
python backend\scripts\build_training_dataset.py
python backend\scripts\train_win_probability.py
python backend\scripts\evaluate_win_probability.py --model backend\models\artifacts\chase_wp_logistic_regression_chase_wp_v1.joblib
```

Training writes Joblib files and `metrics.json` under
`backend/models/artifacts/`. Those binaries are gitignored and must be
regenerated locally.
