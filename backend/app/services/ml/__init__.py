"""Phase 2 machine-learning pipeline for chase win probability."""

from app.services.ml.dataset_builder import (
    DatasetAudit,
    TrainingDataset,
    audit_matches,
    build_training_dataset,
    chronological_match_split,
)
from app.services.ml.evaluate import (
    MATCH_LEVEL_AGGREGATION,
    EvaluationReport,
    MatchLevelEvaluation,
    evaluate_binary_probabilities,
)
from app.services.ml.features import (
    FEATURE_NAMES,
    FEATURE_SCHEMA_VERSION,
    FeatureVector,
    extract_feature_vector,
    is_active_feature_state,
    is_chase_training_state,
)
from app.services.ml.inference import (
    InferenceResult,
    ProbabilityPrediction,
    predict_batch,
    predict_one,
)
from app.services.ml.model_registry import ModelArtifact, load_model, save_model
from app.services.ml.train import TrainedModel, fit_baseline_models

__all__ = [
    "FEATURE_NAMES",
    "FEATURE_SCHEMA_VERSION",
    "MATCH_LEVEL_AGGREGATION",
    "DatasetAudit",
    "EvaluationReport",
    "MatchLevelEvaluation",
    "FeatureVector",
    "InferenceResult",
    "ModelArtifact",
    "ProbabilityPrediction",
    "TrainedModel",
    "TrainingDataset",
    "audit_matches",
    "build_training_dataset",
    "chronological_match_split",
    "evaluate_binary_probabilities",
    "extract_feature_vector",
    "fit_baseline_models",
    "is_active_feature_state",
    "is_chase_training_state",
    "load_model",
    "predict_batch",
    "predict_one",
    "save_model",
]
