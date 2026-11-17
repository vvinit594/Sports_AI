"""Deterministic classifier for cricket questions grounded in match evidence.

Phase 3 improves natural-language recognition and confidence semantics.
This module does not call an LLM. Only HIGH-confidence, single-category
factual questions are eligible for the deterministic answer engine.
MEDIUM and LOW confidence requests are left for the Gemini path.
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


class ConfidenceLevel(StrEnum):
    """Rule-based certainty. Not a calibrated probability."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ClassificationResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    category: QuestionCategory
    supported: bool
    certainty: ConfidenceLevel
    reason: str | None = None
    normalized_question: str
    matched_categories: tuple[QuestionCategory, ...] = ()
    ambiguous: bool = False

    @property
    def use_deterministic(self) -> bool:
        """Only HIGH-confidence supported factual categories bypass Gemini."""

        return (
            self.supported
            and self.certainty is ConfidenceLevel.HIGH
            and self.category is not QuestionCategory.UNSUPPORTED
            and not self.ambiguous
        )


_WHITESPACE_RE = re.compile(r"\s+")
_PUNCT_RE = re.compile(r"[?!.,:;\"'`]+")

_CONTRACTIONS = (
    (re.compile(r"\bwhat's\b"), "what is"),
    (re.compile(r"\bwhos\b"), "who is"),
    (re.compile(r"\bwho's\b"), "who is"),
    (re.compile(r"\bhow's\b"), "how is"),
    (re.compile(r"\bhow're\b"), "how are"),
    (re.compile(r"\bthey're\b"), "they are"),
    (re.compile(r"\bthey've\b"), "they have"),
    (re.compile(r"\bit's\b"), "it is"),
    (re.compile(r"\bdidn't\b"), "did not"),
    (re.compile(r"\bwasn't\b"), "was not"),
    (re.compile(r"\bweren't\b"), "were not"),
    (re.compile(r"\bcan't\b"), "cannot"),
    (re.compile(r"\bwon't\b"), "will not"),
)

_INTERPRETIVE_RE = re.compile(
    r"\b(why|tactical|tactics|strategy|pressure|momentum|analys[ee]|analyz[ee]|"
    r"predict|prediction|forecast|should|advice|advise|best shot|important|"
    r"under pressure|who will win|going to win)\b"
)
_UNSUPPORTED_STATS_RE = re.compile(
    r"\b(economy|strike rate|batting average|bowling average|partnership|"
    r"career stats?|fantasy( points)?|dream11( points)?|player points|"
    r"man of the match)\b"
)
_CONCEPT_RE = re.compile(
    r"^(what is a |what are |explain (a |the )?(powerplay|drs|super over|"
    r"required run rate|current run rate|wicket|no-?ball|wide)\b)"
)
_VAGUE_RE = re.compile(
    r"^(how is the chase( going)?|what is happening|whats happening|"
    r"update me|tell me about (the )?match|how is it going|"
    r"any update|match update)$"
)

