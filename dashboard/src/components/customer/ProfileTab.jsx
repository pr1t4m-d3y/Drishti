import { motion } from 'framer-motion';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';
import { Coins, TrendingUp, Gem } from 'lucide-react';
import GaugeChart from '../GaugeChart';

const DONUT_COLORS = ['#00AEEF', '#0088CC', '#006699', '#004466', '#002233', '#FFA000', '#D32F2F'];

const MetricCard = ({ title, value, color = 'text-oxford-blue' }) => (
    <motion.div
        whileHover={{ y: -4, scale: 1.02, boxShadow: '0px 12px 30px rgba(0,0,0,0.08)' }}
        className="card p-4 border border-slate-100"
    >
        <p className="text-xs text-slate-grey uppercase tracking-wide mb-1">{title}</p>
        <p className={`text-lg font-bold ${color}`}>{value}</p>
    </motion.div>
);

export default function ProfileTab({ customer }) {
    const investments = customer.investments || [];
    const moneyFlow = customer.moneyFlow || [];
    const expenseBreakdown = customer.expenseBreakdown || {};
    const hasInvestments = investments.length > 0;

    // Expense donut data
    const donutData = Object.entries(expenseBreakdown).map(([name, value]) => ({ name, value }));

    // Expense velocity
    const monthlyExpense = customer.expenses || 0;
    const dailyExpense = Math.round(monthlyExpense / 30);
    const weeklyExpense = Math.round(monthlyExpense / 4);

    // Recent transactions placeholder (last 3 from money flow)
    const recentActivity = [
        { merchant: 'EMI Payment', amount: -customer.emi_amount, category: 'EMI' },
        { merchant: 'Salary Credit', amount: customer.income, category: 'Income' },
        { merchant: 'Expenses', amount: -Math.round(monthlyExpense * 0.3), category: 'Shopping' },
    ];

    return (
        <div className="space-y-6">
            {/* Top Row: 5 Metric Cards */}
            <div className="grid grid-cols-5 gap-3">
                <MetricCard title="Income" value={`₹${customer.income?.toLocaleString('en-IN')}`} />
                <MetricCard
                    title="Late Payments"
                    value={`${customer.late_payments} / 24`}
                    color={customer.late_payments > 0 ? 'text-risk-critical' : 'text-risk-safe'}
                />
                <MetricCard title="Expenses" value={`₹${customer.expenses?.toLocaleString('en-IN')}`} />
                <MetricCard title="Loan Type" value={customer.loan_type} />
                <MetricCard title="Loan Amount" value={`₹${customer.loan_amount?.toLocaleString('en-IN')}`} />
            </div>

            {/* Middle Row: Gauge + Money Flow + Investments */}
            <div className="grid grid-cols-12 gap-4">
                {/* Risk Gauge - 30% */}
                <div className="col-span-3 card p-5 flex flex-col items-center justify-center">
                    <h4 className="text-xs text-slate-grey uppercase tracking-wide mb-3">Risk Score</h4>
                    <GaugeChart score={customer.risk_score} size={180} />
                </div>

                {/* Money Flow Chart - expands if no investments */}
                <div className={`${hasInvestments ? 'col-span-5' : 'col-span-9'} card p-5`}>
                    <h4 className="text-xs text-slate-grey uppercase tracking-wide mb-3">Money Flow (3 Months)</h4>
                    <ResponsiveContainer width="100%" height={200}>
                        <LineChart data={moneyFlow}>
                            <defs>
                                <linearGradient id="incomeGrad" x1="0" y1="0" x2="0" y2="1">
                                    <stop offset="5%" stopColor="#00AEEF" stopOpacity={0.8} />
                                    <stop offset="95%" stopColor="#00AEEF" stopOpacity={0} />
                                </linearGradient>
                            </defs>
                            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                            <XAxis dataKey="month" tick={{ fontSize: 11, fill: '#4A5C6D' }} />
                            <YAxis tick={{ fontSize: 11, fill: '#4A5C6D' }} />
                            <Tooltip />
                            <Line type="monotone" dataKey="income" stroke="#00AEEF" strokeWidth={2} dot={{ r: 4 }} name="Income" />
                            <Line type="monotone" dataKey="expenses" stroke="#D32F2F" strokeWidth={2} dot={{ r: 4 }} name="Expenses" />
                        </LineChart>
                    </ResponsiveContainer>
                </div>

                {/* Investments - only if exists */}
                {hasInvestments && (
                    <div className="col-span-4 card p-5">
                        <h4 className="text-xs text-slate-grey uppercase tracking-wide mb-3">Investments</h4>
                        <div className="space-y-3">
                            {investments.map((inv, i) => (
                                <motion.div
                                    key={i}
                                    initial={{ opacity: 0, x: 10 }}
                                    animate={{ opacity: 1, x: 0 }}
                                    transition={{ delay: i * 0.1 }}
                                    className="flex items-center gap-3 p-2 rounded-lg hover:bg-slate-50 transition-colors"
                                >
                                    <div className="w-9 h-9 bg-sky-blue/10 rounded-lg flex items-center justify-center">
                                        <Gem className="w-4 h-4 text-sky-blue" />
                                    </div>
                                    <div className="flex-1">
                                        <p className="text-sm font-medium text-oxford-blue">{inv.type}</p>
                                        <p className="text-xs text-slate-grey">₹{inv.amount?.toLocaleString('en-IN')}</p>
                                    </div>
                                </motion.div>
                            ))}
                        </div>
                    </div>
                )}
            </div>

            {/* Bottom Row: Donut + Velocity + Recent Activity */}
            <div className="grid grid-cols-3 gap-4">
                {/* Expenses Donut */}
                <div className="card p-5">
                    <h4 className="text-xs text-slate-grey uppercase tracking-wide mb-3">All Expenses</h4>
                    <ResponsiveContainer width="100%" height={180}>
                        <PieChart>
                            <Pie
                                data={donutData}
                                cx="50%"
                                cy="50%"
                                innerRadius={50}
                                outerRadius={75}
                                paddingAngle={2}
                                dataKey="value"
                            >
                                {donutData.map((_, i) => (
                                    <Cell key={i} fill={DONUT_COLORS[i % DONUT_COLORS.length]} />
                                ))}
                            </Pie>
                            <Tooltip formatter={(val) => `₹${val.toLocaleString('en-IN')}`} />
                        </PieChart>
                    </ResponsiveContainer>
                    <div className="flex flex-wrap gap-2 mt-2">
                        {donutData.slice(0, 4).map((d, i) => (
                            <span key={d.name} className="text-[10px] text-slate-grey flex items-center gap-1">
                                <span className="w-2 h-2 rounded-full" style={{ background: DONUT_COLORS[i] }} />
                                {d.name}
                            </span>
                        ))}
                    </div>
                </div>

                {/* Expense Velocity */}
                <div className="card p-5">
                    <h4 className="text-xs text-slate-grey uppercase tracking-wide mb-3">Expense Velocity</h4>
                    <div className="space-y-4 mt-4">
                        {[
                            { label: 'Daily', value: dailyExpense },
                            { label: 'Weekly', value: weeklyExpense },
                            { label: 'Monthly', value: monthlyExpense },
                        ].map(item => (
                            <div key={item.label} className="flex justify-between items-center py-2 border-b border-slate-50 last:border-0">
                                <span className="text-sm text-slate-grey">{item.label}</span>
                                <span className="text-sm font-bold text-oxford-blue">₹{item.value.toLocaleString('en-IN')}</span>
                            </div>
                        ))}
                    </div>
                </div>

                {/* Recent Activity */}
                <div className="card p-5">
                    <h4 className="text-xs text-slate-grey uppercase tracking-wide mb-3">Recent Activity</h4>
                    <div className="space-y-3 mt-2">
                        {recentActivity.map((tx, i) => (
                            <div key={i} className="flex items-center gap-3 py-2 border-b border-slate-50 last:border-0">
                                <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${tx.amount > 0 ? 'bg-risk-safe/10' : 'bg-risk-critical/10'
                                    }`}>
                                    {tx.amount > 0 ? (
                                        <TrendingUp className="w-4 h-4 text-risk-safe" />
                                    ) : (
                                        <Coins className="w-4 h-4 text-risk-critical" />
                                    )}
                                </div>
                                <div className="flex-1">
                                    <p className="text-sm font-medium text-oxford-blue">{tx.merchant}</p>
                                    <p className="text-xs text-slate-grey">{tx.category}</p>
                                </div>
                                <span className={`text-sm font-mono font-semibold ${tx.amount > 0 ? 'text-risk-safe' : 'text-risk-critical'}`}>
                                    {tx.amount > 0 ? '+' : ''}₹{Math.abs(tx.amount).toLocaleString('en-IN')}
                                </span>
                            </div>
                        ))}
                    </div>
                </div>
            </div>
        </div>
    );
}
