# PulseIQ Feature Definitions — Phase 2

Schema version: `chase_wp_v1`.

All features are derived from a Phase 1 `MatchState` plus earlier states in
the same innings. Nothing after the current `sequence` is used.

## Active prediction states

A state is eligible for feature extraction when all of these hold:

- `is_active_prediction_state` is true
- the innings and match are not complete
- the delivery is not `source_delivery_after_terminal`
- post-innings penalty has not been applied
- `knowledge_horizon` is not `after_innings`
- `innings_number` is present

Chase-win training and inference additionally require:

- regulation innings 2
- not a super over
- a known target

Terminal states are reconstructed by Phase 1 and are kept out of training.

## Feature list

| Name | Definition | Missing handling |
| --- | --- | --- |
| `innings_number` | Current innings number | `0` if absent |
| `is_chase` | `1` if innings 2, not super over, target known | never missing |
| `is_first_innings` | `1` if regulation innings 1 | never missing |
| `current_score` | `innings_runs_at_delivery` | always present |
| `wickets_lost` | Counting dismissals | always present |
| `wickets_remaining` | Phase 1 remaining wickets | `0` + `missing_wickets_remaining` |
| `legal_balls` | Legal balls so far | always present |
| `balls_remaining` | Scheduled legal balls left | `0` + `missing_balls_remaining` |
| `scheduled_balls` | Scheduled legal balls | `0` + `missing_scheduled_balls` |
| `overs_remaining` | `balls_remaining / balls_per_over` | follows balls remaining |
| `target` | Chase target | `0` + `missing_target` |
| `runs_remaining` | `target - score` when known | `0` when unknown |
| `current_run_rate` | Phase 1 CRR | `0` + flag when no legal ball |
| `required_run_rate` | Phase 1 RRR | `0` + flag when not a chase |
| `target_pressure` | `RRR / max(CRR, 1)` | `0` when RRR unknown |
| `resources_remaining` | `(balls left / scheduled) * (wickets left / 10)` | available parts only |
| `runs_last_6` | Sum of `total_runs` on the previous 6 same-innings deliveries | `0` if none |
| `runs_last_12` | Same window of 12 | `0` if none |
| `wickets_last_6` | Counting wickets in the last 6 deliveries | `0` if none |
| `wickets_last_12` | Same window of 12 | `0` if none |
| `boundaries_last_6` | Source 4s and 6s in the last 6 deliveries (`non_boundary` is false) | `0` if none |
| `boundaries_last_12` | Same window of 12 | `0` if none |
| `missing_*` | Explicit 0/1 flags for nullable fields | never missing |

Team names are not encoded. On 11 matches they would overfit identity, not
situation.

## Assumptions

- Score uses `innings_runs_at_delivery`, so post-innings penalties cannot
  leak into a live ball.
- Recent windows use the current delivery plus earlier `at_delivery` states
  in the same innings. The current ball is known at the prediction timestamp.
- History rows with `sequence > current.sequence` are ignored.
- A 4 or 6 batter-runs event is a boundary only when
  `DeliveryApplied.non_boundary` is false. That flag is copied from Cricsheet
  during Phase 1 replay. All-run fours/sixes marked `non_boundary` are not
  counted. The flag is not inferred when the source omitted it.
- Pre-innings chase snapshots (0/0, target known) are valid prediction
  states. Their recent windows are zero.
- First-innings states can be featurized but are not chase-win training rows.

## Leakage rules

- Match outcome is never a feature.
- Future deliveries are never a feature.
- After-innings and post-penalty snapshots are not training rows.
- The ball that completes the chase is not an active prediction state.
