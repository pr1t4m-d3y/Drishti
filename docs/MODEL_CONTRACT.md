# Model contract

How a model trained outside the app (for example an XGBoost notebook) becomes the model the app serves.

## The short version

1. Train on the app's **train split** only, in a notebook (`notebooks/xgboost_model_template.ipynb` is a starting point).
2. Export `model.json` (XGBoost) or `model.joblib` plus `model_card.json` into `models/incoming/`.
3. Run `python -m drishti.ml.import_model --load`.

The command validates the model, calibrates it on the validation split, picks thresholds there, evaluates on the test split
**once**, writes `models/risk_model.joblib` and `models/metrics.json`, and re-scores every customer in the database.
The API, the dashboards and the agents then use it. Nothing else changes.

## Requirements

| Item | Requirement |
|---|---|
| Interface | `predict_proba(X)` returning shape `(n, 2)`, finite, within `[0, 1]` |
| Formats | XGBoost native `.json` / `.ubj`, or a joblib/pickle scikit-learn-compatible estimator |
| Input | A DataFrame with the columns listed in `model_card.json` -> `features` (default: `drishti.ml.data.FEATURES`) |
| Features | Raw UCI columns (`limit_bal`, `pay_1`..`pay_6`, `bill_amt1`..`6`, `pay_amt1`..`6`, ...) and the engineered ones from `add_features()` in `drishti/ml/data.py` |
| Feature order | Must match the card (and `feature_names_in_` if the model has it) |
| Training data | The app's **train split** (`drishti.ml.train.make_splits`, seed 42). Validation may be used for early stopping. **Never the test split**, or the reported metrics are not honest |
| Label | `default_label` (1 = defaults next month) |

`model_card.json` (optional, but recommended):

```json
{
  "name": "xgboost-notebook-v1",
  "features": ["limit_bal", "age", "pay_1", "..."],
  "trained_on": "app train split only (seed 42)",
  "author": "name",
  "notes": "free text"
}
```

## Adding a new feature

The API, the agents and the batch scorer all compute features in one place: `add_features()` in `drishti/ml/data.py`.
Add the feature there (using only information available at scoring time, never the label), list it in the card, and
the whole app computes it the same way. A card that lists a feature the app cannot compute is rejected with a message
that says so.

## What the importer checks

* the file loads (XGBoost needs the OpenMP runtime on macOS: `brew install libomp`)
* `predict_proba` exists and returns valid probabilities on 50 real rows
* every listed feature exists; the model's input width and feature names match the card
* afterwards: calibration, threshold selection and test evaluation use the same code as the built-in model
  (`drishti/ml/train.py::package`), so numbers are comparable

Failures exit with `CONTRACT ERROR: ...` and change nothing.

## Security

`.pkl` and `.joblib` files are pickles and can execute code on load. Only import files you trust; prefer XGBoost's
native `.json`, which is plain data.

## What runs where

| Command | Behaviour |
|---|---|
| `make train` / `python -m drishti.ml.train` | Uses `models/incoming/model.*` if present, otherwise trains the built-in candidates (logistic regression, gradient boosting, and XGBoost when it can be loaded) and keeps the best on validation PR-AUC. `--builtin` forces the built-in path |
| `python -m drishti.ml.import_model path` | Import a specific file |
| Docker build, CI | Both call the same training entry point, so a committed `models/incoming/model.json` is validated on every PR and baked into the image |
