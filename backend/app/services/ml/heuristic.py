"""Deterministic chase-win heuristic used as a non-ML baseline.

This is not a fitted model. Coefficients are documented constants so the
formula is reproducible. It exists so inference and moment detection can
run before a corpus large enough for training is available.
"""

from __future__ import annotations

import math

from app.core.exceptions import InferenceError
from app.services.ml.features import FeatureVector

# rate_gap weight, extra wickets vs 5, extra resource vs 50%, intercept
RATE_GAP_WEIGHT = 0.12
WICKET_WEIGHT = 0.12
RESOURCE_WEIGHT = 1.2
INTERCEPT = -0.3
WICKET_CENTER = 5.0
RESOURCE_CENTER = 0.5


def heuristic_chase_win_probability(features: FeatureVector) -> float:
    values = features.values
    if values.get("is_chase", 0.0) < 0.5:
        raise InferenceError("heuristic chase probability is defined only for chase states")
    if values.get("missing_target", 0.0) >= 0.5:
        raise InferenceError("heuristic chase probability requires a known target")

    rate_gap = values["current_run_rate"] - values["required_run_rate"]
    if values.get("missing_required_run_rate", 0.0) >= 0.5:
        rate_gap = 0.0
    wickets = values["wickets_remaining"]
    resources = values["resources_remaining"]
    logit = (
        RATE_GAP_WEIGHT * rate_gap
        + WICKET_WEIGHT * (wickets - WICKET_CENTER)
        + RESOURCE_WEIGHT * (resources - RESOURCE_CENTER)
        + INTERCEPT
    )
    probability = 1.0 / (1.0 + math.exp(-logit))
    return min(1.0, max(0.0, probability))
