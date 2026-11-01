# PulseIQ

The Adaptive Intelligence Layer for Live Sports.

Phase 1 implements the cricket data foundation and historical match replay
engine only. Machine learning, generative AI, APIs, and the web application
are not part of this phase.

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
backend/tests
data/raw/cricsheet/samples
docs/
```

## Next phase

Phase 2 will train a win-probability model and detect significant moments.
It has not been started.
