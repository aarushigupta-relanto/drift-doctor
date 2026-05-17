"""Load production samples from a configurable dataset."""

from __future__ import annotations

import os
from typing import Optional

import pandas as pd

from ml.run_config import MLRunConfig


def load_production_sample(
    n: int = 200,
    *,
    config: MLRunConfig | None = None,
    dataset_path: Optional[str] = None,
    drift_tag: Optional[str] = None,
) -> pd.DataFrame:
    """
    Load a sample of production rows for drift monitoring.
    """
    cfg = config or MLRunConfig.default()
    path = dataset_path or cfg.dataset_path
    tag = drift_tag or cfg.production_tag

    if not os.path.isfile(path):
        raise FileNotFoundError(f"Dataset not found at {path}.")

    df = pd.read_csv(path)
    prod = df[df["drift_tag"] == tag].dropna(subset=["user_query", "intent"])
    if prod.empty:
        raise ValueError(
            f"No rows with drift_tag='{tag}' in {path}. "
            "Check the dataset or pass custom records to /api/monitor/run."
        )

    sample_size = min(n, len(prod))
    return prod.sample(n=sample_size, random_state=42).reset_index(drop=True)
