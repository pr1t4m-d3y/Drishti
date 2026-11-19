import pytest

from drishti.agents.tools import sql_tools as t


def test_unknown_query_rejected():
    assert "error" in t.run_allowlisted_query("drop_everything")


def test_wrong_or_extra_params_rejected():
    assert "error" in t.run_allowlisted_query("customer_by_id", {})
    assert "error" in t.run_allowlisted_query("customer_by_id", {"customer_id": 1, "x": 2})


def test_type_coercion_and_rejection():
    assert t.validate_params("customer_by_id", {"customer_id": "3"}) == {"customer_id": 3}
    with pytest.raises(t.QueryError):
        t.validate_params("customer_by_id", {"customer_id": "abc"})
    with pytest.raises(t.QueryError):
        t.validate_params("customer_by_id", {"customer_id": True})


def test_row_limit_clamped_and_segment_validated():
    assert t.validate_params("top_risk", {"n": 10_000})["n"] == t.MAX_ROWS
    assert t.validate_params("top_risk", {"n": -5})["n"] == 1
    assert t.validate_params("top_risk_in_segment", {"segment": "high", "n": 3})["segment"] == "HIGH"
    with pytest.raises(t.QueryError):
        t.validate_params("top_risk_in_segment", {"segment": "x' OR 1=1 --", "n": 3})


def test_sql_injection_string_is_bound_not_executed():
    res = t.get_customer("1; DROP TABLE customers")  # type: ignore[arg-type]
    assert "error" in res
    assert t.get_customer(1)["row_count"] == 1  # table still intact


def test_default_label_never_selected():
    for q in t.ALLOWLIST.values():
        assert "default_label" not in q.sql
        assert "SELECT *" not in q.sql.upper()
    assert "default_label" not in t.get_customer(1)["rows"][0]


def test_top_risk_ordering():
    rows = t.top_risk_customers(3)["rows"]
    assert [r["customer_id"] for r in rows] == [1, 2, 3]


def test_missed_payment_count():
    assert t.count_missed_payments(2)["rows"][0]["customers"] == 3


def test_readonly_connection_blocks_writes():
    from sqlalchemy import text
    from sqlalchemy.exc import OperationalError

    from drishti.db.session import get_readonly_engine

    with get_readonly_engine().connect() as c, pytest.raises(OperationalError):
        c.execute(text("DELETE FROM customers"))
