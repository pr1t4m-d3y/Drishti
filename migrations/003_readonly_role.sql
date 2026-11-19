-- requires: READONLY_PASSWORD
-- Least-privilege role for the agents' SQL tools. `default_label` (ground truth) is deliberately NOT granted.
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'drishti_ro') THEN
        CREATE ROLE drishti_ro LOGIN PASSWORD '{{READONLY_PASSWORD}}' NOSUPERUSER NOCREATEDB NOCREATEROLE;
    END IF;
END $$;
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
