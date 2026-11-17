"""Deterministic classifier for cricket questions grounded in match evidence.

This module does not call an LLM. It prefers explicit, conservative patterns
over broad keyword matching. Interpretive, statistical, and conceptual
questions are left for the Gemini path.
"""

from __future__ import annotations

import re
from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class QuestionCategory(StrEnum):
    SCORE_AND_MATCH_STATE = "score_and_match_state"
    RUN_RATE = "run_rate"
    DELIVERY_ANALYSIS = "delivery_analysis"
    RECENT_PERFORMANCE = "recent_performance"
    SIGNIFICANT_MOMENTS = "significant_moments"
    TERMINAL_STATE = "terminal_state"
    UNSUPPORTED = "unsupported"


class ClassificationResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    category: QuestionCategory
    supported: bool
    certainty: str
    reason: str | None = None
    normalized_question: str


_WHITESPACE_RE = re.compile(r"\s+")
_PUNCT_RE = re.compile(r"[?!.,:;\"'`]+")

_INTERPRETIVE_RE = re.compile(
    r"\b(why|tactical|tactics|strategy|pressure|momentum|analys[ee]|analyz[ee]|"
    r"predict|forecast|should|advise|best shot|important)\b"
)
_UNSUPPORTED_STATS_RE = re.compile(
    r"\b(economy|strike rate|batting average|bowling average|partnership|"
    r"career stats?|fantasy|dream11|points|man of the match)\b"
)
_CONCEPT_RE = re.compile(
    r"^(what is a |what are |explain (a |the )?(powerplay|drs|super over|"
    r"required run rate|current run rate|wicket|no-?ball|wide)\b)"
)

_TERMINAL_RE = re.compile(
    r"\b(who won|winner|final score|match result|result of (the |this )?match|"
    r"did .+ win)\b"
)
_MOMENTS_RE = re.compile(
    r"\b(significant moments?|turning points?|win[- ]?probability changes?|"
    r"largest (win[- ]?probability|probability|wp) (change|swing)s?)\b"
)
_DELIVERY_RE = re.compile(
    r"\b(last (ball|delivery)|what happened on the last|"
    r"who (was )?(the )?(batter|bowler|striker)|who bowled|"
    r"who (was )?batting on the last|"
    r"(how many|what) runs (came )?(from|on|off) (the )?(last )?(ball|delivery)|"
    r"was it a (wicket|wide|no-?ball)|"
    r"(wide|no-?ball) (on )?(the )?(last )?(ball|delivery))\b"
)
_RECENT_RE = re.compile(
    r"\b(last (few|six|6) (balls|deliveries)|recent (balls|deliveries|overs)|"
    r"last over|runs in the last (few|six|6)|wickets in the last (few|six|6))\b"
)
_RUN_RATE_RE = re.compile(
    r"\b((the )?(current run rate|crr)|(the )?(required run rate|rrr)|"
    r"runs remaining|balls remaining|how many runs (are )?left|"
    r"how many balls (are )?(left|remaining))\b"
)
_SCORE_RE = re.compile(
    r"\b((the )?current score|(?<!final )score|how many wickets|"
    r"wickets (have )?(fallen|down)|"
    r"which innings|what innings|batting team|bowling team|who is batting|"
    r"who is bowling|what is the target|the target|"
    r"has the match (finished|ended|completed)|is the match (over|finished|complete)|"
    r"how many overs|what overs)\b"
)


def normalize_question(text: str) -> str:
    cleaned = _PUNCT_RE.sub(" ", text.lower())
    return _WHITESPACE_RE.sub(" ", cleaned).strip()


def classify_question(question: str | None) -> ClassificationResult:
    if question is None:
        return ClassificationResult(
            category=QuestionCategory.UNSUPPORTED,
            supported=False,
            certainty="none",
            reason="no_question",
            normalized_question="",
        )
    normalized = normalize_question(question)
    if not normalized:
        return ClassificationResult(
            category=QuestionCategory.UNSUPPORTED,
            supported=False,
            certainty="none",
            reason="empty_question",
            normalized_question="",
        )
    if _UNSUPPORTED_STATS_RE.search(normalized):
        return ClassificationResult(
            category=QuestionCategory.UNSUPPORTED,
            supported=False,
            certainty="high",
            reason="unsupported_statistics",
            normalized_question=normalized,
        )
    if _CONCEPT_RE.search(normalized):
        return ClassificationResult(
            category=QuestionCategory.UNSUPPORTED,
            supported=False,
            certainty="high",
            reason="conceptual_question",
            normalized_question=normalized,
        )
    if _INTERPRETIVE_RE.search(normalized):
        return ClassificationResult(
            category=QuestionCategory.UNSUPPORTED,
            supported=False,
            certainty="high",
            reason="interpretive_question",
            normalized_question=normalized,
        )

    matches: list[QuestionCategory] = []
    for category, pattern in (
        (QuestionCategory.TERMINAL_STATE, _TERMINAL_RE),
        (QuestionCategory.SIGNIFICANT_MOMENTS, _MOMENTS_RE),
        (QuestionCategory.DELIVERY_ANALYSIS, _DELIVERY_RE),
        (QuestionCategory.RECENT_PERFORMANCE, _RECENT_RE),
        (QuestionCategory.RUN_RATE, _RUN_RATE_RE),
        (QuestionCategory.SCORE_AND_MATCH_STATE, _SCORE_RE),
    ):
        if pattern.search(normalized):
            matches.append(category)

    if len(matches) == 1:
        return ClassificationResult(
            category=matches[0],
            supported=True,
            certainty="high",
            reason=None,
            normalized_question=normalized,
        )
    if len(matches) > 1:
        return ClassificationResult(
            category=QuestionCategory.UNSUPPORTED,
            supported=False,
            certainty="none",
            reason="ambiguous_question",
            normalized_question=normalized,
        )
    return ClassificationResult(
        category=QuestionCategory.UNSUPPORTED,
        supported=False,
        certainty="none",
        reason="no_explicit_category",
        normalized_question=normalized,
    )
