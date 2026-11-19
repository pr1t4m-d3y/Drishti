-- Core relational schema (PostgreSQL). Kept in sync with drishti/db/models.py by tests/test_migrations.py.

CREATE TABLE IF NOT EXISTS customers (
    customer_id          INTEGER PRIMARY KEY,
    limit_bal            DOUBLE PRECISION NOT NULL,
    sex                  INTEGER NOT NULL,
    education            INTEGER NOT NULL,
    marriage             INTEGER NOT NULL,
    age                  INTEGER NOT NULL,
    pay_1 INTEGER NOT NULL, pay_2 INTEGER NOT NULL, pay_3 INTEGER NOT NULL,
    pay_4 INTEGER NOT NULL, pay_5 INTEGER NOT NULL, pay_6 INTEGER NOT NULL,
    bill_amt1 DOUBLE PRECISION NOT NULL, bill_amt2 DOUBLE PRECISION NOT NULL, bill_amt3 DOUBLE PRECISION NOT NULL,
    bill_amt4 DOUBLE PRECISION NOT NULL, bill_amt5 DOUBLE PRECISION NOT NULL, bill_amt6 DOUBLE PRECISION NOT NULL,
    pay_amt1 DOUBLE PRECISION NOT NULL, pay_amt2 DOUBLE PRECISION NOT NULL, pay_amt3 DOUBLE PRECISION NOT NULL,
    pay_amt4 DOUBLE PRECISION NOT NULL, pay_amt5 DOUBLE PRECISION NOT NULL, pay_amt6 DOUBLE PRECISION NOT NULL,
    n_delinquent_months  INTEGER NOT NULL,
    max_delay            INTEGER NOT NULL,
    util_latest          DOUBLE PRECISION NOT NULL,
    risk_proba           DOUBLE PRECISION NOT NULL,
    risk_segment         VARCHAR(16) NOT NULL,
    top_risk_factors     JSONB,
    scored_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    default_label        INTEGER NOT NULL  -- ground truth, evaluation only; never granted to the agent role
);
CREATE INDEX IF NOT EXISTS ix_customers_risk_proba ON customers (risk_proba DESC);
CREATE INDEX IF NOT EXISTS ix_customers_risk_segment ON customers (risk_segment);
CREATE INDEX IF NOT EXISTS ix_customers_seg_proba ON customers (risk_segment, risk_proba DESC);

CREATE TABLE IF NOT EXISTS interventions (
    id            SERIAL PRIMARY KEY,
    customer_id   INTEGER NOT NULL REFERENCES customers (customer_id),
    action_type   VARCHAR(32) NOT NULL
                  CHECK (action_type IN ('EMI_EXTENSION','RESTRUCTURING_REVIEW','COUNSELLING_REFERRAL','PAYMENT_REMINDER','NO_ACTION')),
    rationale     TEXT NOT NULL,
    citations     JSONB,
    status        VARCHAR(16) NOT NULL DEFAULT 'proposed' CHECK (status IN ('proposed','approved','rejected')),
    proposed_by   VARCHAR(64) NOT NULL DEFAULT 'intervention_agent',
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    decided_by    VARCHAR(64),
    decided_at    TIMESTAMPTZ,
    decision_note TEXT,
    -- four-eyes rule enforced in the database as well as the API
    CONSTRAINT ck_four_eyes CHECK (decided_by IS NULL OR decided_by <> proposed_by)
);
CREATE INDEX IF NOT EXISTS ix_interventions_customer ON interventions (customer_id);
CREATE INDEX IF NOT EXISTS ix_interventions_status ON interventions (status);

CREATE TABLE IF NOT EXISTS api_keys (
    id         SERIAL PRIMARY KEY,
    name       VARCHAR(64) NOT NULL UNIQUE,
    key_hash   VARCHAR(64) NOT NULL UNIQUE,   -- salted SHA-256; the key itself is never stored
    role       VARCHAR(16) NOT NULL DEFAULT 'analyst' CHECK (role IN ('analyst','admin')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    revoked    INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS request_metrics (
    id         SERIAL PRIMARY KEY,
    trace_id   VARCHAR(32) NOT NULL,
    session_id VARCHAR(64) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    payload    JSONB NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_request_metrics_trace ON request_metrics (trace_id);
CREATE INDEX IF NOT EXISTS ix_request_metrics_session ON request_metrics (session_id);
