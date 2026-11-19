# Technical discovery: credit early-warning and intervention copilot

> **Status of this document.** This is a discovery write-up prepared the way a forward-deployed engineer
> would prepare it *before* a client workshop. There is no real bank behind it: stakeholders, workflow
> and pain points below are **hypotheses drawn from public material and common lending operations**, each
> marked with a question to confirm in the room. Nothing here is a measured fact about a real
> institution.

## 1. Problem statement (hypothesis)

Collections and risk teams at retail lenders see delinquency late. By the time an account is 30+ days past due, options narrow, costs rise and the customer relationship suffers. Analysts spend time pulling data from several systems, then looking up what policy allows before deciding on an outreach, a counselling referral or a restructuring review.

**Opportunity**: surface at-risk accounts *earlier*, explain why, and propose the policy-compliant next step with its citation, while keeping a human accountable for every action.

## 2. Stakeholders and what each needs

| Stakeholder | Pain point (hypothesis) | What they need from us | Confirm by asking |
|---|---|---|---|
| Head of Collections / Credit Risk | Late visibility; inconsistent treatment across analysts | Ranked early-warning list with reasons; consistent, policy-cited recommendations | "How many accounts per analyst per day, and how are they prioritised today?" |
| Risk analysts / collections officers | Swivel-chair between systems; hunting through circulars | One place to ask a question and get a cited answer | "Walk me through the last restructuring request you handled." |
| Compliance / Legal | Fear of non-compliant outreach; need audit trail | Every recommendation cites a clause; nothing executes without approval; immutable log | "What evidence do auditors ask for after a customer complaint?" |
| Customer Experience / Grievance cell | Complaints about aggressive recovery | Early, empathetic interventions (counselling, reminders) | "What share of complaints come from recovery contact?" |
| Information Security / Data Protection | PII leaving the perimeter; third-party AI | PII masking, least privilege, regional processing, no training on their data | "Where must data reside? Is Vertex AI in-region acceptable?" |
| Data / ML platform team | Models without monitoring; handoffs | Reusable scoring service, drift hooks, evaluation harness | "What is the model-governance process for a new score?" |
| IT / Platform owner | Another system to run | Managed services, IaC, SSO via IAM / IAP | "Which identity provider, and what is the change-management process?" |

## 3. Current workflow (to validate)

1. Monthly batch or bureau feed flags delinquent accounts, often after the due date.
2. Analyst opens the core banking / LMS screen and a separate collections tool; pulls repayment history by hand.
3. Analyst searches the policy library / circulars (PDFs, intranet pages) to see what is permitted.
4. Analyst decides an action and records it in the collections system; a supervisor approves exceptions.
5. Customer is contacted; outcome logged weeks later.

Where time is probably lost (**to measure, not assume**): steps 2 and 3. The repository ships a benchmark plan, not a result: see "Success metrics".

## 4. Data sources and constraints

| Source | Content | Sensitivity | Notes |
|---|---|---|---|
| Loan / card account system | Limits, balances, repayment status, bills, payments | High (financial PII) | Read replica or nightly extract; no direct prod access |
| Bureau / alternative data | Scores, enquiries | High | Licensing limits on use; out of scope for phase 1 |
| Policy corpus | RBI directions, the bank's internal policies | Public / internal | Versioned; effective dates matter |
| Existing intervention log | Past actions and outcomes | Medium | Needed later to learn what actually works |

**Constraints that shape the design**

* **Compliance**: recommendations must trace to a specific clause; no automated adverse action; respect conduct rules on recovery contact. We cite, we do not interpret law: ambiguous cases route to Compliance.
* **PII**: pseudonymous customer ids only in prompts; PII masked in outputs, logs and traces; bulk-export requests refused.
* **Human approval**: every action is a *proposal*. Decisions are attributed to an authenticated person.
* **Residency / vendor**: Gemini on Vertex AI in the client's chosen region; data not used for training (to be confirmed contractually).
* **Auditability**: a trace id per request, retained inputs/outputs policy to be agreed with Compliance.

## 5. Success metrics

| Metric | Definition | How it will be measured | Target |
|---|---|---|---|
| Early-warning precision / recall | Share of flagged accounts that go delinquent; share of delinquents caught | Held-out, time-based backtest on the bank's own data | Set with the business after the baseline run (public-data baseline is in `models/metrics.json`) |
| Time-to-decision | Minutes from opening an account to a recorded decision | Timed benchmark of manual vs assisted review on a fixed set of cases with real analysts | **Not claimed until measured** |
| Answer accuracy | Golden-set pass rate by category | `make eval` | Floors in `evals/thresholds.json`, raised after first real run |
| Groundedness / citation precision | Answers whose claims are supported by cited passages | Verifier + judge rubric | Tracked, no unsupported policy claims shipped |
| Safety pass rate | Adversarial prompts refused / non-leaking | Adversarial section of the golden set | ≥ 0.90 floor, goal 1.0 on known classes |
| Latency / cost | p50, p95, cost per request | Per-request metrics | Agreed with the client's UX and budget |
| Human override rate | How often analysts reject proposals | `interventions.status` | Used to improve policy retrieval and prompts |

## 6. Risks and mitigations

| Risk | Likelihood / impact | Mitigation |
|---|---|---|
| Model precision lower than expected on the client's population | High / High | Backtest before promising anything; start with ranking support, not automation; monitor drift |
| LLM states a policy that does not exist | Medium / High | Retrieval-only answers, citation verification, "not covered" is a valid answer, human approval |
| Prompt injection via documents or tool output | Medium / High | Treat retrieved text as data, scrub, read-only tools, no execute path |
| Data leakage via logs/traces | Medium / High | PII masking at exporter and logger; PII-free metrics rows |
| Stale policy | Medium / Medium | Idempotent ingest with content hashes; effective-date metadata is a phase-2 item |
| Bias / fairness in scoring | Medium / High | Fairness review of features (e.g. age, sex are in the public dataset and would be excluded or audited in a real deployment); Compliance sign-off |
| Over-reliance by analysts | Medium / Medium | Show evidence and uncertainty; track override rate |
| Vendor / cost surprises | Low / Medium | Budget alerts, dated pricing table, min-instances 0, smallest Cloud SQL tier for pilot |

## 7. Phased rollout

| Phase | Scope | Exit criteria |
|---|---|---|
| **0. Discovery (2 weeks)** | Workshops, data access, policy inventory, define golden set with Compliance | Signed-off metrics and data-handling plan |
| **1. Shadow pilot (4-6 weeks)** | Scores and answers shown to a small analyst group alongside the old process; nothing acted on from the tool | Backtest precision/recall agreed; eval floors met; zero safety incidents |
| **2. Assisted decisions (6-8 weeks)** | Analysts approve/reject proposals in the tool; audit log live; timed benchmark vs baseline | Measured time-to-decision change; override rate understood |
| **3. Scale (ongoing)** | More products and policies, drift monitoring, feedback loop from outcomes | Operational runbook, ownership transferred to the client team |

## 8. Open questions for the first workshop

1. Which product lines and regions are in scope, and which regulator directions apply to each?
2. What are the authoritative policy sources, and who owns updates?
3. Which fields may leave the core system, and where may Gemini be called from?
4. What does the model-governance process require before a new score is used?
5. What would make Compliance say "no" to a proposal, and can we encode those cases as eval items?
