# PulseIQ API — Phase 3

The HTTP API exposes reconstructed historical cricket matches, chase
win-probability, significant moments, and grounded explanations.

This is not a live cricket feed. The default catalog is the official Cricsheet
T20 sample under `data/raw/cricsheet/samples`. Those files are completed
historical matches.

OpenAPI is served at `/docs`, `/redoc`, and `/openapi.json`.

## Local startup

From the repository root, with the virtual environment activated:

```powershell
pip install -r backend\requirements.txt
cd backend
python -m uvicorn app.main:create_app --factory --reload --host 127.0.0.1 --port 8000
```

Copy `.env.example` to `.env` for local overrides. Never put real API keys in
source control. `.env` is gitignored.

## Authentication

There is no authentication in Phase 3. The product requirements do not define
user accounts, and this API only serves local historical samples. Auth belongs
to a later phase if the product needs it.

## Data source

Every match payload includes `data_source: "historical_cricsheet"` and
`is_historical: true` on match summaries. A future live provider can implement
the same catalog lookup methods without changing these URL contracts.

## Endpoints

### `GET /health`

Liveness. The process is up.

```json
{"status": "ok", "service": "pulseiq", "phase": 3}
```

### `GET /api/v1/health/ready`

Readiness. Returns HTTP 200 when the historical catalog directory exists and
was scanned. Returns HTTP 503 when the configured Cricsheet directory is
missing.

`model_loaded` and `llm_configured` are informational. A missing model does
not fail readiness; win-probability and moment endpoints then return an
unavailable payload instead of invented numbers.

The response never includes environment variables or API keys.

### `GET /api/v1/matches`

Lists catalogued historical matches.

```json
{
  "data_source": "historical_cricsheet",
  "count": 1,
  "matches": [
    {
      "source_match_id": "1082591",
      "teams": ["Team A", "Team B"],
      "dates": ["2017-04-05"],
      "match_type": "T20",
      "is_historical": true
    }
  ]
}
```

### `GET /api/v1/matches/{match_id}`

Match metadata for one source match ID. HTTP 404 when the id is unknown.

### `GET /api/v1/matches/{match_id}/state`

Reconstructed match state from the Phase 1 engine.

| Query | Meaning |
| --- | --- |
| *(none)* | Latest reconstructed state |
| `sequence` | State after that delivery sequence |
| `full=true` | Also include every reconstructed state |

Unknown sequences return HTTP 404 with `code: sequence_not_found`.
Negative sequences return HTTP 422.

The API does not recompute cricket metrics. It returns `MatchState` from
`MatchStateEngine.reconstruct()`.

### `GET /api/v1/matches/{match_id}/win-probability`

Delivery-level chase win probability from the Phase 2 inference pipeline.

| Query | Meaning |
| --- | --- |
| *(none)* | Every eligible active regulation chase state |
| `sequence` | That sequence only |

Response shape:

```json
{
  "source_match_id": "1082591",
  "data_source": "historical_cricsheet",
  "available": true,
  "unavailable_reason": null,
  "predictions": [
    {
      "source_match_id": "1082591",
      "sequence": 120,
      "probability": 0.42,
      "model_id": "chase_wp_logreg",
      "feature_schema_version": "chase_wp_v1"
    }
  ],
  "model": {
    "model_id": "chase_wp_logreg",
    "model_kind": "logreg",
    "evaluation_is_meaningful": false,
    "evaluation_limitation": "..."
  }
}
```

Unavailable cases stay explicit:

- `available: false`, `unavailable_reason: "model_artifact_missing"` when no
  Joblib artifact can be loaded. Predictions are empty. Nothing is fabricated.
- `available: false`, `unavailable_reason: "unsupported_state"` when the
  requested sequence exists but is not an active regulation chase.

Probabilities are validated in `[0, 1]` by the existing inference layer.

The current training corpus has 11 usable completed matches. Predictions are
pipeline estimates, not production-accurate forecasts. See `docs/MODEL_CARD.md`.

### `GET /api/v1/matches/{match_id}/moments`

Significant moments from the Phase 2 detector. The detector is not rewritten.
It needs win-probability predictions, so a missing model returns
`model_artifact_missing` rather than an empty-moment success. A loaded model
with too few eligible chase states returns `available: true` and `moments: []`.

### `POST /api/v1/matches/{match_id}/explanations`

Generate a grounded explanation of a reconstructed state.

Request:

```json
{
  "audience_level": "beginner",
  "sequence": 120
}
```

`audience_level` is required and must be `beginner`, `casual`, or `advanced`.
Omit `sequence` to explain the latest reconstructed state.

The LLM does not calculate scores, wickets, run rates, or probabilities. Those
values come from the match engine and ML services. See
`docs/GENAI_EXPLANATIONS.md`.

## Error responses

All errors use:

```json
{
  "error": "match not found: missing-id",
  "code": "match_not_found",
  "detail": null
}
```

| HTTP | `code` | When |
| --- | --- | --- |
| 404 | `match_not_found` | Unknown match id |
| 404 | `sequence_not_found` | Unknown delivery sequence |
| 413 | `request_too_large` | Body larger than `PULSEIQ_MAX_REQUEST_BYTES` |
| 422 | `validation_error` | Invalid query or JSON body |
| 429 | `rate_limited` | LLM provider rate limit |
| 502 | `malformed_output` | LLM JSON failed schema validation |
| 502 | `invalid_credentials` | LLM provider rejected the server-side key |
| 503 | `provider_unavailable` | Selected LLM provider is not configured |
| 504 | `timeout` | LLM provider timed out |

Responses do not include stack traces, environment variables, or API keys.

## CORS

Set `PULSEIQ_CORS_ORIGINS` to an explicit comma-separated origin list. The
default is empty, so browsers are not granted cross-origin access until you
configure it.

## Model artifacts

The API loads one Joblib artifact:

1. `PULSEIQ_MODEL_PATH` if set
2. otherwise the newest `*.joblib` file in `PULSEIQ_MODEL_DIR`
   (default `backend/models/artifacts`)

Train artifacts with the Phase 2 scripts before expecting win-probability
results. Heuristic artifacts are valid registry models; the API does not
silently invent a heuristic when no file exists.
