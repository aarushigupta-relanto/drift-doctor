"""Load production samples from the project dataset for predictive monitoring."""

from __future__ import annotations

import os
from typing import Optional

import pandas as pd


def get_dataset_path() -> str:
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(root, "final_dataset.csv")


def load_production_sample(
    n: int = 200,
    *,
    dataset_path: Optional[str] = None,
    drift_tag: str = "clean_web",
) -> pd.DataFrame:
    """
    Load a sample of production rows for drift monitoring.

    Uses rows tagged ``clean_web`` by default (production traffic in this project).
    """
    path = dataset_path or get_dataset_path()
    if not os.path.isfile(path):
        raise FileNotFoundError(
            f"Dataset not found at {path}. Place final_dataset.csv in the project root."
        )

    df = pd.read_csv(path)
    prod = df[df["drift_tag"] == drift_tag].dropna(subset=["user_query", "intent"])
    if prod.empty:
        raise ValueError(
            f"No rows with drift_tag='{drift_tag}' in {path}. "
            "Check the dataset or pass custom records to /api/monitor/run."
        )

    sample_size = min(n, len(prod))
    return prod.sample(n=sample_size, random_state=42).reset_index(drop=True)
