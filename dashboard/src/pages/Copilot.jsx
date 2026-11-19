import { useCallback, useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { ArrowLeft, Send, ShieldCheck, Check, X } from 'lucide-react';
import { chat, decide, health, pendingInterventions } from '../copilotApi';

const EXAMPLES = [
    'Which 10 customers are most at risk this month and why?',
    'What can we offer customer #4521 under our policies?',
    'Is a 10-day EMI extension allowed for a customer with two missed payments?',
    'Now draft a counselling note for the top 3.',
];

export default function Copilot() {
    const navigate = useNavigate();
    const [key, setKey] = useState(() => sessionStorage.getItem('drishti_key') || '');
    const [messages, setMessages] = useState([]);
    const [sessionId, setSessionId] = useState(null);
    const [input, setInput] = useState('');
    const [busy, setBusy] = useState(false);
    const [error, setError] = useState('');
    const [pending, setPending] = useState([]);
    const [status, setStatus] = useState(null);
    const endRef = useRef(null);

    useEffect(() => { health().then(setStatus).catch(() => setStatus(null)); }, []);
    useEffect(() => { endRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages]);

    const refreshPending = useCallback(() => {
        if (!key) return;
        pendingInterventions(key).then(setPending).catch(() => setPending([]));
    }, [key]);
    useEffect(refreshPending, [refreshPending]);

    const saveKey = (v) => { setKey(v); sessionStorage.setItem('drishti_key', v); };

    const send = async (text) => {
        const q = (text ?? input).trim();
        if (!q || busy) return;
        setInput(''); setError(''); setBusy(true);
        setMessages((m) => [...m, { role: 'user', text: q }]);
        try {
            const r = await chat(key, q, sessionId);
            setSessionId(r.session_id);
            setMessages((m) => [...m, { role: 'assistant', text: r.answer, meta: r }]);
            refreshPending();
        } catch (e) {
            setError(e.message);
        } finally { setBusy(false); }
    };

    const act = async (id, decision) => {
        try { await decide(key, id, decision); refreshPending(); } catch (e) { setError(e.message); }
    };

    return (
        <div className="min-h-screen bg-page-bg flex">
            <aside className="w-[28%] min-w-[300px] bg-white border-r border-slate-100 p-6 flex flex-col gap-5">
                <button onClick={() => navigate('/')} className="flex items-center gap-2 text-sm text-slate-grey hover:text-oxford-blue">
                    <ArrowLeft className="w-4 h-4" /> Back
                </button>
                <div>
                    <h1 className="text-xl font-bold text-oxford-blue">Drishti Copilot</h1>
                    <p className="text-xs text-slate-grey mt-1 flex items-center gap-1">
                        <ShieldCheck className="w-3 h-3" /> Recommendations only. A human approves every action.
                    </p>
                </div>
                <div>
                    <label className="text-xs text-slate-grey uppercase tracking-wide">API key</label>
                    <input type="password" value={key} onChange={(e) => saveKey(e.target.value)} placeholder="dk_..."
                        className="mt-1 w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-sky-blue/30" />
                    <p className="text-[11px] text-slate-grey mt-1">
                        API {status ? `up (${status.customers.toLocaleString()} customers)` : 'unreachable: start it with `make api`'}
                    </p>
                </div>
                <div>
                    <p className="text-xs text-slate-grey uppercase tracking-wide mb-2">Try</p>
                    <div className="flex flex-col gap-2">
                        {EXAMPLES.map((e) => (
                            <button key={e} onClick={() => send(e)} disabled={busy || !key}
                                className="text-left text-xs card p-3 border border-slate-100 hover:border-sky-blue disabled:opacity-50">{e}</button>
                        ))}
                    </div>
                </div>
                <div className="flex-1 overflow-y-auto">
                    <p className="text-xs text-slate-grey uppercase tracking-wide mb-2">Pending approvals ({pending.length})</p>
                    {pending.map((p) => (
                        <div key={p.id} className="card p-3 border border-slate-100 mb-2 text-xs">
                            <p className="font-semibold text-oxford-blue">Customer {p.customer_id}: {p.action_type}</p>
                            <p className="mt-1">{p.rationale}</p>
                            {p.citations.map((c) => <p key={c.chunk_id} className="text-[11px] text-slate-grey mt-1">{c.doc}, {c.section}, p.{c.page}</p>)}
                            <div className="flex gap-2 mt-2">
                                <button onClick={() => act(p.id, 'approved')} className="flex items-center gap-1 px-2 py-1 rounded bg-risk-safe text-white"><Check className="w-3 h-3" />Approve</button>
                                <button onClick={() => act(p.id, 'rejected')} className="flex items-center gap-1 px-2 py-1 rounded border border-risk-critical text-risk-critical"><X className="w-3 h-3" />Reject</button>
                            </div>
                        </div>
                    ))}
                </div>
            </aside>

            <main className="flex-1 flex flex-col h-screen">
                <div className="flex-1 overflow-y-auto p-8 space-y-4">
                    {messages.length === 0 && <p className="text-sm text-slate-grey">Ask about risk, policy or an intervention. Add your API key first.</p>}
                    {messages.map((m, i) => (
                        <motion.div key={i} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
                            className={`max-w-[75%] card p-4 text-sm ${m.role === 'user' ? 'ml-auto bg-sky-blue/10' : ''}`}>
                            <p className="whitespace-pre-wrap">{m.text}</p>
                            {m.meta && (
                                <div className="mt-3 pt-3 border-t border-slate-100 text-[11px] text-slate-grey space-y-1">
                                    <p>trace <code>{m.meta.trace_id}</code> · grounded: {String(m.meta.grounded)} ·
                                        {' '}{m.meta.metrics.latency_s}s · {m.meta.metrics.input_tokens}/{m.meta.metrics.output_tokens} tokens ·
                                        {' '}{m.meta.metrics.cost_usd == null ? 'cost n/a' : `$${m.meta.metrics.cost_usd}`} · {m.meta.metrics.agent_steps} steps</p>
                                    {m.meta.citations.map((c) => <p key={c.chunk_id}>Source: {c.doc}, {c.section}, p.{c.page}</p>)}
                                </div>
                            )}
                        </motion.div>
                    ))}
                    {busy && <p className="text-sm text-slate-grey">Agents working…</p>}
                    {error && <p className="text-sm text-risk-critical">{error}</p>}
                    <div ref={endRef} />
                </div>
                <form onSubmit={(e) => { e.preventDefault(); send(); }} className="p-4 border-t border-slate-100 bg-white flex gap-3">
                    <input value={input} onChange={(e) => setInput(e.target.value)} placeholder="Ask about risk, policy or an intervention"
                        className="flex-1 border border-slate-200 rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-sky-blue/30" />
                    <button disabled={busy || !key} className="px-4 py-2.5 rounded-lg bg-sky-blue text-white text-sm font-semibold disabled:opacity-50 flex items-center gap-2">
                        <Send className="w-4 h-4" /> Send
                    </button>
                </form>
            </main>
        </div>
    );
}
