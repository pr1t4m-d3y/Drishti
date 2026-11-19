import { motion } from 'framer-motion';
import {
    AreaChart, Area, LineChart, Line, BarChart, Bar,
    XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine,
} from 'recharts';
import { CheckCircle, XCircle } from 'lucide-react';

export default function FinancialTab({ customer }) {
    const balanceHistory = customer.balanceHistory || [];
    const creditHistory = customer.creditHistory || [];
    const expenseBreakdown = customer.expenseBreakdown || {};
    const emiDelays = customer.emiDelays || [];

    // Spending by category data
    const categoryData = Object.entries(expenseBreakdown).map(([name, value]) => ({
        name: name.length > 8 ? name.slice(0, 8) + '…' : name,
        fullName: name,
        value,
        isRisk: name === 'Gambling' || name === 'ATM',
    }));

    const riskFactors = [
        { title: 'Gambling', detected: customer.has_gambling === 1 },
        { title: 'Lending Apps', detected: customer.has_lending_apps === 1 },
        { title: 'Auto-Debits', detected: customer.failed_auto_debits > 0, label: 'Failed' },
    ];

    return (
        <div className="space-y-6">
            {/* 2x2 Chart Grid */}
            <div className="grid grid-cols-2 gap-4">
                {/* Account Balance Trend */}
                <div className="card p-5">
                    <h4 className="text-xs text-slate-grey uppercase tracking-wide mb-3">Account Balance Trend</h4>
                    <ResponsiveContainer width="100%" height={220}>
                        <AreaChart data={balanceHistory}>
                            <defs>
                                <linearGradient id="balanceGrad" x1="0" y1="0" x2="0" y2="1">
                                    <stop offset="5%" stopColor="#00AEEF" stopOpacity={0.8} />
                                    <stop offset="95%" stopColor="#00AEEF" stopOpacity={0} />
                                </linearGradient>
                            </defs>
                            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                            <XAxis dataKey="month" tick={{ fontSize: 10, fill: '#4A5C6D' }} />
                            <YAxis tick={{ fontSize: 10, fill: '#4A5C6D' }} />
                            <Tooltip formatter={(val) => `₹${val.toLocaleString('en-IN')}`} />
                            <Area type="monotone" dataKey="balance" stroke="#00AEEF" strokeWidth={2} fill="url(#balanceGrad)" />
                        </AreaChart>
                    </ResponsiveContainer>
                </div>

                {/* Credit Utilization Trend */}
                <div className="card p-5">
                    <h4 className="text-xs text-slate-grey uppercase tracking-wide mb-3">Credit Utilization Trend</h4>
                    {creditHistory.length > 0 ? (
                        <ResponsiveContainer width="100%" height={220}>
                            <LineChart data={creditHistory}>
                                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                                <XAxis dataKey="month" tick={{ fontSize: 10, fill: '#4A5C6D' }} />
                                <YAxis domain={[0, 100]} tick={{ fontSize: 10, fill: '#4A5C6D' }} />
                                <Tooltip formatter={(val) => `${val}%`} />
                                <ReferenceLine y={80} stroke="#D32F2F" strokeDasharray="6 4" strokeWidth={1.5} label={{ value: '80%', position: 'right', fontSize: 10, fill: '#D32F2F' }} />
                                <Line type="monotone" dataKey="utilization" stroke="#0D9488" strokeWidth={2} dot={{ r: 4, fill: '#0D9488' }} />
                            </LineChart>
                        </ResponsiveContainer>
                    ) : (
                        <div className="h-[220px] flex items-center justify-center text-sm text-slate-grey">
                            No credit card data
                        </div>
                    )}
                </div>

                {/* Spending by Category */}
                <div className="card p-5">
                    <h4 className="text-xs text-slate-grey uppercase tracking-wide mb-3">Spending by Category</h4>
                    <ResponsiveContainer width="100%" height={220}>
                        <BarChart data={categoryData}>
                            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                            <XAxis dataKey="name" tick={{ fontSize: 9, fill: '#4A5C6D' }} />
                            <YAxis tick={{ fontSize: 10, fill: '#4A5C6D' }} />
                            <Tooltip formatter={(val) => `₹${val.toLocaleString('en-IN')}`} labelFormatter={(label) => {
                                const item = categoryData.find(d => d.name === label);
                                return item ? item.fullName : label;
                            }} />
                            <Bar dataKey="value" radius={[4, 4, 0, 0]}>
                                {categoryData.map((entry, i) => (
                                    <motion.rect
                                        key={i}
                                        fill={entry.isRisk ? '#D32F2F' : '#00AEEF'}
                                    />
                                ))}
                            </Bar>
                        </BarChart>
                    </ResponsiveContainer>
                </div>

                {/* EMI Payment Delays */}
                <div className="card p-5">
                    <h4 className="text-xs text-slate-grey uppercase tracking-wide mb-3">EMI Payment Delays</h4>
                    <ResponsiveContainer width="100%" height={220}>
                        <AreaChart data={emiDelays}>
                            <defs>
                                <linearGradient id="delayGrad" x1="0" y1="0" x2="0" y2="1">
                                    <stop offset="5%" stopColor="#D32F2F" stopOpacity={0.6} />
                                    <stop offset="95%" stopColor="#D32F2F" stopOpacity={0} />
                                </linearGradient>
                            </defs>
                            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                            <XAxis dataKey="month" tick={{ fontSize: 10, fill: '#4A5C6D' }} />
                            <YAxis tick={{ fontSize: 10, fill: '#4A5C6D' }} label={{ value: 'Days', angle: -90, position: 'insideLeft', fontSize: 10, fill: '#4A5C6D' }} />
                            <Tooltip />
                            <Area type="monotone" dataKey="daysDelayed" stroke="#D32F2F" strokeWidth={2} fill="url(#delayGrad)" />
                        </AreaChart>
                    </ResponsiveContainer>
                </div>
            </div>

            {/* Risk Factor Cards */}
            <div className="grid grid-cols-3 gap-4">
                {riskFactors.map((factor, i) => (
                    <motion.div
                        key={factor.title}
                        initial={{ opacity: 0, y: 15 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: i * 0.1 }}
                        whileHover={{ y: -4, boxShadow: '0px 12px 30px rgba(0,0,0,0.08)' }}
                        className={`card p-5 border ${factor.detected ? 'border-risk-critical/20' : 'border-risk-safe/20'
                            }`}
                    >
                        <div className="flex items-center justify-between">
                            <div>
                                <p className="text-sm font-semibold text-oxford-blue">{factor.title}</p>
                                <p className={`text-xs mt-1 ${factor.detected ? 'text-risk-critical' : 'text-risk-safe'}`}>
                                    {factor.detected ? (factor.label || 'Detected') : 'None'}
                                </p>
                            </div>
                            {factor.detected ? (
                                <XCircle className="w-8 h-8 text-risk-critical" />
                            ) : (
                                <CheckCircle className="w-8 h-8 text-risk-safe" />
                            )}
                        </div>
                    </motion.div>
                ))}
            </div>
        </div>
    );
}
