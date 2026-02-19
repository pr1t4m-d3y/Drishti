import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { AlertTriangle, ChevronDown } from 'lucide-react';
import { fetchTransactions } from '../../api';

const MODE_COLORS = {
    'UPI': 'bg-purple-100 text-purple-700',
    'CC': 'bg-amber-100 text-amber-700',
    'DC': 'bg-sky-blue/10 text-sky-blue',
    'NEFT': 'bg-emerald-100 text-emerald-700',
    'IMPS': 'bg-indigo-100 text-indigo-700',
};

export default function TransactionsTab({ customerId }) {
    const [months, setMonths] = useState(6);
    const [transactions, setTransactions] = useState([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        setLoading(true);
        fetchTransactions(customerId, months).then(data => {
            setTransactions(data);
            setLoading(false);
        });
    }, [customerId, months]);

    const formatDate = (iso) => {
        const d = new Date(iso);
        const day = d.getDate();
        const month = d.toLocaleString('en-IN', { month: 'short' });
        const time = d.toLocaleString('en-IN', { hour: '2-digit', minute: '2-digit', hour12: true });
        return `${day} ${month}, ${time}`;
    };

    return (
        <div className="space-y-4">
            {/* Timeframe Dropdown */}
            <div className="flex justify-between items-center">
                <h3 className="text-sm font-semibold text-oxford-blue">Transaction History</h3>
                <div className="relative">
                    <select
                        value={months}
                        onChange={e => setMonths(Number(e.target.value))}
                        className="appearance-none bg-white border border-slate-200 rounded-lg px-4 py-2 pr-8 text-sm text-oxford-blue cursor-pointer focus:outline-none focus:ring-2 focus:ring-sky-blue/30"
                    >
                        <option value={1}>Last 1 Month</option>
                        <option value={3}>Last 3 Months</option>
                        <option value={6}>Last 6 Months</option>
                        <option value={12}>Last 1 Year</option>
                    </select>
                    <ChevronDown className="absolute right-2 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-grey pointer-events-none" />
                </div>
            </div>

            {/* Transactions Table */}
            <div className="card overflow-hidden">
                <div className="max-h-[500px] overflow-y-auto">
                    <table className="w-full">
                        <thead className="sticky top-0 z-5">
                            <tr className="bg-oxford-blue text-white text-xs uppercase tracking-wider">
                                <th className="px-5 py-3 text-left font-semibold">Date & Time</th>
                                <th className="px-5 py-3 text-left font-semibold">Merchant</th>
                                <th className="px-5 py-3 text-left font-semibold">Category</th>
                                <th className="px-5 py-3 text-left font-semibold">Mode</th>
                                <th className="px-5 py-3 text-right font-semibold">Amount</th>
                            </tr>
                        </thead>
                        <tbody>
                            {loading ? (
                                <tr><td colSpan="5" className="px-5 py-12 text-center text-sm text-slate-grey">Loading...</td></tr>
                            ) : transactions.length === 0 ? (
                                <tr><td colSpan="5" className="px-5 py-12 text-center text-sm text-slate-grey">No transactions found</td></tr>
                            ) : (
                                transactions.map((txn, i) => (
                                    <motion.tr
                                        key={txn.id || i}
                                        initial={{ opacity: 0 }}
                                        animate={{ opacity: 1 }}
                                        transition={{ delay: Math.min(i * 0.02, 0.5) }}
                                        className={`border-b border-slate-50 text-sm ${i % 2 === 0 ? 'bg-white' : 'bg-slate-50/50'}`}
                                    >
                                        <td className="px-5 py-3 text-slate-grey text-xs">{formatDate(txn.date)}</td>
                                        <td className="px-5 py-3">
                                            <div className="flex items-center gap-2">
                                                <span className="font-medium text-oxford-blue">{txn.merchant}</span>
                                                {(txn.is_gambling === 1 || txn.is_lending_app === 1) && (
                                                    <AlertTriangle className="w-4 h-4 text-risk-warning" />
                                                )}
                                            </div>
                                        </td>
                                        <td className="px-5 py-3 text-slate-grey">{txn.category}</td>
                                        <td className="px-5 py-3">
                                            <span className={`px-2 py-0.5 rounded text-xs font-semibold ${MODE_COLORS[txn.mode] || 'bg-slate-100 text-slate-600'}`}>
                                                {txn.mode}
                                            </span>
                                        </td>
                                        <td className="px-5 py-3 text-right font-mono font-semibold">
                                            <div className="flex items-center justify-end gap-2">
                                                <span className={txn.amount >= 0 ? 'text-risk-safe' : 'text-risk-critical'}>
                                                    {txn.amount >= 0 ? '+' : ''}₹{Math.abs(txn.amount).toLocaleString('en-IN')}
                                                </span>
                                                {txn.is_bounced === 1 && (
                                                    <span className="px-1.5 py-0.5 bg-risk-critical text-white text-[10px] font-bold rounded">BOUNCED</span>
                                                )}
                                            </div>
                                        </td>
                                    </motion.tr>
                                ))
                            )}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
}
