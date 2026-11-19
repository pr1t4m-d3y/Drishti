-- PostgreSQL: least-privilege role used by the agents' SQL tools.
-- Run once as an admin after the schema exists. Password comes from Secret Manager.
-- The agent role can read only the columns it needs: `default_label` (ground truth) is excluded.
CREATE ROLE drishti_ro LOGIN PASSWORD :'ro_password' NOSUPERUSER NOCREATEDB NOCREATEROLE;
REVOKE ALL ON ALL TABLES IN SCHEMA public FROM drishti_ro;
GRANT USAGE ON SCHEMA public TO drishti_ro;
GRANT SELECT (
    customer_id, limit_bal, sex, education, marriage, age,
    pay_1, pay_2, pay_3, pay_4, pay_5, pay_6,
    bill_amt1, bill_amt2, bill_amt3, bill_amt4, bill_amt5, bill_amt6,
    pay_amt1, pay_amt2, pay_amt3, pay_amt4, pay_amt5, pay_amt6,
    n_delinquent_months, max_delay, util_latest,
    risk_proba, risk_segment, top_risk_factors, scored_at
) ON customers TO drishti_ro;
GRANT SELECT ON interventions TO drishti_ro;
ALTER ROLE drishti_ro SET statement_timeout = '5s';
ALTER ROLE drishti_ro SET default_transaction_read_only = on;
