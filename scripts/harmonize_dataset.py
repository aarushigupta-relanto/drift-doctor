#!/usr/bin/env python3
"""
Write final_dataset_harmonized.csv with clean_web intents mapped to the clean taxonomy.

Usage (from project root):
  python scripts/harmonize_dataset.py
  python scripts/harmonize_dataset.py --inplace   # overwrite final_dataset.csv (backup first)
"""

from __future__ import annotations

import argparse
import os
import sys

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from ml.intent_harmonizer import harmonize_dataframe, reference_intent_distribution


def main() -> None:
    parser = argparse.ArgumentParser(description="Harmonize clean_web intents to clean taxonomy")
    parser.add_argument(
        "--input",
        default=os.path.join(ROOT, "final_dataset.csv"),
        help="Input CSV path",
    )
    parser.add_argument(
        "--output",
        default=os.path.join(ROOT, "final_dataset_harmonized.csv"),
        help="Output CSV path (ignored if --inplace)",
    )
    parser.add_argument(
        "--inplace",
        action="store_true",
        help="Overwrite input file (creates .bak backup first)",
    )
    args = parser.parse_args()

    df = pd.read_csv(args.input)
    print(f"Loaded {len(df)} rows from {args.input}")
    print("Before (clean_web intents):")
    print(df[df["drift_tag"] == "clean_web"]["intent"].value_counts().head(8))

    harmonized = harmonize_dataframe(df, only_drift_tag="clean_web")
    print("\nAfter harmonization (clean_web):")
    print(reference_intent_distribution(harmonized))

    out_path = args.input if args.inplace else args.output
    if args.inplace:
        backup = args.input + ".bak"
        pd.read_csv(args.input).to_csv(backup, index=False)
        print(f"\nBackup written to {backup}")

    harmonized.to_csv(out_path, index=False)
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
