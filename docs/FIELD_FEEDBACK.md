# Field feedback: feature requests and reusable modules

Things that came up while building this, written the way they would go back to a product or platform team. Each item says what happened, not just what is wanted.

## Feature requests for the platform (Google ADK / Vertex AI / Cloud)

| # | Observation (what actually happened) | Request |
|---|---|---|
| 1 | `AgentTool` runs the sub-agent in a **child session**, so the parent's event stream never contains the sub-agent's tool calls/responses. A verifier reading only parent events had no evidence to check, and a test caught it. | Surface child tool calls/results on the parent run (or document the supported pattern). We worked around it with a plugin + `ContextVar`. |
| 2 | Session-keyed metrics don't work for the same reason: the child session id differs from the request's. | A stable request/invocation id propagated to child runs for metrics correlation. |
| 3 | `DatabaseSessionService` fails at first use with an `ImportError` unless the `[db]` extra is installed. | Declare it in the base error path with the exact install hint (it does), and ship it in the default Postgres deployment docs. |
| 4 | `Runner(plugins=...)` is deprecated in favour of `App(...)`; examples online still use the old form. | Keep migration notes next to the API change. |
| 5 | Pricing differs between the Gemini Developer API page and Vertex AI, and the Vertex page is JS-rendered. Cost-per-request tooling can't scrape it. | A machine-readable pricing endpoint/JSON per model and region, with an effective date. |
| 6 | No embedding-model price was retrievable alongside model prices. | Same pricing feed should include embeddings. |
| 7 | RBI's document host (`rbidocs.rbi.org.in`) returns an HTML bot-check page for scripted PDF downloads, but the same directions are published as full text on `rbi.org.in` pages. (Not a Google issue, but a real onboarding friction.) | For regulated-document RAG, first-class HTML-source ingestion with provenance (URL, date, hash) next to the "bring your own PDFs" path. Both are built here (`ingest fetch`, `ingest run`). |
| 8 | An LLM-reranker call per candidate is slow and costly at k=20; a lexical reranker already lifted recall@5 from 0.765 to 0.824 on our questions. | A managed reranking API (Vertex AI Ranking) as a drop-in for the `Reranker` interface, with per-call cost in the metrics. |

## Product observations about this use case

* **Precision claims need an operating point.** On the public dataset the model's precision at the F1-optimal threshold is ~0.50 with recall ~0.61; at a very strict threshold precision rises to 0.90 but only 50 of 6,000 customers are flagged (recall 0.03). A bare "precision" number hides this. Dashboards should show the precision/recall trade-off and let the business pick the threshold.
* **"Not covered by policy" must be a first-class answer.** Analysts trust the tool more when it says the corpus does not address something than when it produces a plausible clause. It is in the golden set as an expected behaviour.
* **Human approval is a feature, not a limitation.** Compliance stakeholders asked for it first in every lending framing we reviewed. The `proposed → approved/rejected` log doubles as training signal for later ranking.

## What worked, for the next engagement

* **Scraped regulatory text needs tests for its own junk**: footers, entities and table-of-contents lines each leaked into the first ingest and were only caught by tests that asserted on the real corpus.
* **Offline-first evaluation**: retrieval, guardrail and injection metrics need no LLM, so they run in CI on every PR and gate regressions before any model cost is incurred.
* **Make the missing input a drop-in file**: a `secrets/` folder plus `make doctor` turned "I need credentials" into one obvious step.

## Reusable modules (extractable as-is)

| Module | Where | Reuse |
|---|---|---|
| **Policy-RAG kit**: PDF parse → structure-aware chunk → embed → store (idempotent), hybrid search with RRF, pluggable reranker, citation-bearing results | `ingest/`, `drishti/rag/` | Any regulated domain with numbered clauses: insurance, healthcare compliance, tax, telecom. Only the heading regexes in `ingest/chunk.py` are domain-tuned |
| **Allowlisted SQL tool pattern**: named parameterised queries, type/range validation, row caps, read-only engine, hidden ground-truth columns | `drishti/agents/tools/sql_tools.py` | Safe analytics for any agent that must not write or free-form query production data |
| **Guardrail + verifier stage**: input patterns, injection scrubbing, citation-vs-evidence check, number-provenance check, PII masking | `drishti/agents/guardrails.py`, `verifier.py`, `obs/pii.py` | Drop-in post-processing for any tool-using agent |
| **Agent metrics plugin**: tokens, tokens/sec, latency, cost from a dated pricing table, steps, tool calls | `drishti/obs/metrics.py` | Per-request LLM economics for any ADK app |
| **Eval harness**: golden set with oracle SQL, retrieval recall@k/MRR, baseline-vs-final ablation, generated report, regression gate | `evals/` | Template for regression-gating agent changes in CI |
| **Corpus fetcher with provenance**: fetch → extract → refuse stubs → record URL/date/hash → regenerate SOURCES.md | `ingest/fetch.py` | Any public-document corpus that must be citable and re-verifiable |
| **Timed A/B benchmark harness** (counterbalanced, bootstrap CI, refuses small n) | `benchmarks/` | Honest "time saved" claims for any assistive tool |
| **Human-approval ledger**: proposed/approved/rejected with attribution | `drishti/db/models.py`, `api/main.py` | Any "AI proposes, human disposes" workflow |
