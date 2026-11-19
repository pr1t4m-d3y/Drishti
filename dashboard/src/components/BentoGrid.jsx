import { motion } from 'framer-motion';
import { AlertTriangle, CreditCard, Clock, XCircle } from 'lucide-react';

const CARDS = [
    { key: 'critical', title: 'CRITICAL RISK', icon: AlertTriangle, color: 'text-risk-critical', statKey: 'criticalCount', borderColor: 'border-risk-critical/20', hoverShadow: 'rgba(211,47,47,0.12)' },
    { key: 'high_credit_util', title: 'AVG CREDIT UTIL', icon: CreditCard, color: 'text-risk-warning', statKey: 'avgCreditUtil', suffix: '%', borderColor: 'border-risk-warning/20', hoverShadow: 'rgba(255,160,0,0.12)' },
    { key: 'late_payments', title: 'LATE PAYMENTS', icon: Clock, color: 'text-sky-blue', statKey: 'totalLatePayments', borderColor: 'border-sky-blue/20', hoverShadow: 'rgba(0,174,239,0.12)' },
    { key: 'failed_debits', title: 'FAILED AUTO-DEBITS', icon: XCircle, color: 'text-risk-critical', statKey: 'totalFailedDebits', borderColor: 'border-risk-critical/20', hoverShadow: 'rgba(211,47,47,0.12)' },
];

export default function BentoGrid({ stats, activeFilter, onFilterClick }) {
    return (
        <div className="grid grid-cols-4 gap-4">
            {CARDS.map((card, i) => {
                const isActive = activeFilter === card.key;
                const value = stats?.[card.statKey] ?? '—';
                return (
                    <motion.div
                        key={card.key}
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: i * 0.1, type: 'spring', stiffness: 300, damping: 20 }}
                        whileHover={{ y: -8, scale: 1.02, boxShadow: `0px 20px 40px ${card.hoverShadow}` }}
                        whileTap={{ scale: 0.98 }}
                        onClick={() => onFilterClick(card.key)}
                        className={`card p-6 cursor-pointer border transition-all ${isActive
                                ? 'border-sky-blue ring-2 ring-sky-blue/20'
                                : card.borderColor
                            }`}
                    >
                        <div className="flex items-center justify-between mb-4">
                            <p className="text-xs font-semibold text-slate-grey uppercase tracking-wider">{card.title}</p>
                            <card.icon className={`w-5 h-5 ${card.color} opacity-60`} />
                        </div>
                        <p className={`text-3xl font-bold ${card.color}`}>
                            {value}{card.suffix || ''}
                        </p>
                    </motion.div>
                );
            })}
        </div>
    );
}
