# PulseIQ

The Adaptive Intelligence Layer for Live Sports.

Phase 1 implements the cricket data foundation and historical match replay
engine. Phase 2 adds chase-win features, baseline models, inference, and
moment detection. Phase 3 adds a FastAPI application and a provider-independent
GenAI explanation service over that existing intelligence.

The 15 official sample matches are historical files, not a live feed. Eleven
of them are usable for chase-win labels. That corpus is not enough for a
production-quality model.

## What exists today

- Parses official Cricsheet T20 JSON.
- Reconstructs ball-by-ball match state.
- Validates reconstructed totals against the original source records.
- Replays a historical match deterministically.
- Extracts leakage-safe chase-win features and trains baseline models.
- Serves match metadata, reconstructed state, win probability, significant
  moments, and grounded explanations over HTTP.

## Requirements

- Python 3.12+
- A virtual environment
- Optional: a Gemini or OpenAI-compatible API key for hosted explanations.
  The default `LLM_PROVIDER=mock` needs no key.

PostgreSQL, Redis, and authentication are not used in Phase 3.

Phase 4.1 adds a Next.js landing page and onboarding flow. It does not call
the API and does not include the match dashboard.

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend\requirements.txt
```

Copy `.env.example` to `.env` if you need local overrides. Do not commit `.env`.

## Tests

From the repository root after activating the virtual environment:

```powershell
cd backend
python -m pytest
```

Lint and format (from the repository root):

```powershell
python -m ruff check backend
python -m ruff format --check backend
```

Automated tests do not call a hosted LLM. They use the mock provider and
httpx transports.

## Run the API

```powershell
cd backend
python -m uvicorn app.main:create_app --factory --reload --host 127.0.0.1 --port 8000
```

OpenAPI: `http://127.0.0.1:8000/docs`

## Run the frontend (Phase 4.1)

```powershell
cd frontend
npm install
npm run dev
```

Open `http://localhost:3000`. Use **Let's play** to start onboarding.

See `docs/API.md` and `docs/GENAI_EXPLANATIONS.md`.

Win-probability routes require a Joblib artifact in
`backend/models/artifacts` (or `PULSEIQ_MODEL_PATH`). Train one with the
Phase 2 scripts. If no artifact is present, those routes return
`available: false` instead of invented probabilities.

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
for inspection, tests, and the Phase 3 catalog. Full competition archives are
not stored here. Download additional files from https://cricsheet.org/downloads/
when needed.

Cricsheet data is licensed under the Open Data Commons Attribution License.
See `data/raw/cricsheet/LICENSE.txt`.

## Project layout

```
backend/app/api                  FastAPI routes and error handlers
backend/app/core                 Cricket rules, settings, logging
backend/app/schemas              Normalized and API models
backend/app/services/ingestion   Cricsheet parser
backend/app/services/match_engine
backend/app/services/replay
backend/app/services/ml
backend/app/services/intelligence
backend/app/services/api         Match catalog and intelligence wrappers
backend/app/services/explanations
backend/models
backend/tests
frontend/                         Landing page and onboarding
data/raw/cricsheet/samples
docs/
```

## Next phase

Phase 4.2 (match dashboard and API integration) has not been started.
