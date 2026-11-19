# Drishti roadmap and vision

The single place for where Drishti is heading and everything that still has to be built or measured. Work through it one
item at a time; tick items off here as they land. The README never needs to change: its numbers are read live from
`models/metrics.json` and the evaluation results files.

## Vision

A lender's risk team should see trouble coming weeks earlier, understand *why* in plain language, and know exactly what
they are allowed to offer the customer, with the regulator's own words attached and a second person signing off. Drishti
aims to be that early-warning and decision-support layer: a calibrated risk model, an agent team that reasons over the
customer's data and the lending directions, and an audit trail for every recommendation.

## Where things stand

Working today: model training and calibration, SHAP explanations, an import path for externally trained models, the
FastAPI service, the agent team and verifier, hybrid retrieval over RBI directions, human approvals with four-eyes,
tracing and metrics code, the evaluation harness, Docker, Terraform and CI. Current measured numbers are always in
[`models/metrics.json`](../models/metrics.json) and [`evals/results/RESULTS.md`](../evals/results/RESULTS.md).

## Roadmap

Each item says what it needs and when it counts as done.

### 1. Model (owner: ML collaborator)

| Item | Needs | Done when |
|---|---|---|
| XGBoost training notebook | The collaborator's notebook or exported model in `models/incoming/` | `python -m drishti.ml.import_model --load` passes the contract and `models/metrics.json` shows the imported model |
| Feature engineering round 2 | New features added in `drishti/ml/data.py::add_features` | Held-out PR-AUC beats the current model on the same split |
| Cost-based threshold policy | Agreed cost of a missed defaulter vs a wrongly flagged customer | The risk segments (currently 0.60 / 0.40 / 0.25) are derived from that cost, not fixed by hand |
| Fairness and subgroup review | Decision on which attributes to audit (age, sex, education, marriage) | Per-subgroup precision/recall table committed; protected attributes reviewed for removal |
| Leakage check on every imported model | Nothing extra | Importer reports duplicate-row overlap and rejects suspicious results. Treat any accuracy well above the majority-class baseline of about 78% on this dataset (for example in the 90s) as a leakage warning until proven otherwise |
| Retraining job and drift monitoring | A schedule and a stored score history | Weekly retrain candidate, PSI drift report, promotion only if held-out metrics improve |
| Model registry and serving | GCP project | Model registered in Vertex AI Model Registry and served from an endpoint, with the API calling it |
| Real portfolio data | A lender's data under agreement | Retrained and re-evaluated on the real book |

Model targets, measured on the held-out split and recorded in `models/metrics.json`: ROC-AUC at or above the current
model, recall at the chosen operating point at or above the current model with precision not lower, and a documented
precision/recall trade-off curve.

### 2. AI, retrieval and agents

| Item | Needs | Done when |
|---|---|---|
| Live end-to-end evaluation, baseline vs final | Gemini key in `secrets/.env` | `evals/results/RESULTS.md` has accuracy, groundedness, citation precision, safety, p50/p95 latency, tokens/sec and cost per request for both variants |
| Gemini embeddings and reranker | Gemini key | Corpus re-ingested with Gemini embeddings; recall@5 and MRR re-measured and compared with the offline numbers |
| Reference answers for policy questions | Gemini key, then human review | Every `needs_review` item in `evals/golden_set.jsonl` is `reviewed` (`make drafts`, then `--approve`) |
| Larger and harder golden set | Domain review | At least 150 questions, including multi-turn and ambiguous-policy cases, with an over-refusal section |
| More policy sources | RBI texts saved to `data/policies/` | Integrated Ombudsman scheme, customer-protection and recovery directions ingested with provenance |
| MCP server | Nothing external | The SQL and policy tools are exposed through a Model Context Protocol server and used by an external client in a test |
| Agent hosting | GCP project | The ADK agents run on Vertex AI Agent Engine as an alternative to the Cloud Run container |
| Indirect-injection suite | Nothing external | Several poisoned documents covering different attack styles, all neutralised, run on every PR |

### 3. Data platform

| Item | Needs | Done when |
|---|---|---|
| Cloud Storage ingestion | GCP project | A file landing in a bucket triggers ingestion; manifest and provenance recorded |
| BigQuery | GCP project | Scored customers and request metrics exported to BigQuery; an analytics view and a dashboard on top |
| Document AI / OCR | GCP project | Scanned circulars ingested with layout-aware parsing |
| Postgres full-text search | Nothing external | BM25 side of hybrid search runs in Postgres (`tsvector` index already in the migrations) for corpora too large for memory |
| Sensitive Data Protection (DLP) | GCP project | Regex masking supplemented or replaced by DLP inspection |

### 4. Platform and operations

| Item | Needs | Done when |
|---|---|---|
| First cloud deployment | GCP project id, region, billing account | `deploy/terraform` applied, Cloud Run URL live, `make smoke` passes, budget alert active |
| Monitoring | Deployment | Cloud Monitoring dashboard for latency, errors, tokens and cost; alerts and SLOs defined |
| Private networking | Deployment | Cloud SQL on a private IP with a serverless VPC connector |
| Continuous deployment | Deployment | Merge to `main` deploys behind the manual approval gate |
| Trace review | Deployment | A real end-to-end trace (orchestrator, sub-agents, tools, retrieval) viewed in Cloud Trace and documented |

### 5. Product and interface

| Item | Needs | Done when |
|---|---|---|
| React dashboard on the real data | Design decision | The v1 pages read customers, risk and interventions from the FastAPI service instead of their own backend |
| Approvals inbox | Nothing external | Pending recommendations grouped by customer with filters, bulk review and an audit view |
| Role-based access | Identity provider | Analyst, approver and admin roles enforced in the API and the UI |
| Screenshots and a short screen recording | A running stack with a Gemini key | Added to the repository and linked from the README |
| Analyst-facing explanations | Nothing external | SHAP drivers shown in plain language next to each score |

### 6. Measurement

| Item | Needs | Done when |
|---|---|---|
| Review-time benchmark | At least 3 analysts | `python -m benchmarks.review_time analyze` reports the time difference with a confidence interval and decision agreement |
| Production-style backtest | Time-ordered historical data | Out-of-time precision, recall and calibration reported |

## Known limitations

* The current model is trained on a public dataset (Taiwan, 2005), not a lender's portfolio.
* Customer scores in the loaded database include rows the model trained on; evaluation uses the held-out split only.
* Without credentials the app uses an offline embedder and lexical reranker; retrieval numbers improve with Gemini.
* The pgvector store, migrations, Docker image and Terraform are verified in CI, not yet in a live cloud project.
* The v1 React pages use synthetic data from their own Express backend until item 5 above is done.
