// Client for the Drishti copilot API (FastAPI). Proxied at /copilot-api in dev (see vite.config.js).
const BASE = '/copilot-api';

function headers(key) {
    return { 'Content-Type': 'application/json', 'X-API-Key': key };
}

async function parse(res) {
    const body = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(body?.error?.message || `Request failed (${res.status})`);
    return body;
}

export const chat = (key, message, sessionId) =>
    fetch(`${BASE}/chat`, { method: 'POST', headers: headers(key), body: JSON.stringify({ message, session_id: sessionId || null }) }).then(parse);

export const pendingInterventions = (key) =>
    fetch(`${BASE}/interventions?status=proposed`, { headers: headers(key) }).then(parse);

export const decide = (key, id, decision, note = '') =>
    fetch(`${BASE}/interventions/${id}/decision`, { method: 'POST', headers: headers(key), body: JSON.stringify({ decision, note }) }).then(parse);

export const health = () => fetch(`${BASE}/health`).then(parse);
