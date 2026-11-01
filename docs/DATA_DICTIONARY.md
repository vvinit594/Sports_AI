# PulseIQ Data Dictionary — Phase 1

## Provenance

| Field | Type | Source | Notes |
| --- | --- | --- | --- |
| `source` | string | constant | Always `cricsheet` |
| `source_match_id` | string | filename stem | Cricsheet match id, e.g. `1082591` |
| `data_version` | string | `meta.data_version` | Inspected sample is `1.2.0` |
| `created` | string | `meta.created` | `YYYY-MM-DD` |
| `revision` | int | `meta.revision` | File revision |
| `source_path` | string? | local | Present only when parsed from disk |

## Match info

| Field | Type | Source | Notes |
| --- | --- | --- | --- |
| `balls_per_over` | int | `info.balls_per_over` | Defaults to 6 only if missing |
| `match_type` | string | `info.match_type` | `T20`, `IT20`, or competition code such as IPL/WTC |
| `team_type` | string? | `info.team_type` | `club` or `international` |
| `gender` | string | `info.gender` | Copied as provided |
| `scheduled_overs` | int? | `info.overs` | Usually 20 for T20 |
| `season` | string | `info.season` | Coerced to string; source may be int |
| `dates` | string[] | `info.dates` | |
| `teams` | string[] | `info.teams` | |
| `venue`, `city` | string? | `info` | |
| `event` | object? | `info.event` | `group` coerced to string |
| `toss` | object | `info.toss` | |
| `outcome` | object | `info.outcome` | Winner, result, method, margins |
| `players` | map | `info.players` | Official listed players |
| `registry_people` | map | `info.registry.people` | Stable 8-char ids |
| `player_of_match` | string[] | `info.player_of_match` | |

`info.supersubs` is documented as required by Cricsheet but is absent from the
inspected T20 sample. It is treated as optional.

## Delivery

| Field | Type | Source / rule |
| --- | --- | --- |
| `sequence` | int | Derived: 1..N across the match |
| `innings_number` | int | Derived: innings order including super overs |
| `over_number` | int | `over.over` (0-based in Cricsheet) |
| `delivery_in_over` | int | Derived: 1-based index in that over, including extras |
| `actual_delivery` | string? | `delivery.actual_delivery`; not invented if missing |
| `batter`, `bowler`, `non_striker` | string | Source |
| `batter_runs` | int | `runs.batter`, fallback `runs.batsman` |
| `extras_runs` | int | `runs.extras` |
| `total_runs` | int | `runs.total` |
| `extras.*` | int | Named extras only; missing keys are 0 |
| `is_legal_delivery` | bool | False if wide or no-ball |
| `non_boundary` | bool | `runs.non_boundary` |
| `wickets` | list | Source wickets plus `counts_as_wicket` |

Cricsheet does not store a separate official innings total. The source total is
the sum of delivery `runs.total` plus innings `penalty_runs.pre/post`.

## Match state

State `sequence` 0 is the empty snapshot before the first ball. Later states
are the situation immediately after that many deliveries.

| Field | Meaning |
| --- | --- |
| `innings_runs` | Current innings total, including applied penalty runs |
| `innings_wickets` | Counting dismissals only |
| `innings_wicket_events` | All wicket records, including retired hurt |
| `legal_balls` | Deliveries that are not wides or no-balls |
| `total_deliveries` | Every recorded delivery in the innings |
| `overs` | Cricket notation from legal balls, e.g. `12.3` |
| `current_run_rate` | `(runs / legal_balls) * balls_per_over`, else null |
| `target` | Chase target if known |
| `target_source` | `cricsheet`, `derived_previous_innings`, or `none` |
| `runs_remaining` | `target - innings_runs`; may be negative after overshooting |
| `balls_remaining` | `max(0, scheduled_balls - legal_balls)` |
| `required_run_rate` | `(runs_remaining / balls_remaining) * balls_per_over` |
| `wickets_remaining` | `10 - absent_hurt_count - innings_wickets` |
| `is_super_over` | From source `super_over` |
| `outcome` | Copied from source; never inferred by the engine |

## Assumptions

1. Wides and no-balls are the only illegal extras.
2. `retired hurt` / `retired not out` do not count toward all-out.
3. `retired out` does count toward all-out.
4. Standard all-out is 10 wickets, reduced by `absent_hurt`. Squad size is not
   used because player lists can include substitutes.
5. Target overs use cricket notation: `35.1` means 35 overs + 1 ball.
6. Super-over scheduled length is one over unless the source supplies target overs.
7. Super-over chase target is derived only when Cricsheet omits `target` and a
   previous super-over innings by the other team exists.
8. Regulation chase targets are never invented.
9. Super-over runs are isolated from regulation innings totals.
10. Missing source fields stay missing. They are not filled with estimates.

## Fields inspected in real T20 files and preserved when present

Wicket kinds: `caught`, `bowled`, `run out`, `lbw`, `stumped`,
`caught and bowled`, `retired hurt`, `hit wicket`, `retired out`,
`obstructing the field`, `handled the ball`.

Extras: `wides`, `legbyes`, `noballs`, `byes`, `penalty`.

Outcomes: winner by runs/wickets, `tie` with `eliminator`, `no result`, `D/L`.

Other: reviews, replacements, miscounted overs, absent hurt, non-boundary
fours/sixes, multi-super-over matches (up to 6 innings in the sample).
