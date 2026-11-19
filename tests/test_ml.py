import numpy as np
import pandas as pd
import pytest

from drishti.config import get_settings
from drishti.ml.data import FEATURES, add_features
from drishti.ml.predict import segment_for

needs_model = pytest.mark.skipif(not get_settings().model_path.exists(), reason="model artifact not trained")


def _row(**kw):
    base = {"customer_id": 1, "limit_bal": 100000.0, "sex": 1, "education": 2, "marriage": 1, "age": 40,
            **{f"pay_{i}": 0 for i in range(1, 7)}, **{f"bill_amt{i}": 20000.0 for i in range(1, 7)},
            **{f"pay_amt{i}": 2000.0 for i in range(1, 7)}}
    return pd.DataFrame([base | kw])


def test_feature_engineering_uses_no_label():
    df = add_features(_row(pay_1=2, pay_2=1))
    assert "default_label" not in FEATURES and set(FEATURES) <= set(df.columns)
    assert df.loc[0, "n_delinquent_months"] == 2 and df.loc[0, "max_delay"] == 2
    assert df.loc[0, "util_latest"] == pytest.approx(0.2)


def test_zero_limit_does_not_divide_by_zero():
    df = add_features(_row(limit_bal=0.0))
    assert np.isfinite(df.loc[0, "util_latest"])


def test_segment_boundaries():
    assert [segment_for(p) for p in (0.0, 0.25, 0.40, 0.60, 1.0)] == ["LOW", "MEDIUM", "HIGH", "CRITICAL", "CRITICAL"]


@needs_model
def test_scoring_orders_risk_and_explains_with_shap():
    from drishti.ml.predict import score_frame

    safe = score_frame(_row())
    risky = score_frame(_row(**{f"pay_{i}": 3 for i in range(1, 7)}, pay_amt1=0.0))
    assert risky.loc[0, "risk_proba"] > safe.loc[0, "risk_proba"]
    top = risky.loc[0, "top_risk_factors"]
    assert top and all(f["impact"] > 0 for f in top)
    assert any(f["feature"] in {"max_delay", "pay_1", "n_delinquent_months", "pay_2"} for f in top)
