# Working on Drishti together

Current status and pending items: [docs/ROADMAP.md](docs/ROADMAP.md).

## Split of work

| Area | Owner | Where |
|---|---|---|
| Model (research, features, tuning) | ML collaborator | `notebooks/`, `models/incoming/`, `add_features()` in `drishti/ml/data.py` |
| App (API, agents, retrieval, data, UI, deploy) | App owner | everything else |

The two sides meet at one interface, described in [docs/MODEL_CONTRACT.md](docs/MODEL_CONTRACT.md). The app runs without
any collaborator work (it trains a built-in model); a model in `models/incoming/` replaces it.

## Flow

1. Branch from `main`: `git checkout -b feat/<short-name>`.
2. Make the change. Keep commits small.
3. Run the checks you can: `make lint typecheck test`. For a model change, also `python -m drishti.ml.import_model --load`.
4. Open a PR. CI runs lint, types, tests, the offline evaluation, the Postgres/pgvector tests, the Docker build, Terraform
   validation and the dashboard build. A model change is validated by CI too (`make train` imports `models/incoming/`).
5. Merge when green.

## Model changes

* Notebook outputs are noisy in diffs: clear outputs before committing (`Cell -> All Output -> Clear`), or commit only the
  exported model and card.
* Report numbers from `models/metrics.json` (written by the importer), not from the notebook, so they come from the same
  held-out test split and protocol as every other model.
* Never train on the test split. Never put credentials in a notebook.

## Conventions

* Python 3.11+, typed, formatted and linted by ruff, checked by mypy.
* No secrets in git: use `secrets/` (git-ignored) or Secret Manager.
* Every behaviour change comes with a test; the golden set in `evals/` guards agent behaviour.
