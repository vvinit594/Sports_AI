# PulseIQ Product Requirements — Phase 1

## Status

Phase 1 only: data foundation and historical match replay engine.

This document does not claim that Machine Learning, Generative AI,
personalization, APIs, or the frontend exist. Those are later phases.

## Problem

Live cricket produces a dense stream of deliveries, extras, wickets, and
scoreboard changes. Before PulseIQ can rank moments or explain them, it must
reconstruct the match situation after every ball from historical source data.

## Phase 1 goal

Build a reliable cricket data-processing foundation that can:

1. Parse official Cricsheet T20 JSON.
2. Normalize match metadata, innings, and deliveries.
3. Reconstruct score, wickets, legal balls, overs, run rates, target, and
   remaining runs after every delivery.
4. Replay a historical match deterministically.
5. Validate reconstructed totals against the original source records.

## In scope

- Men's and women's T20 club and unofficial international matches from Cricsheet.
- Legal vs illegal delivery classification.
- Wides, no-balls, byes, leg-byes, and penalty extras.
- Wickets that do and do not count toward all-out.
- Innings transitions, one-innings matches, ties, no-results, D/L targets.
- Super overs treated as a separate phase.
- Miscounted overs, absent hurt, retired hurt, and retired out as they appear
  in the source.

## Out of scope for Phase 1

- Win-probability models and moment detection.
- LLM explanations and agent orchestration.
- Fan profiles and personalization.
- FastAPI, PostgreSQL, Redis, and the Next.js application.
- Live cricket APIs.
- Deployment.

## Success criteria

- Parser handles representative real Cricsheet T20 files without inventing fields.
- Reconstructed innings totals match source delivery sums.
- The same match replayed twice produces identical states.
- Unit and real-match tests pass.
