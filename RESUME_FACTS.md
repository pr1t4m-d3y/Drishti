# Resume facts (each one reproducible)

Only things that were actually measured or counted are listed. Measured 2026-11-19. If a number is weak I say so. Re-run the command before quoting a number in an interview.

## Verified facts

| Fact | Value | Proof (command / file) |
|---|---|---|
| Records in the dataset | **30,000** labelled card-holder records (UCI "Default of Credit Card Clients"), 0 missing values, 22.1% default rate | `python -m drishti.ml.train` → `models/metrics.json` → `data_quality` |
| Train / validation / test split | 18,000 / 6,000 / 6,000, stratified, seed 42 | `models/metrics.json` → `split` |
| Leakage controls | id excluded from features; scaling fit inside the pipeline on train only; the 13 duplicate feature rows across train/test are reported, not hidden | `models/metrics.json` → `train_test_duplicate_feature_rows`; `drishti/ml/train.py` |
| Model | Calibrated HistGradientBoosting, selected over a logistic-regression baseline by validation PR-AUC (0.543 vs 0.491); per-customer **TreeSHAP** explanations of the selected model | `models/metrics.json`; `drishti/ml/predict.py`; `tests/test_ml.py` |
| **Test precision / recall / F1 at the F1-optimal threshold** | **0.501 / 0.612 / 0.551** (ROC-AUC 0.790, PR-AUC 0.559) on 6,000 held-out customers | `models/metrics.json` → `test.at_max_f1_threshold`; `docs/images/precision_recall.png` |
| Test precision at a strict threshold | **0.90 precision, 0.034 recall** (50 customers flagged of 6,000) | `models/metrics.json` → `test.at_precision_target_0.80_on_validation` |
| Policy corpus | **5 real RBI directions, 810 chunks**, each chunk carrying chapter / topic / paragraph metadata; provenance (URL, fetch date, hash) recorded | `python -m ingest fetch && python -m ingest run && python -m ingest stats`; `data/policies/SOURCES.md` |
| Idempotent ingestion | Re-running skips unchanged documents; changed ones are replaced, never duplicated; vectors from a different embedder trigger a rebuild | `tests/test_ingest_retrieval.py::test_ingest_is_idempotent` |
| **Retrieval ablation** (17 policy questions, k = 5; hash embeddings + lexical reranker, i.e. a floor) | recall@5 **0.588 → 0.765 → 0.824** and MRR **0.392 → 0.649 → 0.698** for vector-only → hybrid (BM25 + RRF) → hybrid + rerank | `python -m evals.run --offline` → `evals/results/offline.json`, `RESULTS.md`. Relevance = chunk contains all topic keywords of the question (`gold_keywords`), a proxy, not human judgement |
| Golden evaluation set | **59 questions**: 20 SQL/data, 17 policy RAG, 8 intervention, 14 adversarial/safety | `python -m evals.build_golden_set`; `evals/golden_set.jsonl` |
| Oracle-checked SQL questions | 17 of 17 oracle queries execute against the real database | `evals/results/offline.json` → `oracle` |
| Input guardrails (deterministic, no LLM) | **12 of 13** adversarial prompts blocked before any model call (92.3%) | `evals/results/offline.json` → `guardrails` |
| Indirect prompt injection | Payload hidden in a retrieved document does **not** survive scrubbing (override marker and payload token both removed, legitimate text preserved) | `evals/results/offline.json` → `injection`; `tests/test_guardrails.py::test_poisoned_fixture_is_fully_neutralised` |
| Automated tests | **122 passing, 4 skipped** (the 4 need Postgres and run in CI); line coverage **77%** over `drishti/`, `ingest/`, `evals/`, `benchmarks/` | `make test` |
| Static checks | `ruff` clean, `mypy` clean on 52 files, `shellcheck` clean | `make lint typecheck`; `shellcheck -S warning scripts/*.sh deploy/*.sh` |
| Agents and tools | 4 LLM agents (orchestrator + risk-data, policy, intervention) + a verifier stage (deterministic + optional LLM verifier agent); 9 function tools (6 data, 1 policy search, 2 intervention) | `drishti/agents/system.py`, `drishti/agents/tools/` |
| Safe data access | Agent SQL = 7 named, parameterised queries on a read-only connection; ground-truth label never selectable. Postgres role grants verified by test (runs in CI) | `tests/test_sql_allowlist.py`; `migrations/003_readonly_role.sql`; `tests/test_store_contract.py` |
| Human-in-the-loop | Agent write tool only inserts `proposed`; approval needs a *different* authenticated person (API + DB `CHECK`) | `tests/test_api.py::test_four_eyes_rule_blocks_self_approval`; `migrations/001_core_schema.sql` |
| Observability | OpenTelemetry spans (agents, tools, retrieval, HTTP) with PII-masking exporter; JSON logs; per-request tokens, tokens/s, latency, cost from a dated pricing table | `drishti/obs/`; `tests/test_agent_routing.py` (metrics asserted with a scripted LLM) |
| Infrastructure as code | Terraform (Cloud Run, Cloud SQL, Secret Manager, Artifact Registry, IAM, budget), SQL migrations kept in sync with ORM models by a test, Dockerfile, 5 GitHub Actions jobs + manual eval and deploy workflows | `deploy/terraform/`, `migrations/`, `.github/workflows/`, `tests/test_terraform.py`, `tests/test_migrations.py` |
| Review-time benchmark | Harness implemented and tested; refuses to report a reduction with fewer than 3 participants | `benchmarks/`, `tests/test_benchmark.py` |
| Python code size | ~6,000 lines across `drishti/`, `ingest/`, `evals/`, `benchmarks/`, `ui/`, `tests/` | `find drishti ingest evals benchmarks ui tests -name '*.py' \| xargs wc -l` |

## Not yet measured (do **not** put these on a resume)

| Item | Why | How to get it |
|---|---|---|
| Accuracy before → after (baseline vs final), end-to-end safety pass rate, groundedness, citation precision, judge scores | Needs an LLM key | Add the key to `secrets/.env`, `make all` (or run the **eval** GitHub Action) → `evals/results/RESULTS.md` |
| Retrieval with Gemini embeddings + Gemini reranker | Same | Same |
| Latency p50/p95, tokens/sec, cost per request | Needs real model calls | Same, or `GET /admin/metrics` after real usage |
| Cloud Run URL, Cloud SQL + pgvector in the cloud, trace screenshot | Not deployed | `deploy/terraform/README.md` |
| Review-time reduction ("35%") | No measurement exists | Run `benchmarks/` with real analysts, or drop the claim |
| Reference answers for the 17 policy questions | Drafted by the LLM from retrieved RBI text, then must be reviewed by a human | `make drafts`, then `python -m evals.draft_references --approve ...` |

## Things to correct on the resume

* "94%+ precision": **not reproducible**. Measured on a public dataset: ~0.50 precision at the balanced operating point, 0.90 at 3.4% recall. Quote the operating point, not a bare percentage.
* "10,000+ financial records": the upgraded project uses 30,000 real, public records; the original repo had 1,000 synthetic ones.
* "Automatically executes restructuring": the system now **recommends and a second human approves**. Reword to "recommends policy-cited actions for human approval".
* "35% faster review": no measurement; reword or run the benchmark.
