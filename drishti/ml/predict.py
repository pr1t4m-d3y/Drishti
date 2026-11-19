"""Scoring, segmenting and explaining. Wraps the trained artifact; does not retrain."""

from __future__ import annotations

from functools import lru_cache

import joblib
import numpy as np
import pandas as pd

from drishti.config import get_settings
from drishti.ml.data import add_features

LABELS = {
    "pay_1": "repayment status last month",
    "pay_2": "repayment status 2 months ago",
    "pay_3": "repayment status 3 months ago",
    "max_delay": "worst payment delay (months)",
    "n_delinquent_months": "number of delinquent months (of last 6)",
    "util_latest": "credit utilisation (latest bill / limit)",
    "util_mean": "average credit utilisation",
    "limit_bal": "credit limit",
    "repay_ratio": "share of billed amount repaid",
    "recent_delay_trend": "recent vs older delay trend",
}


@lru_cache
def load_artifact() -> dict:
    path = get_settings().model_path
    if not path.exists():
        raise FileNotFoundError(f"{path} missing. Run `python -m drishti.ml.train` first.")
    return joblib.load(path)


def segment_for(p: float) -> str:
    s = get_settings()
    if p >= s.seg_critical:
        return "CRITICAL"
    if p >= s.seg_high:
        return "HIGH"
    if p >= s.seg_medium:
        return "MEDIUM"
    return "LOW"


def score_frame(raw: pd.DataFrame) -> pd.DataFrame:
    """Return `raw` + derived features + risk_proba, risk_segment, top_risk_factors."""
    art = load_artifact()
    df = add_features(raw)
    X = df[art["features"]]
    df["risk_proba"] = art["model"].predict_proba(X)[:, 1]
    df["risk_segment"] = df["risk_proba"].map(segment_for)
    df["top_risk_factors"] = _top_factors(art, X)
    return df


def _top_factors(art: dict, X: pd.DataFrame, k: int = 3) -> list[list[dict]]:
    """Per-customer drivers: logistic coefficient x standardised value (explainer model).

    This explains the *linear surrogate*, not the gradient-boosted scorer. Documented as such.
    """
    pipe = art["explainer"]
    scaler, lr = pipe.steps[0][1], pipe.steps[-1][1]
    contrib = scaler.transform(X) * lr.coef_[0]
    names = list(art["features"])
    out = []
    for row in contrib:
        idx = np.argsort(row)[::-1][:k]
        out.append(
            [
                {"feature": names[i], "label": LABELS.get(names[i], names[i]), "impact": round(float(row[i]), 3)}
                for i in idx
                if row[i] > 0
            ]
        )
    return out
