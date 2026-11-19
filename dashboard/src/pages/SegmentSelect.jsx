import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Users, CreditCard, ArrowRight } from 'lucide-react';
import { fetchStats } from '../api';

export default function SegmentSelect() {
    const navigate = useNavigate();
    const [allStats, setAllStats] = useState(null);
    const [ccStats, setCcStats] = useState(null);

    useEffect(() => {
        fetchStats('all').then(setAllStats);
        fetchStats('credit_card').then(setCcStats);
    }, []);

    const cards = [
        {
            key: 'all',
            title: 'All Users',
            description: 'Customers with debit card loans — including those with credit cards',
            icon: Users,
            count: allStats?.totalCustomers || '—',
            riskCount: allStats?.highRiskCount || 0,
            gradient: 'from-sky-blue/10 to-sky-blue/5',
            border: 'border-sky-blue/20',
            iconBg: 'bg-sky-blue/10',
            iconColor: 'text-sky-blue',
        },
        {
            key: 'credit_card',
            title: 'Credit Card Users',
            description: 'Only customers who hold a credit card — focused risk analysis',
            icon: CreditCard,
            count: ccStats?.totalCustomers || '—',
            riskCount: ccStats?.highRiskCount || 0,
            gradient: 'from-amber-500/10 to-orange-500/5',
            border: 'border-amber-500/20',
            iconBg: 'bg-amber-500/10',
            iconColor: 'text-amber-600',
        },
    ];

    return (
        <div className="min-h-screen bg-page-bg flex flex-col items-center justify-center p-8">
            {/* Logo */}
            <motion.div
                initial={{ opacity: 0, y: -20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.6 }}
                className="text-center mb-12"
            >
                <div className="flex items-center justify-center gap-3 mb-4">
                    <img src="/logo.png" alt="Drishti Logo" className="w-12 h-12 object-contain" />
                    <h1 className="text-4xl font-bold text-oxford-blue tracking-tight">DRISHTI</h1>
                </div>
                <p className="text-slate-grey text-lg">Financial Stress & Risk Intelligence Platform</p>
            </motion.div>

            {/* Segment Cards */}
            <div className="flex gap-8 max-w-4xl w-full">
                {cards.map((card, i) => (
                    <motion.div
                        key={card.key}
                        initial={{ opacity: 0, y: 30 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.2 + i * 0.15, type: 'spring', stiffness: 300, damping: 25 }}
                        whileHover={{ y: -8, scale: 1.02, boxShadow: '0px 20px 40px rgba(0,0,0,0.1)' }}
                        whileTap={{ scale: 0.98 }}
                        onClick={() => navigate(`/dashboard?segment=${card.key}`)}
                        className={`flex-1 card p-8 cursor-pointer bg-gradient-to-br ${card.gradient} border ${card.border} transition-colors group`}
                    >
                        <div className={`w-14 h-14 ${card.iconBg} rounded-xl flex items-center justify-center mb-6`}>
                            <card.icon className={`w-7 h-7 ${card.iconColor}`} />
                        </div>
                        <h2 className="text-2xl font-bold text-oxford-blue mb-2">{card.title}</h2>
                        <p className="text-slate-grey text-sm mb-6 leading-relaxed">{card.description}</p>

                        <div className="flex items-end justify-between">
                            <div>
                                <p className="text-4xl font-bold text-oxford-blue">{card.count}</p>
                                <p className="text-xs text-slate-grey mt-1">Total Profiles</p>
                            </div>
                            <div className="text-right">
                                <p className="text-2xl font-bold text-risk-critical">{card.riskCount}</p>
                                <p className="text-xs text-slate-grey mt-1">High Risk</p>
                            </div>
                        </div>

                        <div className="flex items-center gap-2 mt-6 text-sky-blue text-sm font-medium group-hover:gap-3 transition-all">
                            <span>Enter Dashboard</span>
                            <ArrowRight className="w-4 h-4" />
                        </div>
                    </motion.div>
                ))}
            </div>
        </div>
    );
}
