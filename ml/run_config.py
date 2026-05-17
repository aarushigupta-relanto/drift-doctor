"""
ML run settings for the predictive demo (dataset, model paths, drift tags).

Defaults to datasets/drift_doctor_demo.csv. Pass MLRunConfig into training, monitoring, and retraining.
"""

from __future__ import annotations

import os
from dataclasses import asdict, dataclass, field
from typing import Any


def project_root() -> str:
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def default_demo_dataset_path() -> str:
    return os.path.join(project_root(), "datasets", "drift_doctor_demo.csv")


def default_legacy_dataset_path() -> str:
    return os.path.join(project_root(), "final_dataset.csv")


def default_models_dir() -> str:
    return os.path.join(project_root(), "ml", "models")


@dataclass
class MLRunConfig:
    dataset_path: str
    reference_model_path: str
    reference_vectorizer_path: str
    models_dir: str = field(default_factory=default_models_dir)
    historical_tag: str = "clean"
    production_tag: str = "clean_web"
    legacy_harmonize: bool = False
    model_type: str = "random_forest"

    def resolve_paths(self) -> "MLRunConfig":
        """Make relative paths absolute from project root."""
        root = project_root()

        def _abs(p: str) -> str:
            if not p:
                return p
            return p if os.path.isabs(p) else os.path.normpath(os.path.join(root, p))

        self.dataset_path = _abs(self.dataset_path)
        self.reference_model_path = _abs(self.reference_model_path)
        self.reference_vectorizer_path = _abs(self.reference_vectorizer_path)
        self.models_dir = _abs(self.models_dir)
        return self

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_payload(cls, payload: dict[str, Any] | None) -> "MLRunConfig":
        payload = payload or {}
        root = project_root()
        models_dir = payload.get("models_dir") or default_models_dir()

        dataset = payload.get("dataset_path") or payload.get("dataset")
        if not dataset:
            dataset = default_demo_dataset_path()

        ref_model = payload.get("reference_model_path") or payload.get("reference_model")
        if not ref_model:
            ref_model = os.path.join(models_dir, "reference_model.pkl")

        ref_vec = payload.get("reference_vectorizer_path") or payload.get("reference_vectorizer")
        if not ref_vec:
            ref_vec = os.path.join(models_dir, "tfidf_vectorizer.pkl")

        legacy = bool(payload.get("legacy_harmonize", False))
        if not legacy and "final_dataset" in os.path.basename(str(dataset)):
            legacy = True

        cfg = cls(
            dataset_path=str(dataset),
            reference_model_path=str(ref_model),
            reference_vectorizer_path=str(ref_vec),
            models_dir=str(models_dir),
            historical_tag=str(payload.get("historical_tag", "clean")),
            production_tag=str(payload.get("production_tag", "clean_web")),
            legacy_harmonize=legacy,
            model_type=str(payload.get("model_type", "random_forest")),
        )
        return cfg.resolve_paths()

    @classmethod
    def default(cls) -> "MLRunConfig":
        return cls.from_payload({})
