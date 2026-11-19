import csv

from benchmarks import review_time as b


def _write(path, rows):
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, b.FIELDS)
        w.writeheader()
        w.writerows(rows)


def _rows(participants, manual=100.0, assisted=60.0):
    out = []
    for p in participants:
        for i in range(2):
            out.append(dict(participant=p, case_id=f"c{i}", customer_id=i, segment="HIGH", condition="manual", seconds=manual + i, decision="NO_ACTION"))
            out.append(dict(participant=p, case_id=f"d{i}", customer_id=i, segment="HIGH", condition="assisted", seconds=assisted + i, decision="NO_ACTION"))
    return out


def test_refuses_to_report_reduction_with_too_few_participants(tmp_path):
    _write(tmp_path / "t.csv", _rows(["a", "b"]))
    r = b.analyze(tmp_path / "t.csv", tmp_path / "none.csv")
    assert r["reduction_pct"] is None and "at least 3" in r["note"]


def test_reports_reduction_with_ci_when_enough_participants(tmp_path):
    _write(tmp_path / "t.csv", _rows(["a", "b", "c", "d"]))
    r = b.analyze(tmp_path / "t.csv", tmp_path / "none.csv")
    assert 38 < r["reduction_pct"]["median_of_participants"] < 42
    lo, hi = r["reduction_pct"]["ci95"]
    assert lo <= r["reduction_pct"]["median_of_participants"] <= hi


def test_decision_agreement_against_reference(tmp_path):
    _write(tmp_path / "t.csv", _rows(["a", "b", "c"]))
    (tmp_path / "ref.csv").write_text("case_id,decision\nc0,NO_ACTION\nd0,COUNSELLING_REFERRAL\n")
    r = b.analyze(tmp_path / "t.csv", tmp_path / "ref.csv")
    assert r["decision_agreement"] == {"manual": 1.0, "assisted": 0.0}


def test_conditions_are_counterbalanced_and_reproducible():
    cases = [{"case_id": f"x{i}", "customer_id": i, "segment": "LOW"} for i in range(6)]
    a = b.assign_conditions("p1", cases)
    assert [c["condition"] for c in a].count("manual") == 3
    assert a == b.assign_conditions("p1", cases)


def test_pick_cases_is_stratified_and_deterministic():
    c1, c2 = b.pick_cases(4), b.pick_cases(4)
    assert c1 == c2 and len(c1) <= 4
