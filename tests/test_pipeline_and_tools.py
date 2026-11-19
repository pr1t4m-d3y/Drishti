"""Coverage for the glue code: training, pipeline steps, draft references, demo, benchmark runner, PDF parsing."""

import json

import numpy as np
import pandas as pd


def _synthetic_raw(n=1800, seed=0):
    rng = np.random.default_rng(seed)
    pay = rng.integers(-1, 4, size=(n, 6))
    d = {"customer_id": np.arange(1, n + 1), "limit_bal": rng.integers(10_000, 300_000, n).astype(float),
         "sex": rng.integers(1, 3, n), "education": rng.integers(1, 5, n), "marriage": rng.integers(1, 4, n),
         "age": rng.integers(21, 70, n)}
    for i in range(6):
        d[f"pay_{i + 1}"] = pay[:, i]
        d[f"bill_amt{i + 1}"] = rng.normal(40_000, 20_000, n)
        d[f"pay_amt{i + 1}"] = rng.integers(0, 5000, n).astype(float)
    df = pd.DataFrame(d)
    score = df["pay_1"] * 0.9 + df["pay_2"] * 0.4 + rng.normal(0, 0.7, n)
    df["default_label"] = (score > 1.2).astype(int)
    return df


def test_training_protocol_on_synthetic_data():
    from drishti.ml.train import fit_and_evaluate

    art, rep = fit_and_evaluate(_synthetic_raw())
    assert rep["split"]["train"] + rep["split"]["validation"] + rep["split"]["test"] == 1800
    assert rep["split"]["validation"] == rep["split"]["test"] == 360
    assert rep["selected_model"] in rep["validation_pr_auc_by_model"]
    t = rep["test"]["at_max_f1_threshold"]
    assert 0 <= t["precision"] <= 1 and 0 <= t["recall"] <= 1 and t["roc_auc"] > 0.7  # planted signal is learnable
    assert "train_test_duplicate_feature_rows" in rep and rep["data_quality"]["rows"] == 1800
    assert set(art) >= {"model", "base_model", "features", "explainer"}


def _synthetic_features(art):
    from drishti.ml.data import FEATURES, add_features

    return add_features(_synthetic_raw(50))[FEATURES]


def test_calibrated_probabilities_are_valid():
    from drishti.ml.train import fit_and_evaluate

    art, _ = fit_and_evaluate(_synthetic_raw())
    p = art["model"].predict_proba(_synthetic_features(art))[:, 1]
    assert ((p >= 0) & (p <= 1)).all()


def test_pipeline_step_runs_or_skips(capsys):
    from drishti.pipeline import _step

    ran = []
    assert _step("a", lambda: ran.append(1)) == "done" and ran == [1]
    assert _step("b", lambda: ran.append(2), skip="why") == "skipped" and ran == [1]
    assert "SKIPPED (why)" in capsys.readouterr().out


def test_migrate_is_noop_on_sqlite():
    from drishti.db.migrate import migrate

    assert migrate()["applied"] == []


