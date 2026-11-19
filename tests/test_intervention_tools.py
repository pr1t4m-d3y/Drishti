import numpy as np
import pytest

from drishti.agents.tools import intervention_tools as it
from drishti.db.models import Intervention
from drishti.db.session import session_scope
from drishti.rag.store import Chunk, get_store


@pytest.fixture(scope="module")
def chunk_id():
    c = Chunk("fixture", "Fixture Doc", "Sec 1", "1", 2, "fixture policy text for tests",
              embedding=np.ones(256, dtype=np.float32))
    get_store().upsert([c])
    return c.chunk_id


def test_requires_citation_for_real_actions():
    r = it.propose_intervention(1, "EMI_EXTENSION", "why", [])
    assert "citation" in r["error"]


def test_unknown_chunk_and_action_rejected(chunk_id):
    assert "unknown chunk_id" in it.propose_intervention(1, "EMI_EXTENSION", "why", ["nope"])["error"]
    assert "action_type" in it.propose_intervention(1, "WRITE_OFF", "why", [chunk_id])["error"]


def test_unknown_customer_rejected(chunk_id):
    assert "not found" in it.propose_intervention(987654, "COUNSELLING_REFERRAL", "why", [chunk_id])["error"]


def test_proposal_is_recorded_as_proposed_never_executed(chunk_id):
    r = it.propose_intervention(2, "COUNSELLING_REFERRAL", "two missed payments", [chunk_id])
    assert r["status"] == "proposed" and r["requires_human_approval"] is True
    assert r["citations"][0]["chunk_id"] == chunk_id
    with session_scope() as db:
        row = db.get(Intervention, r["intervention_id"])
        assert row.status == "proposed" and row.decided_by is None


def test_no_action_needs_no_citation():
    assert it.propose_intervention(5, "no_action", "low risk", [])["status"] == "proposed"


def test_risk_factors_summarise_delinquency():
    r = it.get_risk_factors(1)
    assert r["risk_segment"] == "CRITICAL" and any("delinquent in 4" in f for f in r["facts"])
    assert "error" in it.get_risk_factors(987654)