_TERMINAL_RE = re.compile(
    r"\b("
    r"who won|"
    r"winner|"
    r"final score|"
    r"final result|"
    r"match result|"
    r"result of (the |this )?match|"
    r"how did (the |this )?match finish|"
    r"how did (the |this )?match end|"
    # Avoid matching "did the win probability …".
    r"did (?!the win probability)[\w ]{1,40}\bwin(?: the match)?"
    r")\b"
)
_MOMENTS_RE = re.compile(
    r"\b("
    r"significant moments?|"
    r"turning points?|"
    r"biggest turning points?|"
    r"win[- ]?probability changes?|"
    r"major (probability|wp) swings?|"
    r"largest (win[- ]?probability|probability|wp) (change|swing)s?|"
    r"when did (the )?win probability change (the )?most|"
    r"which deliveries had (major |the largest )?(probability|wp) (change|swing)s?"
    r")\b"
)
_DELIVERY_RE = re.compile(
    r"\b("
    r"last (ball|delivery)|"
    r"previous (ball|delivery)|"
    r"that (ball|delivery)|"
    r"tell me about the previous delivery|"
    r"what happened on (the )?(last|previous|that) (ball|delivery)|"
    r"who (was )?(on strike|the (batter|bowler|striker))|"
    r"who (was )?batting on the last|"
    r"who bowled( the (last|previous) (ball|delivery))?|"
    r"who delivered the last ball|"
    r"(how many|what) runs (came )?(from|on|off) (the )?(last|previous)? ?(ball|delivery)|"
    r"was (it|the previous delivery|the last (ball|delivery)) a (wicket|wide|no-?ball)|"
    r"was the previous delivery a no-?ball|"
    r"did anyone (get )?(dismissed|out) on (that|the last|the previous) (ball|delivery)|"
    r"(wide|no-?ball) (on )?(the )?(last|previous)? ?(ball|delivery)"
    r")\b"
)
_RECENT_RE = re.compile(
    r"\b("
    r"last (few|six|6) (balls|deliveries)|"
    r"previous (six|6) balls|"
    r"recent (balls|deliveries|overs)|"
    r"last over|"
    r"how did the last over go|"
    r"runs in the last (few|six|6)|"
    r"how many runs came in the recent|"
    r"wickets in the last (few|six|6)|"
    r"were there any wickets recently|"
    r"what happened in the previous six balls|"
    r"what happened in the last (few|six|6) (balls|deliveries)"
    r")\b"
)
_RUN_RATE_RE = re.compile(
    r"\b("
    r"(the )?(current run rate|crr)|"
    r"(the )?(required run rate|rrr|asking rate)|"
    r"scoring rate|"
    r"how quickly (are they|they are) scoring|"
    r"runs remaining|"
    r"runs (are )?still required|"
    r"how many (runs )?(do they|they) need|"
    r"how many runs (are )?(left|still required|remaining)|"
    r"balls remaining|"
    r"deliveries (are )?left|"
    r"how many (balls|deliveries) (are )?(left|remaining)"
    r")\b"
)
_SCORE_RE = re.compile(
    r"\b("
    r"(the )?current score|"
    r"score right now|"
    r"what('?s| is) the score|"
    r"how many runs have they scored|"
    r"how many runs (have|did) (they|the batting (side|team)) scored|"
    r"(?<!final )(?<!required )(?<!run )score|"
    r"how many wickets|"
    r"wickets (are |have )?(fallen|down)|"
    r"which (innings|side) (is batting|is being played)|"
    r"what innings|"
    r"how far into the innings|"
    r"batting team|bowling team|"
    r"which side is batting|"
    r"who is batting|who is bowling|"
    r"what target|"
    r"what target do they need|"
    r"the target|"
    r"has the match (finished|ended|completed)|"
    r"is the match (over|finished|complete)|"
    r"how many overs|what overs"
    r")\b"
)

# Weaker single-category hints. Alone these are MEDIUM and go to Gemini.
_WEAK_SCORE_RE = re.compile(r"\b(scoreboard|match state|situation)\b")
_WEAK_RUN_RATE_RE = re.compile(r"\b(chase rate|run rate)\b")
_WEAK_DELIVERY_RE = re.compile(r"\b(that ball|this ball)\b")


def normalize_question(text: str) -> str:
    # Expand contractions before stripping punctuation so "what's" stays intact.
    cleaned = text.lower().replace("\u2019", "'").replace("`", "'")
    for pattern, replacement in _CONTRACTIONS:
        cleaned = pattern.sub(replacement, cleaned)
    cleaned = _PUNCT_RE.sub(" ", cleaned)
    return _WHITESPACE_RE.sub(" ", cleaned).strip()


