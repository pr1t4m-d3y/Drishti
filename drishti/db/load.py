"""Load the UCI customers, score them with the trained model and store them.

Run:  python -m drishti.db.load
Idempotent: upserts by customer_id.
"""

from __future__ import annotations

import pandas as pd
from sqlalchemy import select

from drishti.db.models import Customer
from drishti.db.session import init_db, session_scope
from drishti.ml.data import load_raw
from drishti.ml.predict import score_frame

COLS = [c.name for c in Customer.__table__.columns if c.name not in {"scored_at"}]


def load_customers(df: pd.DataFrame | None = None, batch: int = 2000) -> int:
    init_db()
    scored = score_frame(load_raw() if df is None else df)
    records = scored[COLS].to_dict("records")
    n = 0
    with session_scope() as db:
        existing = set(db.scalars(select(Customer.customer_id)))
        for i in range(0, len(records), batch):
            for rec in records[i : i + batch]:
                if rec["customer_id"] in existing:
                    db.merge(Customer(**rec))
                else:
                    db.add(Customer(**rec))
                n += 1
            db.flush()
    return n


if __name__ == "__main__":
    print(f"loaded/updated {load_customers()} customers")
