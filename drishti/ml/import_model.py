"""Plug an externally trained model (e.g. an XGBoost model from a notebook) into the app.

    python -m drishti.ml.import_model models/incoming/model.json [--card model_card.json] [--load]

What it does, in order:
  1. loads the model (XGBoost native .json/.ubj, or a pickled/joblib scikit-learn-compatible estimator)
  2. checks the contract: it has predict_proba, its features exist, its input width matches, and it returns
     finite probabilities in [0, 1] on real rows
  3. calibrates on the app's validation split, picks thresholds there, scores the untouched test split once
     (the same protocol as the built-in model, so numbers are comparable)
  4. writes models/risk_model.joblib + models/metrics.json; with --load, re-scores all customers in the DB

SECURITY: .pkl/.joblib files are pickles and can run code when loaded. Only import files you trust.
The model must have been trained on the app's TRAIN split only (use `drishti.ml.train.make_splits`);
otherwise the test metrics are not honest.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from drishti.config import ROOT, get_settings
from drishti.ml.data import FEATURES, add_features, load_raw
from drishti.ml.train import make_splits, package

INCOMING = ROOT / "models" / "incoming"
MODEL_NAMES = ("model.json", "model.ubj", "model.joblib", "model.pkl")


class ContractError(ValueError):
    """The supplied model or model card does not satisfy the app's contract."""


def find_incoming(directory: Path = INCOMING) -> Path | None:
    for name in MODEL_NAMES:
        if (directory / name).exists():
            return directory / name
    return None


def load_model(path: Path):  # noqa: ANN201
    suffix = path.suffix.lower()
    if suffix in {".json", ".ubj"}:
        try:
            from xgboost import XGBClassifier
        except Exception as e:  # noqa: BLE001
            raise ContractError(f"xgboost could not be loaded ({e}). On macOS run: brew install libomp") from e
        m = XGBClassifier()
        m.load_model(str(path))
        return m
    if suffix in {".joblib", ".pkl", ".pickle"}:
        return joblib.load(path)
    raise ContractError(f"unsupported model file type '{suffix}' (use .json/.ubj for XGBoost, .joblib/.pkl otherwise)")


def read_card(path: Path | None) -> dict:
    if path is None or not path.exists():
        return {}
    card = json.loads(path.read_text())
    if not isinstance(card, dict):
        raise ContractError("model card must be a JSON object")
    return card


def validate(model, features: list[str], sample: pd.DataFrame) -> None:  # noqa: ANN001
    if not hasattr(model, "predict_proba"):
        raise ContractError("model needs predict_proba (wrap regressors/decision functions in a classifier)")
    unknown = [f for f in features if f not in sample.columns]
    if unknown:
        raise ContractError(
            f"features not available in the app: {unknown}. Add them to add_features() in drishti/ml/data.py "
            f"or drop them. Available: {sorted(sample.columns)}"
        )
    n_in = getattr(model, "n_features_in_", None)
    if n_in is not None and n_in != len(features):
        raise ContractError(f"model expects {n_in} features but the model card lists {len(features)}")
    names_in = getattr(model, "feature_names_in_", None)
    if names_in is not None and list(names_in) != list(features):
        raise ContractError("feature order/names differ from the card: "
                            f"model={list(names_in)[:5]}..., card={list(features)[:5]}...")
    p = np.asarray(model.predict_proba(sample[features].head(50)))
    if p.ndim != 2 or p.shape[1] != 2:
        raise ContractError(f"predict_proba must return shape (n, 2), got {p.shape}")
    if not np.isfinite(p).all() or p.min() < 0 or p.max() > 1:
        raise ContractError("predict_proba returned non-finite values or values outside [0, 1]")


def import_model(path: Path, card_path: Path | None = None, raw: pd.DataFrame | None = None) -> tuple[dict, dict]:
    """Validate + package an external model. Returns (artifact, report); writes nothing."""
    card = read_card(card_path or path.with_name("model_card.json"))
    features = list(card.get("features") or FEATURES)
    raw = load_raw() if raw is None else raw
    model = load_model(path)
    validate(model, features, add_features(raw))
    sp = make_splits(raw, features)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()[:12]
    name = str(card.get("name") or f"imported:{path.stem}")
    artifact, report = package(model, name, sp, source=f"imported from {path.name} (sha256 {digest})")
    report["model_card"] = {k: v for k, v in card.items() if k != "features"}
    return artifact, report


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("model", type=Path, nargs="?", help="path to the model (default: models/incoming/model.*)")
    ap.add_argument("--card", type=Path, help="model_card.json (default: next to the model)")
    ap.add_argument("--load", action="store_true", help="re-score every customer in the database afterwards")
    a = ap.parse_args()
    path = a.model or find_incoming()
    if path is None:
        print("no model given and nothing in models/incoming/", file=sys.stderr)
        return 2
    s = get_settings()
    try:
        artifact, report = import_model(path, a.card)
    except ContractError as e:
        print(f"CONTRACT ERROR: {e}", file=sys.stderr)
        return 1
    s.model_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(artifact, s.model_path)
    s.metrics_path.write_text(json.dumps(report, indent=2))
    print(json.dumps({k: report[k] for k in ("selected_model", "model_source", "test")}, indent=2))
    if a.load:
        from drishti.db.load import load_customers

        print(f"re-scored {load_customers()} customers")
    else:
        print("next: python -m drishti.db.load   (re-score customers with the new model)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
