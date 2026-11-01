import pytest

from app.core.cricket_rules import (
    balls_to_overs_notation,
    counts_as_wicket,
    current_run_rate,
    is_legal_delivery,
    max_wickets_available,
    overs_notation_to_balls,
    required_run_rate,
    scheduled_balls_for_innings,
)


def test_wides_and_noballs_are_illegal():
    assert is_legal_delivery({"wides": 1}) is False
    assert is_legal_delivery({"noballs": 1}) is False
    assert is_legal_delivery({"wides": 1, "byes": 0}) is False


def test_byes_legbyes_and_penalty_remain_legal():
    assert is_legal_delivery({"byes": 4}) is True
    assert is_legal_delivery({"legbyes": 2}) is True
    assert is_legal_delivery({"penalty": 5}) is True
    assert is_legal_delivery({}) is True
    assert is_legal_delivery(None) is True


def test_wicket_counting_rules():
    assert counts_as_wicket("bowled") is True
    assert counts_as_wicket("retired out") is True
    assert counts_as_wicket("retired hurt") is False
    assert counts_as_wicket("retired not out") is False
    assert counts_as_wicket("unknown future kind") is True


def test_overs_notation_uses_cricket_balls_not_decimals():
    assert overs_notation_to_balls(20) == 120
    assert overs_notation_to_balls(6) == 36
    assert overs_notation_to_balls(35.1) == 211
    assert overs_notation_to_balls("19.5") == 119
    assert overs_notation_to_balls("20.0") == 120
    assert overs_notation_to_balls(None) is None


def test_overs_notation_rejects_invalid_values():
    with pytest.raises(ValueError, match="ball component"):
        overs_notation_to_balls("5.6")
    with pytest.raises(ValueError, match="ball component"):
        overs_notation_to_balls(5.6)
    with pytest.raises(ValueError, match="negative"):
        overs_notation_to_balls(-1)
    with pytest.raises(ValueError, match="negative"):
        overs_notation_to_balls("-2.1")
    with pytest.raises(ValueError, match="malformed"):
        overs_notation_to_balls("1.2.3")
    with pytest.raises(ValueError, match="malformed"):
        overs_notation_to_balls("abc")
    with pytest.raises(ValueError, match="malformed"):
        overs_notation_to_balls("19.")
    with pytest.raises(ValueError, match="malformed"):
        overs_notation_to_balls(True)


def test_balls_to_overs_notation():
    assert balls_to_overs_notation(0) == "0.0"
    assert balls_to_overs_notation(1) == "0.1"
    assert balls_to_overs_notation(6) == "1.0"
    assert balls_to_overs_notation(119) == "19.5"
    assert balls_to_overs_notation(120) == "20.0"


def test_run_rate_helpers():
    assert current_run_rate(12, 6) == 12.0
    assert current_run_rate(0, 0) is None
    assert required_run_rate(12, 6) == 12.0
    assert required_run_rate(0, 6) == 0.0
    assert required_run_rate(-2, 3) == 0.0
    assert required_run_rate(4, 0) is None


def test_scheduled_balls_preference_order():
    assert (
        scheduled_balls_for_innings(
            target_overs=6,
            is_super_over=False,
            match_overs=20,
            match_type="T20",
        )
        == 36
    )
    assert (
        scheduled_balls_for_innings(
            target_overs=None,
            is_super_over=True,
            match_overs=20,
            match_type="T20",
        )
        == 6
    )
    assert (
        scheduled_balls_for_innings(
            target_overs=None,
            is_super_over=False,
            match_overs=20,
            match_type="T20",
        )
        == 120
    )


def test_absent_hurt_reduces_available_wickets():
    assert max_wickets_available(0) == 10
    assert max_wickets_available(1) == 9
    assert max_wickets_available(10) == 0
