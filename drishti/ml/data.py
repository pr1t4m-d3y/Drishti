"""Dataset loading for the credit-default model.

Dataset: UCI "Default of Credit Card Clients" (Yeh & Lien, 2009), 30,000 real, anonymised
Taiwanese card-holder records with a binary label `default payment next month`.
Source: https://archive.ics.uci.edu/dataset/350/default+of+credit+card+clients
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from drishti.config import ROOT

RAW_XLS = ROOT / "data" / "raw" / "default of credit card clients.xls"
UCI_URL = "https://archive.ics.uci.edu/static/public/350/default+of+credit+card+clients.zip"
TARGET = "default_label"

PAY_COLS = [f"pay_{i}" for i in range(1, 7)]  # 1 = most recent month (Sep), 6 = oldest (Apr)
BILL_COLS = [f"bill_amt{i}" for i in range(1, 7)]
PAYAMT_COLS = [f"pay_amt{i}" for i in range(1, 7)]
BASE_FEATURES = ["limit_bal", "sex", "education", "marriage", "age", *PAY_COLS, *BILL_COLS, *PAYAMT_COLS]


def load_raw(path: Path = RAW_XLS) -> pd.DataFrame:
    """Load and rename the raw UCI sheet. Raises a helpful error if it was not downloaded."""
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found. Run `make data` or download {UCI_URL} and unzip into data/raw/."
        )
    df = pd.read_excel(path, header=1)
    df = df.rename(columns={"PAY_0": "PAY_1", "default payment next month": TARGET})
    df.columns = [c.lower() for c in df.columns]
    df = df.rename(columns={"id": "customer_id"})
    return df


def add_features(df: pd.DataFrame) -> pd.DataFrame:
    """Domain features. All use only information available at scoring time (no label)."""
    out = df.copy()
    limit = out["limit_bal"].replace(0, np.nan)
    out["util_latest"] = (out["bill_amt1"] / limit).clip(-1, 5).fillna(0)
    out["util_mean"] = (out[BILL_COLS].mean(axis=1) / limit).clip(-1, 5).fillna(0)
    out["max_delay"] = out[PAY_COLS].max(axis=1)
    out["n_delinquent_months"] = (out[PAY_COLS] > 0).sum(axis=1)
    out["recent_delay_trend"] = out[PAY_COLS[:3]].mean(axis=1) - out[PAY_COLS[3:]].mean(axis=1)
    bills = out[BILL_COLS].sum(axis=1).replace(0, np.nan)
    out["repay_ratio"] = (out[PAYAMT_COLS].sum(axis=1) / bills).clip(0, 5).fillna(0)
    return out


FEATURES = [
    *BASE_FEATURES,
    "util_latest",
    "util_mean",
    "max_delay",
    "n_delinquent_months",
    "recent_delay_trend",
    "repay_ratio",
]


def data_quality_report(df: pd.DataFrame) -> dict:
    """Facts about the data, computed (never typed by hand)."""
    return {
        "rows": int(len(df)),
        "unique_customer_ids": int(df["customer_id"].nunique()),
        "duplicate_feature_rows": int(df.drop(columns=["customer_id"]).duplicated().sum()),
        "default_rate": float(df[TARGET].mean()),
        "missing_values": int(df.isna().sum().sum()),
    }