def classify_question(question: str | None) -> ClassificationResult:
    if question is None:
        return ClassificationResult(
            category=QuestionCategory.UNSUPPORTED,
            supported=False,
            certainty=ConfidenceLevel.LOW,
            reason="no_question",
            normalized_question="",
        )
    normalized = normalize_question(question)
    if not normalized:
        return ClassificationResult(
            category=QuestionCategory.UNSUPPORTED,
            supported=False,
            certainty=ConfidenceLevel.LOW,
            reason="empty_question",
            normalized_question="",
        )
    if _UNSUPPORTED_STATS_RE.search(normalized):
        return ClassificationResult(
            category=QuestionCategory.UNSUPPORTED,
            supported=False,
            certainty=ConfidenceLevel.LOW,
            reason="unsupported_statistics",
            normalized_question=normalized,
        )
    if _CONCEPT_RE.search(normalized):
        return ClassificationResult(
            category=QuestionCategory.UNSUPPORTED,
            supported=False,
            certainty=ConfidenceLevel.LOW,
            reason="conceptual_question",
            normalized_question=normalized,
        )
    if _INTERPRETIVE_RE.search(normalized):
        return ClassificationResult(
            category=QuestionCategory.UNSUPPORTED,
            supported=False,
            certainty=ConfidenceLevel.LOW,
            reason="interpretive_question",
            normalized_question=normalized,
        )
    if _VAGUE_RE.search(normalized):
        return ClassificationResult(
            category=QuestionCategory.UNSUPPORTED,
            supported=False,
            certainty=ConfidenceLevel.MEDIUM,
            reason="vague_question",
            normalized_question=normalized,
        )

    strong: list[QuestionCategory] = []
    for category, pattern in (
        (QuestionCategory.TERMINAL_STATE, _TERMINAL_RE),
        (QuestionCategory.SIGNIFICANT_MOMENTS, _MOMENTS_RE),
        (QuestionCategory.DELIVERY_ANALYSIS, _DELIVERY_RE),
        (QuestionCategory.RECENT_PERFORMANCE, _RECENT_RE),
        (QuestionCategory.RUN_RATE, _RUN_RATE_RE),
        (QuestionCategory.SCORE_AND_MATCH_STATE, _SCORE_RE),
    ):
        if pattern.search(normalized):
            strong.append(category)

    if len(strong) > 1:
        return ClassificationResult(
            category=QuestionCategory.UNSUPPORTED,
            supported=False,
            certainty=ConfidenceLevel.LOW,
            reason="ambiguous_question",
            normalized_question=normalized,
            matched_categories=tuple(strong),
            ambiguous=True,
        )
    if len(strong) == 1:
        return ClassificationResult(
            category=strong[0],
            supported=True,
            certainty=ConfidenceLevel.HIGH,
            reason=None,
            normalized_question=normalized,
            matched_categories=(strong[0],),
        )

    weak: list[QuestionCategory] = []
    for category, pattern in (
        (QuestionCategory.SCORE_AND_MATCH_STATE, _WEAK_SCORE_RE),
        (QuestionCategory.RUN_RATE, _WEAK_RUN_RATE_RE),
        (QuestionCategory.DELIVERY_ANALYSIS, _WEAK_DELIVERY_RE),
    ):
        if pattern.search(normalized):
            weak.append(category)
    if len(weak) == 1:
        return ClassificationResult(
            category=weak[0],
            supported=False,
            certainty=ConfidenceLevel.MEDIUM,
            reason="weak_category_match",
            normalized_question=normalized,
            matched_categories=(weak[0],),
        )
    if len(weak) > 1:
        return ClassificationResult(
            category=QuestionCategory.UNSUPPORTED,
            supported=False,
            certainty=ConfidenceLevel.LOW,
            reason="ambiguous_question",
            normalized_question=normalized,
            matched_categories=tuple(weak),
            ambiguous=True,
        )

    return ClassificationResult(
        category=QuestionCategory.UNSUPPORTED,
        supported=False,
        certainty=ConfidenceLevel.LOW,
        reason="no_explicit_category",
        normalized_question=normalized,
    )
