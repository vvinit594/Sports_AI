# PulseIQ

The Adaptive Intelligence Layer for Live Sports.

Phase 1 implements the cricket data foundation and historical match replay
engine. Phase 2 adds chase-win features, baseline models, inference, and
moment detection. Generative AI, APIs, and the web application are not part
of these phases. The 15 official sample matches are not enough for a
production-quality model.

## What Phase 1 does

- Parses official Cricsheet T20 JSON.
- Reconstructs ball-by-ball match state: score, wickets, legal balls, overs,
  current run rate, target, runs remaining, and required run rate.
- Handles extras, wickets on wides/no-balls, innings transitions, D/L targets,
  no-results, and super overs.
- Validates reconstructed totals against the original source records.
- Replays a historical match deterministically.

## Requirements

- Python 3.12+
- A virtual environment
- No PostgreSQL, Redis, or LLM keys

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend\requirements.txt
```

## Tests

From the repository root after activating the virtual environment:

```powershell
cd backend
python -m pytest
```

## Ingest sample matches

```powershell
python backend\scripts\ingest_cricsheet.py --input data\raw\cricsheet\samples --output data\processed
```

## Replay one match

```powershell
python backend\scripts\replay_match.py data\raw\cricsheet\samples\1082591.json
```

## Phase 2 pipeline

```powershell
python backend\scripts\audit_dataset.py
python backend\scripts\build_training_dataset.py
python backend\scripts\train_win_probability.py
```

See `docs/DATASET.md`, `docs/FEATURES.md`, and `docs/MODEL_CARD.md`.

## Sample data

`data/raw/cricsheet/samples` contains a small official Cricsheet T20 set used
for inspection and tests. Full competition archives are not stored here.
Download additional files from https://cricsheet.org/downloads/ when needed.

Cricsheet data is licensed under the Open Data Commons Attribution License.
See `data/raw/cricsheet/LICENSE.txt`.

## Project layout

```
backend/app/core                 Cricket rules
backend/app/schemas              Normalized models
backend/app/services/ingestion   Cricsheet parser
backend/app/services/match_engine
backend/app/services/replay
backend/app/services/ml
backend/app/services/intelligence
backend/models
backend/tests
data/raw/cricsheet/samples
docs/
```

## Next phase

Phase 3 (APIs, GenAI explanations, personalization, agents, frontend) has
not been started.
