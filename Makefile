.PHONY: help setup data train load ingest up api ui test lint typecheck eval eval-offline report deploy teardown
PY ?= .venv/bin/python

help:            ## list targets
	@grep -E '^[a-z-]+:.*##' Makefile | sed 's/:.*##/\t/'

setup:           ## create venv and install pinned dependencies
	python3 -m venv .venv && $(PY) -m pip install -r requirements-dev.txt

data:            ## download the UCI credit-default dataset (30k rows)
	mkdir -p data/raw && curl -sSL -o data/raw/uci.zip "https://archive.ics.uci.edu/static/public/350/default+of+credit+card+clients.zip" && unzip -oq data/raw/uci.zip -d data/raw

train:           ## train + evaluate the risk model, write models/metrics.json
	$(PY) -m drishti.ml.train

load:            ## score all customers and load them into the database
	$(PY) -m drishti.db.load

ingest:          ## parse -> chunk -> embed -> store the policy PDFs in data/policies (idempotent)
	$(PY) -m ingest run

up:              ## full local stack with Postgres + pgvector (needs Docker)
	docker compose up --build

api:             ## API without Docker (SQLite)
	$(PY) -m uvicorn drishti.api.main:app --reload --port 8000

ui:              ## Streamlit admin UI
	$(PY) -m streamlit run ui/streamlit_app.py

test:            ## unit + integration tests with coverage
	$(PY) -m pytest --cov=drishti --cov=ingest --cov=evals --cov=benchmarks --cov-report=term-missing

lint:            ## ruff
	$(PY) -m ruff check .

typecheck:       ## mypy
	$(PY) -m mypy drishti ingest evals

eval-offline:    ## guardrails, retrieval and oracle checks. No cloud needed
	$(PY) -m evals.run --offline --check

eval:            ## full baseline vs final evaluation (needs Vertex AI credentials)
	$(PY) -m evals.run --variant baseline --judge && $(PY) -m evals.run --variant final --judge --check && $(PY) -m evals.run --report

report:          ## rebuild evals/results/RESULTS.md from saved runs
	$(PY) -m evals.run --report

deploy:          ## build and deploy to Cloud Run (see deploy/README.md)
	bash deploy/deploy.sh

teardown:        ## delete every cloud resource created by deploy
	bash deploy/teardown.sh
