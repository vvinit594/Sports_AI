# PulseIQ Architecture — Phase 1 and Phase 2

## Scope

Phase 1 reconstructs cricket match state. Phase 2 adds chase-win features,
baseline models, inference, and deterministic moment detection. There is still
no HTTP server, database, cache, frontend, or generative AI.

```
Cricsheet JSON
      │
      ▼
ingestion.parser
      │
      ▼
NormalizedMatch
      │
      ├── match_engine.MatchStateEngine ──► MatchState[]
      ├── match_engine.validate_match ───► ValidationReport
      ├── replay.ReplayEngine ───────────► seek / next / restart
      │
      ▼
ml.features / ml.dataset_builder
      │
      ├── ml.train / ml.evaluate / ml.model_registry
      ├── ml.inference
      └── intelligence.moment_detector
```

## Package layout

| Path | Responsibility |
| --- | --- |
| `backend/app/core` | Cricket rules, constants, exceptions |
| `backend/app/schemas` | Normalized Pydantic models |
| `backend/app/services/ingestion` | Cricsheet parser |
| `backend/app/services/match_engine` | State reconstruction and validation |
| `backend/app/services/replay` | Deterministic historical replay |
| `backend/app/services/ml` | Features, dataset, train, evaluate, inference |
| `backend/app/services/intelligence` | Win-probability series and moment detection |
| `backend/models` | Local Joblib artifacts (gitignored binaries) |
| `backend/scripts` | Ingest, replay, audit, train, and evaluate CLIs |
| `backend/tests` | Unit, validation, real-match, and Phase 2 tests |
| `data/raw/cricsheet/samples` | Small official Cricsheet T20 sample |

Later phases can add `api`, SQLAlchemy models, GenAI, and the Next.js app
without changing the match-engine contracts. Phase 2 does not train a
production model on the 15-file sample. See `docs/MODEL_CARD.md`.

## Design decisions

### Modular monolith, not services

Parsing, reconstruction, and replay stay in one package. There is no message
bus and no microservice split.

### Source fields vs derived fields

The parser copies Cricsheet fields. The engine derives match-state metrics
that cricket requires but the file does not store on every ball:

- legal-ball count
- overs notation
- current and required run rate
- balls remaining
- wickets remaining
- runs remaining

Derived values are labeled. Super-over chase targets are the one case where
Cricsheet often omits `target`; the engine may derive `previous super-over
total + 1` and marks `target_source = derived_previous_innings`.

Regulation chase targets are taken from Cricsheet. They are not invented,
because Duckworth-Lewis matches would be wrong if we assumed `first innings + 1`.

### Legal deliveries

A delivery is illegal only when `extras.wides` or `extras.noballs` is present.
Byes, leg-byes, and penalty extras remain legal. A wicket does not imply a
legal delivery.

### Wickets

`retired hurt` and `retired not out` are stored as wicket events but do not
count toward all-out. `retired out` does count. Unknown future kinds count, so
all-out cannot be silently under-counted.

### Super overs

Super-over innings are flagged from the source `super_over` field. Their runs
are not added to regulation innings totals. Multiple super-over pairs are
supported.

### Replay determinism

`ReplayEngine` reconstructs the full state list once. `next`, `seek`, and
`restart` only move a cursor. No clock, network, or random source is used.

### Redis and PostgreSQL

Not used in Phase 1. Redis remains optional for later caching and must not
become a local-development requirement for match processing.

## Data flow for one delivery

1. Parser assigns a match-wide sequence number.
2. Engine adds `runs.total` to the innings score.
3. Engine increments legal balls only for legal deliveries.
4. Engine increments counting wickets from dismissal kind.
5. Engine recalculates overs, CRR, remaining balls/runs, and RRR.
6. After each delivery the engine checks chase-complete, all-out, and
   overs-exhausted conditions. The first innings ending does not end the match.
7. Post-innings penalty runs are applied only on the after-innings snapshot.
   `innings_runs_at_delivery` keeps the score that was known on the ball.
8. Later source deliveries after a terminal condition are preserved and flagged
   as `source_delivery_after_terminal`. They are not active prediction states.
