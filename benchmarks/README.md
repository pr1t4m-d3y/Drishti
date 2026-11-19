# Review-time benchmark (how a "% faster" claim can honestly be made)

The v1 project description claimed a 35% cut in risk-review time with no measurement behind it.
This harness measures it properly. **Nothing in this repo reports a time reduction until you run it
with real analysts.** `analyze` refuses to print a percentage for fewer than 3 participants.

## Protocol
* Each participant reviews the same set of cases (customers chosen deterministically, stratified across risk segments).
* Each case is reviewed once, in one of two conditions, **counterbalanced** across participants so order and case difficulty don't bias the result:
  * `manual`: the participant sees the raw customer fields and looks policy up themselves in `data/policies/`.
  * `assisted`: the participant sees the copilot's cited recommendation (needs LLM credentials).
* The timer runs from "case shown" until the participant types a decision (one of the allowed action types).
* Optional: put a senior reviewer's decisions in `benchmarks/reference_decisions.csv` (`case_id,decision`) to also report decision agreement, because faster is not better if decisions get worse.

## Run
```bash
python -m benchmarks.review_time run --participant analyst1 --cases 6
python -m benchmarks.review_time run --participant analyst2 --cases 6
python -m benchmarks.review_time analyze
```
Output: median seconds per condition, paired % reduction with a bootstrap 95% confidence interval, and decision agreement.
Raw timings are in `benchmarks/results/timings.csv`.
