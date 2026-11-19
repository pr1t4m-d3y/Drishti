import { motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';

const SEGMENT_COLORS = {
    'CRITICAL': 'risk-badge-critical',
    'HIGH RISK': 'risk-badge-high',
    'MEDIUM RISK': 'risk-badge-medium',
    'SAFE': 'risk-badge-safe',
};

export default function CustomerTable({ customers, total, loading, segment }) {
    const navigate = useNavigate();

    return (
        <div className="card overflow-hidden">
            <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
                <h3 className="text-sm font-semibold text-oxford-blue">Customer Overview</h3>
                <span className="text-xs text-slate-grey">{total} results</span>
            </div>

            <div className="max-h-[520px] overflow-y-auto">
                <table className="w-full">
                    <thead className="sticky top-0 z-5">
                        <tr className="bg-oxford-blue text-white text-xs uppercase tracking-wider">
                            <th className="px-6 py-3 text-left font-semibold">Customer ID</th>
                            <th className="px-6 py-3 text-left font-semibold">Risk Segment</th>
                            <th className="px-6 py-3 text-left font-semibold">Risk Score</th>
                            <th className="px-6 py-3 text-left font-semibold">EMI/Income %</th>
                            <th className="px-6 py-3 text-left font-semibold">Credit Util %</th>
                            <th className="px-6 py-3 text-left font-semibold">Late Payments</th>
                        </tr>
                    </thead>
                    <tbody>
                        {loading ? (
                            <tr><td colSpan="6" className="px-6 py-12 text-center text-slate-grey text-sm">Loading...</td></tr>
                        ) : customers.length === 0 ? (
                            <tr><td colSpan="6" className="px-6 py-12 text-center text-slate-grey text-sm">No customers found</td></tr>
                        ) : (
                            customers.map((c, i) => (
                                <motion.tr
                                    key={c.id}
                                    whileHover={{ scale: 1.005, backgroundColor: '#F8FAFC' }}
                                    onClick={() => navigate(`/customer/${c.id}?segment=${segment}`)}
                                    className={`cursor-pointer border-b border-slate-50 text-sm transition-colors ${i % 2 === 0 ? 'bg-white' : 'bg-slate-50/50'
                                        }`}
                                >
                                    <td className="px-6 py-3 font-medium text-oxford-blue">{c.id}</td>
                                    <td className="px-6 py-3">
                                        <span className={`risk-badge ${SEGMENT_COLORS[c.risk_segment]}`}>{c.risk_segment}</span>
                                    </td>
                                    <td className="px-6 py-3 font-mono">{c.risk_score}</td>
                                    <td className="px-6 py-3 font-mono">{c.emi_income_ratio}%</td>
                                    <td className="px-6 py-3 font-mono">{c.credit_util_pct}%</td>
                                    <td className="px-6 py-3">
                                        <span className={c.late_payments > 0 ? 'text-risk-critical font-semibold' : 'text-risk-safe'}>
                                            {c.late_payments}
                                        </span>
                                    </td>
                                </motion.tr>
                            ))
                        )}
                    </tbody>
                </table>
            </div>
        </div>
    );
}
