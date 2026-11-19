"""Generate the README figures from the real model and data:  python -m drishti.ml.figures

Writes docs/images/*.png. Every plotted number comes from the held-out test split or the scored
customers table; nothing is typed in.
"""

from __future__ import annotations

import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from sklearn.metrics import precision_recall_curve  # noqa: E402
from sklearn.model_selection import train_test_split  # noqa: E402

from drishti.config import ROOT, get_settings  # noqa: E402
from drishti.ml.data import FEATURES, TARGET, add_features, load_raw  # noqa: E402
from drishti.ml.predict import _shap_contributions, load_artifact  # noqa: E402
from drishti.ml.train import SEED  # noqa: E402

OUT = ROOT / "docs" / "images"
NAVY, SKY, RED = "#001C38", "#00AEEF", "#D32F2F"


def _test_split():
    df = add_features(load_raw())
    X, y = df[FEATURES], df[TARGET].to_numpy()
    X_tr, X_tmp, y_tr, y_tmp = train_test_split(X, y, test_size=0.4, stratify=y, random_state=SEED)
    _, X_te, _, y_te = train_test_split(X_tmp, y_tmp, test_size=0.5, stratify=y_tmp, random_state=SEED)
    return X_te, y_te


def pr_curve() -> None:
    art, metrics = load_artifact(), json.loads(get_settings().metrics_path.read_text())
    X_te, y_te = _test_split()
    p = art["model"].predict_proba(X_te)[:, 1]
    prec, rec, _ = precision_recall_curve(y_te, p)
    fig, ax = plt.subplots(figsize=(6.4, 4.2), dpi=150)
    ax.plot(rec, prec, color=SKY, lw=2, label="calibrated model (test set)")
    ax.axhline(y_te.mean(), color="grey", ls=":", label=f"no-skill ({y_te.mean():.3f})")
    for key, color, name in (("at_max_f1_threshold", NAVY, "max-F1"), ("at_precision_target_0.80_on_validation", RED, "strict")):
        pt = metrics["test"].get(key)
        if pt:
            ax.scatter(pt["recall"], pt["precision"], color=color, zorder=5, s=50)
            ax.annotate(f"{name}\nP={pt['precision']:.2f}, R={pt['recall']:.2f}", (pt["recall"], pt["precision"]),
                        textcoords="offset points", xytext=(10, 6), fontsize=8, color=color)
    ax.set(xlabel="Recall", ylabel="Precision", title="Precision vs recall on 6,000 held-out customers", xlim=(0, 1), ylim=(0, 1.02))
    ax.legend(loc="upper right", fontsize=8)
    ax.grid(alpha=0.2)
    fig.tight_layout()
    fig.savefig(OUT / "precision_recall.png")
    plt.close(fig)


def segments() -> None:
    from sqlalchemy import text

    from drishti.db.session import get_engine

    with get_engine().connect() as c:
        rows = c.execute(text("SELECT risk_segment, COUNT(*), AVG(default_label) FROM customers GROUP BY 1")).all()
    order = ["CRITICAL", "HIGH", "MEDIUM", "LOW"]
    data = {r[0]: (r[1], r[2]) for r in rows}
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(9, 3.6), dpi=150)
    cols = [RED, "#F57C00", SKY, "#2E7D32"]
    a1.bar(order, [data[s][0] for s in order], color=cols)
    a1.set(title="Customers per risk segment", ylabel="customers")
    a2.bar(order, [data[s][1] * 100 for s in order], color=cols)
    a2.set(title="Observed default rate per segment (%)", ylabel="% defaulted next month")
    for a in (a1, a2):
        a.grid(axis="y", alpha=0.2)
    fig.text(0.5, 0.005, "All 30,000 customers, including rows the model trained on (in-sample).", ha="center", fontsize=7, color="grey")
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(OUT / "segments.png")
    plt.close(fig)


def shap_importance() -> None:
    art = load_artifact()
    X_te, _ = _test_split()
    sample = X_te.sample(1500, random_state=SEED)
    vals = _shap_contributions(art, sample)
    if vals is None:
        return
    imp = np.abs(vals).mean(axis=0)
    idx = np.argsort(imp)[::-1][:10][::-1]
    fig, ax = plt.subplots(figsize=(6.4, 4), dpi=150)
    ax.barh([FEATURES[i] for i in idx], imp[idx], color=NAVY)
    ax.set(title="What drives the score (mean |SHAP|, 1,500 test customers)", xlabel="mean |SHAP| (log-odds)")
    ax.grid(axis="x", alpha=0.2)
    fig.tight_layout()
    fig.savefig(OUT / "shap_importance.png")
    plt.close(fig)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    pr_curve()
    segments()
    shap_importance()
    print("wrote", *sorted(p.name for p in OUT.glob("*.png")))


if __name__ == "__main__":
    main()
