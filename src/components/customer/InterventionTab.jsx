import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { Heart, BookOpen, Bell, CreditCard, ChevronRight } from 'lucide-react';
import GaugeChart from '../GaugeChart';
import { createIntervention, fetchInterventions } from '../../api';

const SUPPORT_CARDS = [
    { title: 'Financial Counseling', icon: Heart, description: 'Connect with advisor', accent: 'sky-blue' },
    { title: 'Financial Literacy', icon: BookOpen, description: 'Education content', accent: 'sky-blue' },
    { title: 'Spending Alert', icon: Bell, description: 'Enable notifications', accent: 'sky-blue' },
    { title: 'Limit Reduction', icon: CreditCard, description: 'Reduce credit limit', accent: 'risk-critical' },
];

export default function InterventionTab({ customer }) {
    const [interventions, setInterventions] = useState([]);
    const [saving, setSaving] = useState(false);

    useEffect(() => {
        fetchInterventions(customer.id).then(setInterventions);
    }, [customer.id]);

    const handleAction = async (action) => {
        setSaving(true);
        await createIntervention(customer.id, action, 'Risk Analyst');
        const updated = await fetchInterventions(customer.id);
        setInterventions(updated);
        setSaving(false);
    };

    const formatDate = (iso) => {
        const d = new Date(iso);
        return d.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' });
    };

    return (
        <div className="space-y-6">
            {/* Risk Gauge - Large Centered */}
            <div className="card p-8 flex flex-col items-center">
                <h4 className="text-xs text-slate-grey uppercase tracking-wide mb-4">Current Risk Assessment</h4>
                <GaugeChart score={customer.risk_score} size={240} />
            </div>

            {/* Action Buttons */}
            <div className="flex gap-3">
                <motion.button
                    whileHover={{ y: -2, scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                    onClick={() => handleAction('Payment Holiday Offered')}
                    disabled={saving}
                    className="flex-1 py-3 px-4 border-2 border-sky-blue text-sky-blue rounded-xl text-sm font-semibold hover:bg-sky-blue/5 transition-colors disabled:opacity-50"
                >
                    Offer Payment Holiday
                </motion.button>
                <motion.button
                    whileHover={{ y: -2, scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                    onClick={() => handleAction('EMI Restructuring Suggested')}
                    disabled={saving}
                    className="flex-1 py-3 px-4 bg-sky-blue text-white rounded-xl text-sm font-semibold hover:bg-sky-blue/90 transition-colors disabled:opacity-50"
                >
                    Suggest EMI Restructuring
                </motion.button>
                <motion.button
                    whileHover={{ y: -2, scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                    onClick={() => handleAction('Advisory Message Sent')}
                    disabled={saving}
                    className="flex-1 py-3 px-4 border-2 border-sky-blue text-sky-blue rounded-xl text-sm font-semibold hover:bg-sky-blue/5 transition-colors disabled:opacity-50"
                >
                    Send Advisory Message
                </motion.button>
            </div>

            {/* Support Cards Grid */}
            <div className="grid grid-cols-4 gap-3">
                {SUPPORT_CARDS.map((card, i) => (
                    <motion.div
                        key={card.title}
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: i * 0.08 }}
                        whileHover={{ y: -4, boxShadow: '0px 12px 30px rgba(0,0,0,0.08)' }}
                        onClick={() => handleAction(card.title)}
                        className={`card p-4 cursor-pointer border ${card.accent === 'risk-critical' ? 'border-risk-critical/20' : 'border-slate-100'
                            }`}
                    >
                        <div className={`w-10 h-10 rounded-lg flex items-center justify-center mb-3 ${card.accent === 'risk-critical' ? 'bg-risk-critical/10' : 'bg-sky-blue/10'
                            }`}>
                            <card.icon className={`w-5 h-5 ${card.accent === 'risk-critical' ? 'text-risk-critical' : 'text-sky-blue'}`} />
                        </div>
                        <p className="text-sm font-semibold text-oxford-blue">{card.title}</p>
                        <p className="text-xs text-slate-grey mt-1">{card.description}</p>
                    </motion.div>
                ))}
            </div>

            {/* Intervention History */}
            <div className="card overflow-hidden">
                <div className="px-5 py-3 border-b border-slate-100">
                    <h4 className="text-sm font-semibold text-oxford-blue">Intervention History</h4>
                </div>
                <div className="max-h-[300px] overflow-y-auto">
                    <table className="w-full">
                        <thead className="sticky top-0">
                            <tr className="bg-slate-50 text-xs text-slate-grey uppercase tracking-wider">
                                <th className="px-5 py-2.5 text-left font-semibold">Date</th>
                                <th className="px-5 py-2.5 text-left font-semibold">Action Taken</th>
                                <th className="px-5 py-2.5 text-left font-semibold">Status</th>
                                <th className="px-5 py-2.5 text-left font-semibold">Analyst</th>
                            </tr>
                        </thead>
                        <tbody>
                            {interventions.length === 0 ? (
                                <tr><td colSpan="4" className="px-5 py-8 text-center text-sm text-slate-grey">No interventions recorded</td></tr>
                            ) : (
                                interventions.map((int, i) => (
                                    <tr key={int.id} className={`border-b border-slate-50 text-sm ${i % 2 === 0 ? 'bg-white' : 'bg-slate-50/30'}`}>
                                        <td className="px-5 py-3 text-slate-grey text-xs">{formatDate(int.date)}</td>
                                        <td className="px-5 py-3 font-medium text-oxford-blue">{int.action}</td>
                                        <td className="px-5 py-3">
                                            <span className={`px-2 py-0.5 rounded text-xs font-semibold ${int.status === 'Viewed' ? 'bg-risk-safe/10 text-risk-safe' : 'bg-sky-blue/10 text-sky-blue'
                                                }`}>{int.status}</span>
                                        </td>
                                        <td className="px-5 py-3 text-slate-grey">{int.analyst_name}</td>
                                    </tr>
                                ))
                            )}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
}
