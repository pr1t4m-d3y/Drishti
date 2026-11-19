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
    **{f"pay_{i}": f"repayment status {i} month(s) ago" for i in range(4, 7)},
    **{f"pay_amt{i}": f"payment made {i} month(s) ago" for i in range(1, 7)},
    **{f"bill_amt{i}": f"bill amount {i} month(s) ago" for i in range(1, 7)},
    "age": "age",
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


def _shap_contributions(art: dict, X: pd.DataFrame) -> np.ndarray | None:
    """Exact TreeSHAP values (log-odds) for the *selected* model. None if SHAP is unavailable.

    Calibration is a monotonic map applied after the base model, so the features that push the raw score
    up are the same ones that push the calibrated probability up.
    """
    try:
        import shap

        base = art.get("base_model")
        if base is None:
            return None
        values = shap.TreeExplainer(base).shap_values(X)
        values = np.asarray(values[1] if isinstance(values, list) else values)
        return values[..., 1] if values.ndim == 3 else values
    except Exception:  # noqa: BLE001 - explanations must never break scoring
        return None


def _top_factors(art: dict, X: pd.DataFrame, k: int = 3) -> list[list[dict]]:
    """Per-customer drivers: SHAP values of the real model, falling back to a logistic surrogate."""
    contrib = _shap_contributions(art, X)
    if contrib is None:  # fallback: coefficient x standardised value of the linear surrogate
        pipe = art["explainer"]
        contrib = pipe.steps[0][1].transform(X) * pipe.steps[-1][1].coef_[0]
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
