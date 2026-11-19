const API_BASE = '/api';

export async function fetchStats(segment = 'all') {
    const res = await fetch(`${API_BASE}/stats?segment=${segment}`);
    return res.json();
}

export async function fetchCustomers({ segment = 'all', risk, search, filter, limit = 50, offset = 0 } = {}) {
    const params = new URLSearchParams({ segment, limit, offset });
    if (risk) params.set('risk', risk);
    if (search) params.set('search', search);
    if (filter) params.set('filter', filter);
    const res = await fetch(`${API_BASE}/customers?${params}`);
    return res.json();
}

export async function fetchCustomer(id) {
    const res = await fetch(`${API_BASE}/customers/${id}`);
    return res.json();
}

export async function fetchTransactions(id, months = 6) {
    const res = await fetch(`${API_BASE}/customers/${id}/transactions?months=${months}`);
    return res.json();
}

export async function createIntervention(customerId, action, analystName) {
    const res = await fetch(`${API_BASE}/interventions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ customerId, action, analystName }),
    });
    return res.json();
}

export async function fetchInterventions(id) {
    const res = await fetch(`${API_BASE}/customers/${id}/interventions`);
    return res.json();
}
