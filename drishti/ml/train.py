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
from dataclasses import dataclass
from datetime import UTC, datetime

import joblib
import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.frozen import FrozenEstimator
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    balanced_accuracy_score,
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
        "accuracy": round(float(accuracy_score(y, pred)), 4),
        "balanced_accuracy": round(float(balanced_accuracy_score(y, pred)), 4),
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


def _xgboost_candidate():  # noqa: ANN202
    """XGBoost if it can be loaded (on macOS it needs the OpenMP runtime: `brew install libomp`)."""
    try:
        from xgboost import XGBClassifier

        return XGBClassifier(
            n_estimators=400, max_depth=4, learning_rate=0.05, subsample=0.9, colsample_bytree=0.9,
            reg_lambda=1.0, eval_metric="aucpr", tree_method="hist", random_state=SEED, n_jobs=-1,
        )
    except Exception:  # noqa: BLE001 - ImportError or XGBoostError (missing libomp)
        return None


@dataclass
class Splits:
    """The fixed 60/20/20 stratified split every model (built-in or imported) is trained and judged on."""

    X_tr: pd.DataFrame
    X_val: pd.DataFrame
    X_te: pd.DataFrame
    y_tr: np.ndarray
    y_val: np.ndarray
    y_te: np.ndarray
    features: list[str]
    quality: dict


def make_splits(raw: pd.DataFrame, features: list[str] | None = None) -> Splits:
    """Deterministic split (seed 42). Notebooks should call this so train/validation/test match the app."""
    features = list(features or FEATURES)
    quality = data_quality_report(raw)
    df = add_features(raw)
    X, y = df[features], df[TARGET].to_numpy()
    X_tr, X_tmp, y_tr, y_tmp = train_test_split(X, y, test_size=0.4, stratify=y, random_state=SEED)
    X_val, X_te, y_val, y_te = train_test_split(X_tmp, y_tmp, test_size=0.5, stratify=y_tmp, random_state=SEED)
    return Splits(X_tr, X_val, X_te, y_tr, y_val, y_te, features, quality)


def package(base_model, name: str, sp: Splits, val_scores: dict[str, float] | None = None,  # noqa: ANN001
            source: str = "trained by drishti.ml.train") -> tuple[dict, dict]:
    """Calibrate an already-fitted `base_model` on validation, pick thresholds, score the test set once.

    Returns (artifact, report). Used for the built-in candidates and for models imported from a notebook,
    so both are judged by exactly the same protocol.
    """
    if val_scores is None:
        val_scores = {name: float(average_precision_score(sp.y_val, base_model.predict_proba(sp.X_val)[:, 1]))}
    calibrated = CalibratedClassifierCV(FrozenEstimator(base_model), method="isotonic")
    calibrated.fit(sp.X_val, sp.y_val)
    # NOTE: calibrating on the validation set means thresholds picked on it are slightly optimistic;
    # the untouched test set below is what gets reported.
    p_val = calibrated.predict_proba(sp.X_val)[:, 1]
    p_te = calibrated.predict_proba(sp.X_te)[:, 1]

    thr_f1 = _pick_threshold(sp.y_val, p_val)
    thr_p = _pick_threshold(sp.y_val, p_val, min_precision=0.80)
    overlap = int(len(set(map(tuple, sp.X_tr.to_numpy())) & set(map(tuple, sp.X_te.to_numpy()))))
    report = {
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "dataset": "UCI Default of Credit Card Clients (30k rows)",
        "data_quality": sp.quality,
        "split": {"train": len(sp.X_tr), "validation": len(sp.X_val), "test": len(sp.X_te), "seed": SEED},
        "train_test_duplicate_feature_rows": overlap,
        "test_base_rate": round(float(sp.y_te.mean()), 4),
        "majority_class_accuracy": round(float(1 - sp.y_te.mean()), 4),  # accuracy of "nobody defaults"
        "validation_pr_auc_by_model": {k: round(v, 4) for k, v in val_scores.items()},
        "selected_model": name,
        "model_source": source,
        "test": {
            "at_max_f1_threshold": _metrics(sp.y_te, p_te, thr_f1),
            "at_precision_target_0.80_on_validation": (
                _metrics(sp.y_te, p_te, thr_p) if not np.isnan(thr_p) else None
            ),
        },
        "notes": [
            "Precision target 0.80 is set on validation; null means no threshold reached it.",
            "Test set was used once, after model selection, calibration and thresholding.",
        ],
    }
    artifact = {"model": calibrated, "base_model": base_model, "features": sp.features,
                "explainer": _fit_explainer(sp.X_tr, sp.y_tr), "name": name, "source": source}
    return artifact, report


def fit_and_evaluate(raw: pd.DataFrame) -> tuple[dict, dict]:
    """Train the built-in candidates, select by validation PR-AUC, package. No files are written."""
    sp = make_splits(raw)
    candidates = {
        "logistic_regression": make_pipeline(
            StandardScaler(), LogisticRegression(max_iter=2000, class_weight="balanced")
        ),
        "hist_gradient_boosting": HistGradientBoostingClassifier(
            max_depth=4, learning_rate=0.05, max_iter=300, l2_regularization=1.0, random_state=SEED
        ),
    }
    xgb = _xgboost_candidate()
    if xgb is not None:
        candidates["xgboost"] = xgb
    val_scores = {}
    for name, est in candidates.items():
        est.fit(sp.X_tr, sp.y_tr)
        val_scores[name] = float(average_precision_score(sp.y_val, est.predict_proba(sp.X_val)[:, 1]))
    best_name = max(val_scores, key=val_scores.get)  # type: ignore[arg-type]
    return package(candidates[best_name], best_name, sp, val_scores)


def main() -> int:
    s = get_settings()
    if "--builtin" not in sys.argv:
        from drishti.ml.import_model import find_incoming

        incoming = find_incoming()
        if incoming is not None:  # a model from a notebook is waiting in models/incoming/
            from drishti.ml.import_model import main as import_main

            print(f"using the model in {incoming} (pass --builtin to train the built-in candidates instead)")
            sys.argv = [sys.argv[0], str(incoming)]
            return import_main()
    artifact, report = fit_and_evaluate(load_raw())
    s.model_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(artifact, s.model_path)
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
