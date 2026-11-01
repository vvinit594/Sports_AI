import pytest

from app.core.exceptions import ReplayError
from app.services.ingestion import parse_cricsheet_dict
from app.services.replay import ReplayEngine
from tests.helpers import cricsheet_match, delivery, innings, over


def _replay() -> ReplayEngine:
    raw = cricsheet_match(
        [
            innings(
                "Alpha",
                [
                    over(
                        0,
                        [
                            delivery(actual_delivery="0.1", batter_runs=1),
                            delivery(actual_delivery="0.2", batter_runs=4),
                            delivery(actual_delivery="0.3", batter_runs=0),
                        ],
                    )
                ],
            )
        ]
    )
    match = parse_cricsheet_dict(raw, source_match_id="replay")
    return ReplayEngine(match)


def test_replay_is_deterministic():
    first = _replay().play_all()
    second = _replay().play_all()
    assert [state.model_dump() for state in first] == [
        state.model_dump() for state in second
    ]
    assert first[-1].innings_runs == 5
    assert first[-1].legal_balls == 3


def test_next_seek_and_restart():
    replay = _replay()
    assert replay.current.sequence == 0
    assert replay.current.innings_runs == 0
    first = replay.next()
    assert first.sequence == 1
    assert first.innings_runs == 1
    jumped = replay.seek(3)
    assert jumped.sequence == 3
    assert jumped.innings_runs == 5
    assert jumped.match_complete is True
    restarted = replay.restart()
    assert restarted.sequence == 0
    assert restarted.innings_runs == 0


def test_next_at_end_raises():
    replay = _replay()
    replay.play_all()
    with pytest.raises(ReplayError):
        replay.next()
