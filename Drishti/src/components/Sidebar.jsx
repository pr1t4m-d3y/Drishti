import { motion } from 'framer-motion';
import { ChevronDown, Search } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

const RISK_LEVELS = ['CRITICAL', 'HIGH RISK', 'MEDIUM RISK', 'SAFE'];
const RISK_COLORS = {
    'CRITICAL': 'bg-risk-critical text-white',
    'HIGH RISK': 'bg-risk-critical/80 text-white',
    'MEDIUM RISK': 'bg-risk-warning text-white',
    'SAFE': 'bg-risk-safe text-white',
};
const RISK_OUTLINE = {
    'CRITICAL': 'border-risk-critical text-risk-critical',
    'HIGH RISK': 'border-risk-critical/70 text-risk-critical',
    'MEDIUM RISK': 'border-risk-warning text-risk-warning',
    'SAFE': 'border-risk-safe text-risk-safe',
};

export default function Sidebar({ segment, stats, customers, selectedCustomer, onCustomerSelect, riskFilter, onRiskFilter }) {
    const navigate = useNavigate();
    const segmentLabel = segment === 'credit_card' ? 'Credit Card Mode' : 'All Users Mode';

    return (
        <aside className="fixed left-0 top-0 w-[25%] h-screen bg-white border-r border-slate-100 flex flex-col z-10"
            style={{ boxShadow: '4px 0 20px rgba(0,0,0,0.03)' }}>

            {/* Header / Logo */}
            <div className="p-6 border-b border-slate-100">
                <div className="flex items-center gap-2 cursor-pointer" onClick={() => navigate('/')}>
                    <img src="/logo.png" alt="Drishti Logo" className="w-8 h-8 object-contain" />
                    <h1 className="text-xl font-bold text-oxford-blue tracking-tight">DRISHTI</h1>
                </div>
                <p className="text-xs text-slate-grey mt-1.5 flex items-center gap-1">
                    <span className="opacity-50">›</span> {segmentLabel}
                </p>
            </div>

            {/* Stat Cards */}
            <div className="p-4 flex flex-col gap-3">
                <motion.div
                    className="card p-4 border border-risk-critical/10"
                    whileHover={{ y: -3, boxShadow: '0px 10px 25px rgba(211,47,47,0.08)' }}
                    transition={{ type: 'spring', stiffness: 400, damping: 25 }}
                >
                    <p className="text-3xl font-bold text-risk-critical">{stats?.highRiskCount ?? '—'}</p>
                    <p className="text-xs text-slate-grey mt-1 uppercase tracking-wide">High Risk</p>
                </motion.div>

                <motion.div
                    className="card p-4 border border-sky-blue/10"
                    whileHover={{ y: -3, boxShadow: '0px 10px 25px rgba(0,174,239,0.08)' }}
                    transition={{ type: 'spring', stiffness: 400, damping: 25 }}
                >
                    <p className="text-3xl font-bold text-sky-blue">{stats?.totalCustomers ?? '—'}</p>
                    <p className="text-xs text-slate-grey mt-1 uppercase tracking-wide">Total Profiles</p>
                </motion.div>

                <motion.div
                    className="card p-4 border border-sky-blue/10"
                    whileHover={{ y: -3, boxShadow: '0px 10px 25px rgba(0,174,239,0.08)' }}
                    transition={{ type: 'spring', stiffness: 400, damping: 25 }}
                >
                    <p className="text-3xl font-bold text-sky-blue">{stats?.activeAccounts ?? '—'}</p>
                    <p className="text-xs text-slate-grey mt-1 uppercase tracking-wide">Active</p>
                </motion.div>
            </div>

            {/* Customer Dropdown */}
            <div className="px-4 pb-4">
                <label className="text-xs text-slate-grey uppercase tracking-wide mb-2 block">Select Customer</label>
                <div className="relative">
                    <select
                        value={selectedCustomer}
                        onChange={(e) => onCustomerSelect(e.target.value)}
                        className="w-full bg-white border border-slate-200 rounded-lg px-4 py-2.5 text-sm text-oxford-blue appearance-none cursor-pointer focus:outline-none focus:ring-2 focus:ring-sky-blue/30 focus:border-sky-blue"
                    >
                        <option value="">Search Customer ID...</option>
                        {customers.map(c => (
                            <option key={c.id} value={c.id}>{c.id} — {c.name}</option>
                        ))}
                    </select>
                    <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-grey pointer-events-none" />
                </div>
            </div>

            {/* Risk Filter Pills */}
            <div className="px-4 pb-4 flex-1 overflow-y-auto">
                <label className="text-xs text-slate-grey uppercase tracking-wide mb-3 block">Filter by Risk</label>
                <div className="flex flex-wrap gap-2">
                    {RISK_LEVELS.map(level => {
                        const isActive = riskFilter === level;
                        return (
                            <motion.button
                                key={level}
                                whileHover={{ scale: 1.05 }}
                                whileTap={{ scale: 0.95 }}
                                onClick={() => onRiskFilter(level)}
                                className={`px-3 py-1.5 rounded-full text-xs font-semibold border transition-all ${isActive ? RISK_COLORS[level] + ' border-transparent' : RISK_OUTLINE[level] + ' bg-transparent'
                                    }`}
                            >
                                {level}
                            </motion.button>
                        );
                    })}
                </div>
            </div>

            {/* Segment Switcher */}
            <div className="p-4 border-t border-slate-100">
                <button
                    onClick={() => navigate(`/dashboard?segment=${segment === 'all' ? 'credit_card' : 'all'}`)}
                    className="w-full text-xs text-sky-blue hover:text-oxford-blue transition-colors text-center py-2"
                >
                    Switch to {segment === 'all' ? 'Credit Card Users' : 'All Users'} →
                </button>
            </div>
        </aside>
    );
}
