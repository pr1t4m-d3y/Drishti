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
| 7 | RBI's document server returns an HTML bot-check page for scripted PDF downloads. (Not a Google issue, but a real onboarding friction.) | For regulated-document RAG, a documented "bring your own PDFs" flow with checksum manifest. We built one (`data/policies/SOURCES.md` + ingest manifest). |

## Product observations about this use case

* **Precision claims need an operating point.** On the public dataset the model's precision at the F1-optimal threshold is ~0.50 with recall ~0.61; at a very strict threshold precision rises to 0.90 but only 50 of 6,000 customers are flagged (recall 0.03). A bare "precision" number hides this. Dashboards should show the precision/recall trade-off and let the business pick the threshold.
* **"Not covered by policy" must be a first-class answer.** Analysts trust the tool more when it says the corpus does not address something than when it produces a plausible clause. It is in the golden set as an expected behaviour.
* **Human approval is a feature, not a limitation.** Compliance stakeholders asked for it first in every lending framing we reviewed. The `proposed → approved/rejected` log doubles as training signal for later ranking.

## Reusable modules (extractable as-is)

| Module | Where | Reuse |
|---|---|---|
| **Policy-RAG kit**: PDF parse → structure-aware chunk → embed → store (idempotent), hybrid search with RRF, pluggable reranker, citation-bearing results | `ingest/`, `drishti/rag/` | Any regulated domain with numbered clauses: insurance, healthcare compliance, tax, telecom. Only the heading regexes in `ingest/chunk.py` are domain-tuned |
| **Allowlisted SQL tool pattern**: named parameterised queries, type/range validation, row caps, read-only engine, hidden ground-truth columns | `drishti/agents/tools/sql_tools.py` | Safe analytics for any agent that must not write or free-form query production data |
| **Guardrail + verifier stage**: input patterns, injection scrubbing, citation-vs-evidence check, number-provenance check, PII masking | `drishti/agents/guardrails.py`, `verifier.py`, `obs/pii.py` | Drop-in post-processing for any tool-using agent |
| **Agent metrics plugin**: tokens, tokens/sec, latency, cost from a dated pricing table, steps, tool calls | `drishti/obs/metrics.py` | Per-request LLM economics for any ADK app |
| **Eval harness**: golden set with oracle SQL, retrieval recall@k/MRR, baseline-vs-final ablation, generated report, regression gate | `evals/` | Template for regression-gating agent changes in CI |
| **Human-approval ledger**: proposed/approved/rejected with attribution | `drishti/db/models.py`, `api/main.py` | Any "AI proposes, human disposes" workflow |
