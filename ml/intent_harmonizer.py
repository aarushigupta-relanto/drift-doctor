"""
Map clean_web (production) rows onto the historical clean intent taxonomy using query text.

The raw dataset uses different label sets:
  clean     -> Greeting, UnderstandQuery, Jokes, ...
  clean_web -> unknown, info_request, support_request, ...

Coarse label mapping (support_request -> CurrentHumanQuery) collapses ~98% of rows
into one class and makes deployed accuracy look like 0%. Harmonization infers intents
from user_query so validation and retraining share one label space.
"""

from __future__ import annotations

import re
from typing import Iterable

import pandas as pd

# Reference taxonomy from final_dataset.csv (drift_tag=clean)
REFERENCE_INTENTS: tuple[str, ...] = (
    "Greeting",
    "GreetingResponse",
    "CourtesyGreeting",
    "CourtesyGreetingResponse",
    "CurrentHumanQuery",
    "RealNameQuery",
    "TimeQuery",
    "NotTalking2U",
    "Shutup",
    "Clever",
    "PodBayDoor",
    "PodBayDoorResponse",
    "SelfAware",
    "NameQuery",
    "Thanks",
    "UnderstandQuery",
    "CourtesyGoodBye",
    "WhoAmI",
    "Gossip",
    "Jokes",
    "Swearing",
    "GoodBye",
)

# (compiled regex, intent) — first match wins
_QUERY_RULES: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"^(hi|hello|hey|hola|hya)\b", re.I), "Greeting"),
    (re.compile(r"^(hi|hello|hey).{0,20}(how are you|doing well)", re.I), "CourtesyGreeting"),
    (re.compile(r"how are you|hope you are doing", re.I), "CourtesyGreeting"),
    (re.compile(r"my user is|this is [a-z]+|i am [a-z]+", re.I), "GreetingResponse"),
    (re.compile(r"good thanks|doing well.*user", re.I), "CourtesyGreetingResponse"),
    (re.compile(r"\b(bye|goodbye|see you|good night)\b", re.I), "GoodBye"),
    (re.compile(r"thanks|thank you", re.I), "Thanks"),
    (re.compile(r"\b(joke|jokes|funny|laugh)\b", re.I), "Jokes"),
    (re.compile(r"who are you|what are you|are you (real|human|ai)", re.I), "WhoAmI"),
    (re.compile(r"\btime\b|what time|what's the time", re.I), "TimeQuery"),
    (re.compile(r"your name|what is your name|who is [a-z]", re.I), "NameQuery"),
    (re.compile(r"real name|actual name", re.I), "RealNameQuery"),
    (re.compile(r"open the pod bay|pod bay door", re.I), "PodBayDoor"),
    (re.compile(r"clever|smart|intelligent", re.I), "Clever"),
    (re.compile(r"gossip|rumor|heard about", re.I), "Gossip"),
    (re.compile(r"swear|damn|hell\b", re.I), "Swearing"),
    (re.compile(r"shut up|be quiet|stop talking", re.I), "Shutup"),
    (re.compile(r"not talking|leave me alone", re.I), "NotTalking2U"),
    (re.compile(r"download", re.I), "UnderstandQuery"),
    (
        re.compile(
            r"documentation|tutorial|reference|library|manual|faq|install|"
            r"module|api|syntax|embedding|distributing|extending|whats new|"
            r"language reference|standard library|howto",
            re.I,
        ),
        "UnderstandQuery",
    ),
    (re.compile(r"foundation|organization|member|support_request|contact", re.I), "CurrentHumanQuery"),
    (re.compile(r"problem|error|bug|fail|broken", re.I), "Shutup"),
    (re.compile(r"understand|explain|what does|how do i|how to", re.I), "UnderstandQuery"),
]

# Fallback when raw production label is known but query rules miss
_RAW_LABEL_MAP: dict[str, str] = {
    "support_request": "CurrentHumanQuery",
    "info_request": "UnderstandQuery",
    "download_query": "UnderstandQuery",
    "problem": "Shutup",
    "unknown": "UnderstandQuery",
}


def infer_reference_intent(
    user_query: str,
    raw_intent: str | None = None,
    *,
    default: str = "UnderstandQuery",
) -> str:
    """Infer a historical (clean) intent from query text and optional raw production label."""
    text = (user_query or "").strip()
    for pattern, intent in _QUERY_RULES:
        if pattern.search(text):
            return intent

    if raw_intent:
        mapped = _RAW_LABEL_MAP.get(str(raw_intent).strip().lower())
        if mapped:
            return mapped

    return default if default in REFERENCE_INTENTS else "UnderstandQuery"


def harmonize_dataframe(
    df: pd.DataFrame,
    *,
    only_drift_tag: str | None = "clean_web",
    inplace: bool = False,
) -> pd.DataFrame:
    """
    Add ``intent_original`` and set ``intent`` to harmonized reference taxonomy.

    Rows with drift_tag=clean are left unchanged (already in reference taxonomy).
    """
    out = df if inplace else df.copy()
    if "intent_original" not in out.columns:
        out["intent_original"] = out["intent"]

    mask = (
        out["drift_tag"] == only_drift_tag
        if only_drift_tag is not None
        else pd.Series(True, index=out.index)
    )

    def _row_intent(row: pd.Series) -> str:
        return infer_reference_intent(
            str(row.get("user_query", "")),
            str(row.get("intent_original", row.get("intent", ""))),
        )

    out.loc[mask, "intent"] = out.loc[mask].apply(_row_intent, axis=1)
    return out


def harmonize_production_frame(
    historical: pd.DataFrame,
    production: pd.DataFrame,
) -> pd.DataFrame:
    """Align clean_web rows for training/validation (keeps intent_original)."""
    aligned = production.copy()
    if "intent_original" not in aligned.columns:
        aligned["intent_original"] = aligned["intent"]
    aligned["intent"] = [
        infer_reference_intent(q, raw)
        for q, raw in zip(aligned["user_query"], aligned["intent_original"])
    ]
    return aligned


def reference_intent_distribution(
    df: pd.DataFrame,
    drift_tag: str = "clean_web",
) -> pd.Series:
    """Debug: intent counts after harmonization."""
    subset = df[df["drift_tag"] == drift_tag] if "drift_tag" in df.columns else df
    return subset["intent"].value_counts()
