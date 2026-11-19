# Project status (internal working notes)

Kept here, not in the README, so the README does not need to change as work lands. Update this file as items are done.

## Built and checked
* Model training, calibration, SHAP, import contract for external models; API; agents (with a scripted LLM in tests);
  retrieval and ingestion over the RBI corpus; evals harness; Terraform, Docker, CI (green on `main`).
* Offline evaluation results are in `evals/results/` and regenerate with `make eval-offline`.

## Pending
| Item | Needs | Command / where |
|---|---|---|
| End-to-end baseline vs final results (accuracy, groundedness, safety, latency, tokens/sec, cost) | Gemini key in `secrets/.env` | `make eval` or the **eval** workflow -> `evals/results/RESULTS.md` |
| Re-ingest with Gemini embeddings and measure the Gemini reranker | Gemini key | `make ingest`, `make eval-offline` |
| Reference answers for policy questions (`needs_review` in `evals/golden_set.jsonl`) | Gemini key + human review | `make drafts`, then `python -m evals.draft_references --approve ID` |
| Cloud deployment, URL, budget alert, trace screenshot | GCP project id and region | `deploy/terraform/README.md` |
| Review-time benchmark | 3+ participants | `benchmarks/README.md` |
| Notebook XGBoost model from the ML collaborator | the notebook / exported model | `docs/MODEL_CONTRACT.md` |
| UI screenshots / GIF | running UI + Gemini key for chat | |
| Optional additions | GCS ingestion, BigQuery export, MCP server, Vertex AI Model Registry, Cloud DLP, Cloud Monitoring dashboards | |

## Known limitations
* Public dataset (Taiwan, 2005); retrain on the target lender's data before real use.
* Customer scores in the loaded database include rows the model trained on; evaluation uses the held-out split only.
* Offline embedder and lexical reranker are the defaults without credentials; retrieval numbers improve with Gemini.
* The pgvector store, migrations, Docker image and Terraform are verified in CI, not on a laptop.
* The v1 React pages use synthetic data from their own Express backend.
