#!/usr/bin/env python3
"""
Generate datasets/drift_doctor_demo.csv — aligned historical + production splits.

Same intent taxonomy on both drift_tag values; production uses shifted phrasing
and intent mix so drift / retrain demos behave realistically without harmonizers.
"""

from __future__ import annotations

import os
import random
from datetime import datetime, timedelta

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_PATH = os.path.join(ROOT, "datasets", "drift_doctor_demo.csv")

INTENTS = (
    "greeting",
    "billing",
    "api_help",
    "order_status",
    "refund",
    "pricing",
    "account",
    "technical_support",
)

# Historical (clean) phrasing templates per intent
HISTORICAL_TEMPLATES: dict[str, list[str]] = {
    "greeting": ["hi", "hello there", "hey", "good morning"],
    "billing": ["question about my bill", "why was I charged twice", "invoice looks wrong"],
    "api_help": ["how do I call the API", "api authentication help", "webhook setup"],
    "order_status": ["where is my order", "track order #{}", "has my package shipped"],
    "refund": ["I want a refund", "return policy", "money back please"],
    "pricing": ["how much is the pro plan", "pricing tiers", "enterprise cost"],
    "account": ["reset my password", "update email on account", "close my account"],
    "technical_support": ["app keeps crashing", "error 500 on login", "feature not working"],
}

# Production (clean_web) — drifted phrasing
PRODUCTION_TEMPLATES: dict[str, list[str]] = {
    "greeting": ["yo", "heya whats up", "hiiii need help"],
    "billing": ["charged me twice on card ???", "billing dispute for last month", "subscription charge unclear"],
    "api_help": ["v2 API auth token where", "how authenticate webhook v2", "REST endpoint docs outdated"],
    "order_status": ["still waiting on shipment #{}", "delivery delayed order {}", "tracking number not updating"],
    "refund": ["refund after 45 days possible?", "chargeback for duplicate payment", "cancel and refund order"],
    "pricing": ["pricing page shows old tiers", "how much enterprise now 2025", "pro plan annual price"],
    "account": ["cant log in after password reset", "merge two accounts", "GDPR delete my data"],
    "technical_support": ["login fails with 403", "dashboard blank screen", "integration timeout errors"],
}


def _rows_for_tag(
    tag: str,
    templates: dict[str, list[str]],
    n: int,
    *,
    intent_weights: dict[str, float] | None = None,
) -> list[dict]:
    intents = list(INTENTS)
    weights = [intent_weights.get(i, 1.0) if intent_weights else 1.0 for i in intents]
    rows: list[dict] = []
    base_date = datetime(2025, 1, 1)
    for i in range(n):
        intent = random.choices(intents, weights=weights, k=1)[0]
        tpl = random.choice(templates[intent])
        query = tpl.format(random.randint(1000, 9999)) if "{}" in tpl else tpl
        rows.append(
            {
                "user_query": query,
                "intent": intent,
                "response": f"auto-response for {intent}",
                "source": "synthetic",
                "timestamp": (base_date + timedelta(days=i % 180)).strftime("%Y-%m-%d"),
                "drift_tag": tag,
            }
        )
    return rows


def generate(
    n_clean: int = 400,
    n_clean_web: int = 900,
    *,
    seed: int = 42,
) -> pd.DataFrame:
    random.seed(seed)
    # Production skew: more api_help + billing (simulated drift)
    prod_weights = {
        "greeting": 0.5,
        "billing": 2.0,
        "api_help": 2.5,
        "order_status": 1.2,
        "refund": 1.5,
        "pricing": 1.0,
        "account": 1.0,
        "technical_support": 1.8,
    }
    hist = _rows_for_tag("clean", HISTORICAL_TEMPLATES, n_clean)
    prod = _rows_for_tag("clean_web", PRODUCTION_TEMPLATES, n_clean_web, intent_weights=prod_weights)
    return pd.DataFrame(hist + prod)


def main() -> None:
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    df = generate()
    df.to_csv(OUT_PATH, index=False)
    print(f"Wrote {len(df)} rows to {OUT_PATH}")
    print(df.groupby(["drift_tag", "intent"]).size().head(20))


if __name__ == "__main__":
    main()