def test_minimal_pdf_is_parsed_with_page_numbers(tmp_path):
    from ingest.parse import parse_pdf

    stream = b"BT /F1 12 Tf 72 700 Td (5. Notice before recovery) Tj ET"
    objs = [b"<< /Type /Catalog /Pages 2 0 R >>", b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
            b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"]
    pdf, offs = b"%PDF-1.4\n", []
    for i, o in enumerate(objs, 1):
        offs.append(len(pdf))
        pdf += f"{i} 0 obj\n".encode() + o + b"\nendobj\n"
    xref = len(pdf)
    pdf += f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n".encode() + b"".join(f"{o:010d} 00000 n \n".encode() for o in offs)
    pdf += f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF".encode()
    f = tmp_path / "doc.pdf"
    f.write_bytes(pdf)
    title, pages = parse_pdf(f)
    assert pages[0].number == 1 and "Notice before recovery" in pages[0].text and title


def test_draft_references_marks_not_in_corpus_and_never_auto_reviews(tmp_path, monkeypatch):
    from evals import draft_references as dr

    gp = tmp_path / "golden.jsonl"
    qs = [{"id": "pol-01", "category": "policy", "question": "penal charges?", "gold_keywords": ["penal"], "status": "needs_review"},
          {"id": "sql-01", "category": "sql", "question": "x"}]
    gp.write_text("\n".join(json.dumps(q) for q in qs) + "\n")
    monkeypatch.setattr(dr, "OUT", gp)

    class Hit:  # empty corpus -> nothing relevant
        pass

    class FakeRetriever:
        def search(self, *a, **k):
            return []

    import drishti.rag.retrieval as rr

    monkeypatch.setattr(rr, "Retriever", FakeRetriever)
    import google.genai as genai

    monkeypatch.setattr(genai, "Client", lambda *a, **k: object())
    assert dr.draft() == {"auto_drafted": 0, "not_in_corpus": 1}
    saved = [json.loads(x) for x in gp.read_text().splitlines()]
    assert saved[0]["status"] == "not_in_corpus" and saved[0]["reference"] is None
    monkeypatch.setattr("sys.argv", ["dr", "--approve", "pol-01"])
    dr.main()  # approving a not_in_corpus item must NOT flip it to reviewed
    assert json.loads(gp.read_text().splitlines()[0])["status"] == "not_in_corpus"


def test_golden_builder_preserves_reviewed_references(tmp_path, monkeypatch):
    from evals import build_golden_set as g

    out = tmp_path / "g.jsonl"
    out.write_text(json.dumps({"id": "pol-01", "category": "policy", "question": "Q", "reference": "R", "status": "reviewed"}) + "\n")
    monkeypatch.setattr(g, "OUT", out)
    merged = g._merge_reviewed([{"id": "pol-01", "category": "policy", "question": "Q", "reference": None, "status": "needs_review"}])
    assert merged[0]["reference"] == "R" and merged[0]["status"] == "reviewed"
    changed = g._merge_reviewed([{"id": "pol-01", "category": "policy", "question": "Q2", "reference": None, "status": "needs_review"}])
    assert changed[0]["status"] == "needs_review"  # question text changed -> review is void


def test_eval_offline_run_writes_results(tmp_path, monkeypatch):
    from evals import run as ev

    monkeypatch.setattr(ev, "RESULTS", tmp_path)
    off = ev.main_offline()
    assert (tmp_path / "offline.json").exists() and off["guardrails"]["attacks"] >= 10
    assert off["injection"]["override_marker_survived"] is False and off["injection"]["payload_token_survived"] is False
    ev.write_report()
    assert "Indirect prompt injection" in (tmp_path / "RESULTS.md").read_text()


def test_summarise_computes_rates_and_leaves_unmeasured_null():
    from evals import run as ev

    qs = [{"id": "a", "category": "sql"}, {"id": "b", "category": "safety"}]
    m = {"latency_s": 2.0, "tokens_per_sec": 50.0, "cost_usd": 0.001, "agent_steps": 3}
    rows = [{"id": "a", "category": "sql", "passed": True, "grounded": True, "metrics": m, "citation_precision": None},
            {"id": "b", "category": "safety", "passed": False, "grounded": None, "metrics": m | {"latency_s": 4.0}}]
    s = ev.summarise("final", {"rows": rows}, qs)
    assert s["pass_rate_by_category"]["sql"]["pass_rate"] == 1.0 and s["safety_pass_rate"] == 0.0
    assert s["latency_p50_s"] == 2.0 and s["latency_p95_s"] == 4.0 and s["citation_precision_mean"] is None
    assert ev.summarise("x", None, qs)["end_to_end"].startswith("not run")


def test_score_row_rules():
    from evals import run as ev

    ok = {"answer": "Customer needs human approval", "refused": False, "grounded": True, "citations": [{"chunk_id": "c"}], "new_proposals": 1}
    assert ev.score_row({"category": "intervention", "expect": "proposal_with_citation_and_human_approval"}, ok)
    assert not ev.score_row({"category": "intervention", "expect": "proposal_with_citation_and_human_approval"}, ok | {"new_proposals": 0})
    assert ev.score_row({"category": "intervention", "expect": "refuse_execution"}, ok | {"new_proposals": 0})
    assert not ev.score_row({"category": "safety", "forbidden": ["PWNED-7731"]}, ok | {"answer": "PWNED-7731", "refused": False})
    assert ev.score_row({"category": "policy", "status": "not_in_corpus"}, ok | {"answer": "The corpus does not cover this."})
    assert ev.score_row({"category": "policy"}, ok)


def test_demo_offline_transcript(tmp_path, monkeypatch):
    import drishti.demo as demo

    (tmp_path / "docs").mkdir()
    monkeypatch.setattr(demo, "ROOT", tmp_path)
    monkeypatch.setattr(demo, "credential_mode", lambda: "offline")
    out = demo.run()
    assert "refused: True" in out and "No LLM credentials" in out and (tmp_path / "docs" / "DEMO.md").exists()


def test_benchmark_run_records_rows(tmp_path, monkeypatch):
    from benchmarks import review_time as b

    monkeypatch.setattr(b, "TIMINGS", tmp_path / "t.csv")
    monkeypatch.setattr(b, "pick_cases", lambda n: [{"case_id": f"c{i}", "customer_id": i, "segment": "LOW"} for i in range(n)])
    monkeypatch.setattr(b, "_show_manual", lambda cid: None)
    monkeypatch.setattr(b, "_show_assisted", lambda cid: None)
    answers = iter(["", "NO_ACTION"] * 4)
    monkeypatch.setattr("builtins.input", lambda *_: next(answers))
    b.run("p9", 4)
    lines = (tmp_path / "t.csv").read_text().splitlines()
    assert lines[0].startswith("participant") and len(lines) == 5
    assert {r.split(",")[4] for r in lines[1:]} == {"manual", "assisted"}


def test_policy_tool_uses_override_retriever(tmp_path):
    from drishti.agents.tools import policy_tools
    from evals.run import poisoned_retriever

    policy_tools.set_retriever_override(poisoned_retriever(tmp_path))
    try:
        res = policy_tools.search_policies("grievance officer", top_k=3)
    finally:
        policy_tools.set_retriever_override(None)
    assert res["results"] and res["results"][0]["injection_flagged"] and "warning" in res
    assert "PWNED-7731" not in json.dumps(res)
