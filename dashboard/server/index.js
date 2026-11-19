const express = require('express');
const cors = require('cors');
const db = require('./db');

const app = express();
app.use(cors());
app.use(express.json());

// GET /api/stats?segment=all|credit_card
app.get('/api/stats', (req, res) => {
    const segment = req.query.segment || 'all';
    const where = segment === 'credit_card' ? 'WHERE has_credit_card = 1' : '';

    const stats = db.prepare(`
    SELECT 
      COUNT(*) as totalCustomers,
      SUM(CASE WHEN risk_segment IN ('CRITICAL', 'HIGH RISK') THEN 1 ELSE 0 END) as highRiskCount,
      SUM(CASE WHEN risk_segment = 'CRITICAL' THEN 1 ELSE 0 END) as criticalCount,
      ROUND(AVG(credit_util_pct), 1) as avgCreditUtil,
      SUM(late_payments) as totalLatePayments,
      SUM(failed_auto_debits) as totalFailedDebits,
      SUM(CASE WHEN risk_segment = 'SAFE' THEN 1 ELSE 0 END) as safeCount,
      SUM(CASE WHEN risk_segment = 'MEDIUM RISK' THEN 1 ELSE 0 END) as mediumCount
    FROM customers ${where}
  `).get();

    const activeAccounts = db.prepare(`SELECT COUNT(*) as cnt FROM customers ${where}`).get().cnt;
    stats.activeAccounts = activeAccounts;

    res.json(stats);
});

// GET /api/customers?segment=all|credit_card&risk=CRITICAL&search=&filter=&limit=&offset=
app.get('/api/customers', (req, res) => {
    const { segment = 'all', risk, search, filter, limit = 50, offset = 0 } = req.query;

    let conditions = [];
    let params = {};

    if (segment === 'credit_card') {
        conditions.push('has_credit_card = 1');
    }

    if (risk) {
        conditions.push('risk_segment = @risk');
        params.risk = risk;
    }

    if (search) {
        conditions.push('(CAST(id AS TEXT) LIKE @search OR name LIKE @searchName OR city LIKE @searchCity)');
        params.search = `%${search}%`;
        params.searchName = `%${search}%`;
        params.searchCity = `%${search}%`;
    }

    // Bento grid filters
    if (filter === 'critical') {
        conditions.push("risk_segment = 'CRITICAL'");
    } else if (filter === 'late_payments') {
        conditions.push('late_payments > 0');
    } else if (filter === 'failed_debits') {
        conditions.push('failed_auto_debits > 0');
    } else if (filter === 'high_credit_util') {
        conditions.push('credit_util_pct > 75');
    }

    const where = conditions.length ? 'WHERE ' + conditions.join(' AND ') : '';

    const customers = db.prepare(`
    SELECT id, name, risk_segment, risk_score, emi_income_ratio, credit_util_pct, late_payments, 
           failed_auto_debits, has_credit_card, city, income
    FROM customers ${where}
    ORDER BY risk_score DESC
    LIMIT @limit OFFSET @offset
  `).all({ ...params, limit: Number(limit), offset: Number(offset) });

    const total = db.prepare(`SELECT COUNT(*) as cnt FROM customers ${where}`).all(params)[0].cnt;

    res.json({ customers, total });
});

// GET /api/customers/:id
app.get('/api/customers/:id', (req, res) => {
    const customer = db.prepare('SELECT * FROM customers WHERE id = ?').get(req.params.id);
    if (!customer) return res.status(404).json({ error: 'Customer not found' });

    // Parse JSON fields
    customer.investments = JSON.parse(customer.investments || '[]');
    customer.balanceHistory = JSON.parse(customer.balance_history || '[]');
    customer.moneyFlow = JSON.parse(customer.money_flow || '[]');
    customer.creditHistory = JSON.parse(customer.credit_history || '[]');
    customer.expenseBreakdown = JSON.parse(customer.expense_breakdown || '{}');
    customer.emiDelays = JSON.parse(customer.emi_delays || '[]');

    res.json(customer);
});

// GET /api/customers/:id/transactions?months=1|3|6|12
app.get('/api/customers/:id/transactions', (req, res) => {
    const months = Number(req.query.months || 6);
    const cutoff = new Date();
    cutoff.setMonth(cutoff.getMonth() - months);

    const transactions = db.prepare(`
    SELECT * FROM transactions 
    WHERE customer_id = ? AND date >= ?
    ORDER BY date DESC
  `).all(req.params.id, cutoff.toISOString());

    res.json(transactions);
});

// POST /api/interventions
app.post('/api/interventions', (req, res) => {
    const { customerId, action, analystName = 'Risk Analyst' } = req.body;

    const result = db.prepare(`
    INSERT INTO interventions (customer_id, date, action, status, analyst_name)
    VALUES (?, ?, ?, 'Sent', ?)
  `).run(customerId, new Date().toISOString(), action, analystName);

    res.json({ id: result.lastInsertRowid, status: 'Sent' });
});

// GET /api/customers/:id/interventions
app.get('/api/customers/:id/interventions', (req, res) => {
    const interventions = db.prepare(`
    SELECT * FROM interventions WHERE customer_id = ? ORDER BY date DESC
  `).all(req.params.id);

    res.json(interventions);
});

const PORT = 3001;
app.listen(PORT, () => {
    console.log(`👁️  Drishti API running on http://localhost:${PORT}`);
});
