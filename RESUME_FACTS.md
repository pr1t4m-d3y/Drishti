# Resume facts (each one reproducible)

Only things that were actually measured or counted are listed. Dates are when they were measured (2026-11-19). If a number is weak I say so. Re-run the command before quoting a number in an interview.

## Verified facts

| Fact | Value | Proof (command / file) |
|---|---|---|
| Records in the dataset | **30,000** labelled card-holder records (UCI "Default of Credit Card Clients"), 0 missing values, 22.1% default rate | `python -m drishti.ml.train` → `models/metrics.json` → `data_quality` |
| Train / validation / test split | 18,000 / 6,000 / 6,000, stratified, seed 42 | `models/metrics.json` → `split` |
| Leakage checks | id excluded from features; scaling fit inside the pipeline on train only; 13 duplicate feature rows across train/test are reported, not hidden | `models/metrics.json` → `train_test_duplicate_feature_rows`; `drishti/ml/train.py` |
| Model | Calibrated HistGradientBoosting, selected over a logistic-regression baseline by validation PR-AUC (0.543 vs 0.491) | `models/metrics.json` → `validation_pr_auc_by_model` |
| **Test precision / recall / F1 at the F1-optimal threshold** | **0.501 / 0.612 / 0.551** (ROC-AUC 0.790, PR-AUC 0.559) on 6,000 held-out customers | `models/metrics.json` → `test.at_max_f1_threshold` |
| Test precision at a strict threshold | **0.90 precision, 0.034 recall** (50 customers flagged of 6,000, i.e. about 45 correct) | `models/metrics.json` → `test.at_precision_target_0.80_on_validation` |
| Golden evaluation set | **59 questions**: 20 SQL/data, 17 policy RAG, 8 intervention, 14 adversarial/safety | `python -m evals.build_golden_set`; `evals/golden_set.jsonl` |
| Oracle-checked SQL questions | 17 of 17 oracle queries execute against the real database | `python -m evals.run --offline` → `evals/results/offline.json` → `oracle` |
| Input guardrails (deterministic, no LLM) | **12 of 13** adversarial prompts blocked before any model call (92.3%) | `python -m evals.run --offline` → `guardrails` |
| Automated tests | **66 passing**, line coverage **73%** over `drishti/`, `ingest/`, `evals/` | `make test` |
| Static checks | `ruff` clean, `mypy` clean on 35 source files | `make lint typecheck` |
| Agents and tools | 4 LLM agents (orchestrator + risk-data, policy, intervention specialists) + a verifier stage (deterministic, plus an optional LLM verifier agent); 9 function tools (6 data, 1 policy search, 2 intervention) | `drishti/agents/system.py`, `drishti/agents/tools/` |
| Read-only data access | Agent SQL runs through 7 named, parameterised queries on a read-only connection; the ground-truth label column is never selectable | `tests/test_sql_allowlist.py`, `migrations/003_readonly_role.sql` |
| Human-in-the-loop | The only write tool inserts `proposed` interventions; approval needs an authenticated decision endpoint | `tests/test_intervention_tools.py`, `tests/test_api.py` |
| Python code size | ~3,900 lines across `drishti/`, `ingest/`, `evals/`, `ui/`, `tests/` | `find drishti ingest evals ui tests -name '*.py' \| xargs wc -l` |

## Not yet measured (do **not** put these on a resume)

| Item | Why | How to get it |
|---|---|---|
| Accuracy before → after (baseline vs final), safety pass rate end to end, groundedness, judge scores | Needs Vertex AI credentials | `make eval` → `evals/results/RESULTS.md` |
| recall@k / MRR for hybrid + rerank vs vector-only | No policy PDFs ingested yet | Add the RBI PDFs (`data/policies/SOURCES.md`), `make ingest`, `make eval-offline` |
| Latency p50/p95, tokens/sec, cost per request | Needs real model calls | `make eval`, or `GET /admin/metrics` after real usage |
| Number of policy documents / chunks | Zero PDFs present | After `make ingest`: `python -m ingest stats` |
| Cloud Run URL, Cloud SQL + pgvector running | Not deployed | `deploy/README.md` |
| Review-time reduction ("35%") | No measurement exists | Timed manual-vs-assisted benchmark with real analysts, or drop the claim |

## Things to correct on the resume

* "94%+ precision": **not reproducible** on any data in this repository. Measured on a public dataset: ~0.50 precision at the balanced operating point, 0.90 at 3.4% recall. Quote the operating point, not a bare percentage.
* "10,000+ financial records": the upgraded project uses 30,000 real, public records; the original repo had 1,000 synthetic ones.
* "Automatically executes restructuring": the system now **recommends and a human approves**. Reword to "recommends policy-cited actions for human approval".
* "35% faster review": no measurement; reword or measure.
