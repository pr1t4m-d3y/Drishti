"""Train, calibrate and evaluate the default-risk model.

Run:  python -m drishti.ml.train

Protocol (all decisions made on validation data only; test touched once):
  1. Stratified 60/20/20 train / validation / test split, fixed seed.
  2. Baseline: standardised logistic regression. Candidate: HistGradientBoosting.
  3. Pick the better model by validation PR-AUC, then calibrate probabilities on validation.
  4. Choose the decision threshold on validation (max F1, plus a "high precision" operating point).
  5. Report precision / recall / F1 / PR-AUC / ROC-AUC on the untouched test set.

Leakage controls: the customer id is not a feature; the label never enters feature engineering;
scaling / imputation are fit inside a Pipeline on the training split only; duplicate feature
rows across splits are counted and reported.

Everything written to models/metrics.json is computed here. Nothing is hand-edited.
"""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime

import joblib
import numpy as np
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.frozen import FrozenEstimator
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    f1_score,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from drishti.config import get_settings
from drishti.ml.data import FEATURES, TARGET, add_features, data_quality_report, load_raw

SEED = 42


def _metrics(y, proba, thr: float) -> dict:
    pred = (proba >= thr).astype(int)
    return {
        "threshold": round(float(thr), 4),
        "precision": round(float(precision_score(y, pred, zero_division=0)), 4),
        "recall": round(float(recall_score(y, pred)), 4),
        "f1": round(float(f1_score(y, pred)), 4),
        "flagged": int(pred.sum()),
        "pr_auc": round(float(average_precision_score(y, proba)), 4),
        "roc_auc": round(float(roc_auc_score(y, proba)), 4),
    }


def _pick_threshold(y, proba, min_precision: float | None = None) -> float:
    p, r, t = precision_recall_curve(y, proba)
    p, r = p[:-1], r[:-1]
    if min_precision is None:
        f1 = 2 * p * r / np.clip(p + r, 1e-9, None)
        return float(t[int(np.argmax(f1))])
    ok = np.where(p >= min_precision)[0]
    if len(ok) == 0:
        return float("nan")  # operating point unreachable; reported honestly as null
    return float(t[ok[int(np.argmax(r[ok]))]])


def main() -> int:
    s = get_settings()
    raw = load_raw()
    quality = data_quality_report(raw)
    df = add_features(raw)
    X, y = df[FEATURES], df[TARGET].to_numpy()

    X_tr, X_tmp, y_tr, y_tmp = train_test_split(X, y, test_size=0.4, stratify=y, random_state=SEED)
    X_val, X_te, y_val, y_te = train_test_split(
        X_tmp, y_tmp, test_size=0.5, stratify=y_tmp, random_state=SEED
    )
    overlap = int(
        len(set(map(tuple, X_tr.to_numpy())) & set(map(tuple, X_te.to_numpy())))
    )

    candidates = {
        "logistic_regression": make_pipeline(
            StandardScaler(), LogisticRegression(max_iter=2000, class_weight="balanced")
        ),
        "hist_gradient_boosting": HistGradientBoostingClassifier(
            max_depth=4, learning_rate=0.05, max_iter=300, l2_regularization=1.0, random_state=SEED
        ),
    }
    val_scores = {}
    for name, est in candidates.items():
        est.fit(X_tr, y_tr)
        val_scores[name] = float(average_precision_score(y_val, est.predict_proba(X_val)[:, 1]))
    best_name = max(val_scores, key=val_scores.get)  # type: ignore[arg-type]

    calibrated = CalibratedClassifierCV(FrozenEstimator(candidates[best_name]), method="isotonic")
    calibrated.fit(X_val, y_val)
    # NOTE: calibrating on the validation set means thresholds picked on it are slightly optimistic;
    # the untouched test set below is what gets reported.
    p_val = calibrated.predict_proba(X_val)[:, 1]
    p_te = calibrated.predict_proba(X_te)[:, 1]

    thr_f1 = _pick_threshold(y_val, p_val)
    thr_p = _pick_threshold(y_val, p_val, min_precision=0.80)
    report = {
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "dataset": "UCI Default of Credit Card Clients (30k rows)",
        "data_quality": quality,
        "split": {"train": len(X_tr), "validation": len(X_val), "test": len(X_te), "seed": SEED},
        "train_test_duplicate_feature_rows": overlap,
        "test_base_rate": round(float(y_te.mean()), 4),
        "validation_pr_auc_by_model": {k: round(v, 4) for k, v in val_scores.items()},
        "selected_model": best_name,
        "test": {
            "at_max_f1_threshold": _metrics(y_te, p_te, thr_f1),
            "at_precision_target_0.80_on_validation": (
                _metrics(y_te, p_te, thr_p) if not np.isnan(thr_p) else None
            ),
        },
        "notes": [
            "Precision target 0.80 is set on validation; null means no threshold reached it.",
            "Test set was used once, after model selection, calibration and thresholding.",
        ],
    }
    s.model_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(
        {"model": calibrated, "base_model": candidates[best_name], "features": FEATURES,
         "explainer": _fit_explainer(X_tr, y_tr)},
        s.model_path,
    )
    s.metrics_path.write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))
    return 0


def _fit_explainer(X_tr, y_tr):
    """Logistic regression used only to explain individual scores (coefficient x z-score)."""
    pipe = make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000, class_weight="balanced"))
    pipe.fit(X_tr, y_tr)
    return pipe


if __name__ == "__main__":
    sys.exit(main())
