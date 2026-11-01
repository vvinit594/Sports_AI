"""Replay a Cricsheet match and print ball-by-ball reconstructed state."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.services.ingestion import parse_cricsheet_file
from app.services.replay import ReplayEngine


def main() -> int:
    parser = argparse.ArgumentParser(description="Replay a historical Cricsheet match")
    parser.add_argument("path", type=Path, help="Cricsheet JSON file")
    parser.add_argument(
        "--every", type=int, default=20, help="Print every N deliveries"
    )
    args = parser.parse_args()

    match = parse_cricsheet_file(args.path)
    replay = ReplayEngine(match)
    print(
        f"{match.source_match_id} {match.info.teams[0]} vs {match.info.teams[1]} "
        f"deliveries={replay.total_deliveries}"
    )
    states = replay.play_all()
    for state in states:
        if (
            state.sequence == 0
            or state.sequence % args.every == 0
            or state.innings_just_completed
        ):
            print(
                f"seq={state.sequence:4d} inn={state.innings_number} "
                f"{state.batting_team} {state.innings_runs}/{state.innings_wickets} "
                f"ov={state.overs} legal={state.legal_balls} "
                f"target={state.target} rem={state.runs_remaining} "
                f"crr={state.current_run_rate} rrr={state.required_run_rate} "
                f"complete={state.innings_just_completed}"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
