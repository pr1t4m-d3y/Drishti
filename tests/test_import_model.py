"""The notebook-to-app contract: accepted models are packaged identically to the built-in ones; bad ones fail loudly."""

import json

import joblib
import pytest
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression

from drishti.ml import import_model as im
from drishti.ml.data import FEATURES
from drishti.ml.train import make_splits
from tests.test_pipeline_and_tools import _synthetic_raw


@pytest.fixture(scope="module")
def raw():
    return _synthetic_raw(1800)


def _fit(raw, features=None, cls=HistGradientBoostingClassifier):
    sp = make_splits(raw, features)
    return cls().fit(sp.X_tr, sp.y_tr)


def test_valid_joblib_model_is_packaged_with_the_same_protocol(raw, tmp_path):
    f = tmp_path / "model.joblib"
    joblib.dump(_fit(raw), f)
    (tmp_path / "model_card.json").write_text(json.dumps({"name": "friend-hgb", "features": FEATURES, "author": "x"}))
    art, rep = im.import_model(f, raw=raw)
    assert rep["selected_model"] == "friend-hgb" and "sha256" in rep["model_source"] and rep["model_card"]["author"] == "x"
    assert rep["split"]["test"] == 360 and 0 <= rep["test"]["at_max_f1_threshold"]["precision"] <= 1
    assert set(art) >= {"model", "base_model", "features", "explainer"}
    p = art["model"].predict_proba(make_splits(raw).X_te)[:, 1]
    assert ((p >= 0) & (p <= 1)).all()


def test_model_card_is_optional_and_defaults_to_app_features(raw, tmp_path):
    f = tmp_path / "m.joblib"
    joblib.dump(_fit(raw), f)
    art, _ = im.import_model(f, raw=raw)
    assert art["features"] == FEATURES


def test_subset_of_features_is_supported(raw, tmp_path):
    feats = ["limit_bal", "age", "pay_1", "pay_2", "max_delay", "util_latest"]
    f = tmp_path / "m.joblib"
    joblib.dump(_fit(raw, feats, LogisticRegression), f)
    (tmp_path / "model_card.json").write_text(json.dumps({"features": feats}))
    art, _ = im.import_model(f, raw=raw)
    assert art["features"] == feats


def test_unknown_feature_is_rejected_with_a_fix_hint(raw, tmp_path):
    f = tmp_path / "m.joblib"
    joblib.dump(_fit(raw), f)
    (tmp_path / "model_card.json").write_text(json.dumps({"features": [*FEATURES, "income_zscore"]}))
    with pytest.raises(im.ContractError, match="add_features"):
        im.import_model(f, raw=raw)


def test_width_mismatch_is_rejected(raw, tmp_path):
    f = tmp_path / "m.joblib"
    joblib.dump(_fit(raw), f)
    (tmp_path / "model_card.json").write_text(json.dumps({"features": FEATURES[:5]}))
    with pytest.raises(im.ContractError, match="expects"):
        im.import_model(f, raw=raw)


def test_model_without_predict_proba_is_rejected(raw, tmp_path):
    from sklearn.svm import LinearSVC

    f = tmp_path / "m.joblib"
    joblib.dump(LinearSVC().fit(make_splits(raw).X_tr, make_splits(raw).y_tr), f)
    with pytest.raises(im.ContractError, match="predict_proba"):
        im.import_model(f, raw=raw)


def test_unsupported_extension_is_rejected(tmp_path):
    f = tmp_path / "model.onnx"
    f.write_bytes(b"x")
    with pytest.raises(im.ContractError, match="unsupported"):
        im.load_model(f)


def test_find_incoming_prefers_xgboost_json(tmp_path):
    assert im.find_incoming(tmp_path) is None
    (tmp_path / "model.joblib").write_bytes(b"x")
    (tmp_path / "model.json").write_text("{}")
    assert im.find_incoming(tmp_path).name == "model.json"


def test_template_notebook_is_valid_and_follows_the_contract():
    from pathlib import Path

    nb = json.loads((Path(__file__).parent.parent / "notebooks" / "xgboost_model_template.ipynb").read_text())
    code = "\n".join("".join(c["source"]) for c in nb["cells"] if c["cell_type"] == "code")
    assert nb["nbformat"] == 4 and "make_splits" in code and "save_model" in code and "model_card.json" in code
    assert "sp.X_te" not in code and "y_te" not in code  # the notebook must never touch the test split
    compile(code.replace("%", "#"), "notebook", "exec")  # syntactically valid Python
