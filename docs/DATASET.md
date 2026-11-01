# PulseIQ Dataset — Phase 2

This document describes the official sample currently in the repository, the
chase-win training label, the match-level split, and how to add more Cricsheet
T20 data. It does not claim that 15 matches are enough to train a production
win-probability model.

## Current sample

`data/raw/cricsheet/samples` holds 15 official Cricsheet JSON files. They were
chosen in Phase 1 to exercise edge cases, not to represent T20 cricket.

| Count | Meaning |
| --- | --- |
| 15 | Total available matches |
| 14 T20 + 1 IT20 | Valid T20-family matches |
| 11 | Completed matches with a usable binary chase outcome |
| 2 | Ties decided by super over / eliminator |
| 1 | Duckworth-Lewis shortened chase |
| 1 | No result (one innings only) |
| 1,268 | Usable active second-innings chase states |
| 3,454 | Source deliveries across all 15 files |
| 3,469 | Reconstructed Phase 1 states |

Usable match ids: `335987`, `335988`, `1082591`, `1082592`, `1082628`,
`1146789`, `1175358`, `1175366`, `1304066`, `1314906`, `1434162`.

Excluded: `1082625` (tie), `1082648` (D/L), `1216517` (tie, two super-over
pairs), `1359519` (no result).

Date range of usable matches: 2008-04-21 to 2024-05-26.

## What is missing or inconsistent

- The sample is a curated edge-case set, not a random T20 population.
- Men's IPL, women's T20, and one unofficial men's international are mixed.
- Super-over and D/L matches are present but excluded from labels.
- Phase 1 `DeliveryApplied` does not carry `non_boundary`; boundary features
  consult the source match when it is supplied.
- No player-level form, venue, toss decision, or live weather features exist.
- 11 labeled matches cannot support a reliable 70/15/15 evaluation.

## Label

For a regulation second innings with a Cricsheet target:

- `1` = the chasing team is `info.outcome.winner`
- `0` = the other team won

A match is unlabeled, and contributes zero training rows, when any of these
are true:

- `result` is `no result`, `abandoned`, `tie`, or `draw`
- `method` is present (D/L and other revised-target methods)
- an eliminator or bowl-out decided the match
- a super over is present
- there is no regulation second innings or no target
- the winner is missing or not one of the two teams

Every delivery row from a labeled match shares that one match-level label.
Do not treat delivery rows as independent observations.

## Split

Matches are sorted by first date, then match id.

- earliest 70% → train
- next 15% → validation
- latest 15% → test

No delivery from one match appears in two splits. If fewer than three labeled
matches exist, all rows stay in train and evaluation is skipped.

On the current 11 labeled matches the split is chronological and implemented,
but it is **not a meaningful evaluation**: only two matches land in test, and
every delivery in a match has the same label.

A held-out report is treated as meaningful only when there are at least 50
usable matches and 8 test matches. Those thresholds are conservative and still
far below a production cricket model.

## Additional historical T20 data required

Do not invent extra rows. Download official Cricsheet archives yourself and
keep them out of git.

Suggested official sources (Open Data Commons Attribution License):

- https://cricsheet.org/downloads/t20s_json.zip
- https://cricsheet.org/downloads/it20s_json.zip
- https://cricsheet.org/downloads/ipl_json.zip
- https://cricsheet.org/downloads/t20s_female_json.zip
- https://cricsheet.org/downloads/wpl_json.zip
- other T20 competition zips listed at https://cricsheet.org/downloads/

A first serious baseline needs hundreds of completed T20 matches with binary
outcomes. Stable calibration usually needs thousands.

### Reproducible acquisition

1. Create `data/raw/cricsheet/full/` locally. It is not required in git.
2. Download the official zip files from Cricsheet. Do not scrape other sites.
3. Extract only `*.json` match files into `data/raw/cricsheet/full/`.
4. Keep the Cricsheet license with the files.
5. Audit, then build the dataset:

```powershell
python backend\scripts\audit_dataset.py --input data\raw\cricsheet\full
python backend\scripts\build_training_dataset.py --input data\raw\cricsheet\full --output data\processed\ml
python backend\scripts\train_win_probability.py --input data\raw\cricsheet\full
```

PulseIQ does not download these archives automatically.
