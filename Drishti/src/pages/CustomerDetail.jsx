import { useEffect, useState } from 'react';
import { useParams, useSearchParams, useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { ArrowLeft, Shield } from 'lucide-react';
import { fetchCustomer } from '../api';
import WalletCard from '../components/WalletCard';
import ProfileTab from '../components/customer/ProfileTab';
import FinancialTab from '../components/customer/FinancialTab';
import TransactionsTab from '../components/customer/TransactionsTab';
import InterventionTab from '../components/customer/InterventionTab';

const TABS = ['Profile', 'Financial Analysis', 'Transactions', 'Intervention'];

export default function CustomerDetail() {
    const { id } = useParams();
    const [searchParams] = useSearchParams();
    const navigate = useNavigate();
    const segment = searchParams.get('segment') || 'all';

    const [customer, setCustomer] = useState(null);
    const [activeTab, setActiveTab] = useState(0);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        setLoading(true);
        fetchCustomer(id).then(data => {
            setCustomer(data);
            setLoading(false);
        });
    }, [id]);

    if (loading) {
        return (
            <div className="min-h-screen bg-page-bg flex items-center justify-center">
                <div className="text-slate-grey">Loading customer data...</div>
            </div>
        );
    }

    if (!customer) {
        return (
            <div className="min-h-screen bg-page-bg flex items-center justify-center">
                <div className="text-risk-critical">Customer not found</div>
            </div>
        );
    }

    const details = [
        { label: 'Age', value: customer.age },
        { label: 'Gender', value: customer.gender },
        { label: 'City', value: customer.city },
        { label: 'EMI Amount', value: `₹${customer.emi_amount?.toLocaleString('en-IN')}` },
        { label: 'Account Age', value: `${customer.account_age} yrs` },
        { label: 'Loan Type', value: customer.loan_type },
    ];

    return (
        <div className="min-h-screen bg-page-bg flex">
            {/* Left Static Panel - 30% */}
            <aside className="w-[30%] p-6 flex flex-col gap-6 overflow-y-auto max-h-screen">
                {/* Back Button */}
                <button
                    onClick={() => navigate(`/dashboard?segment=${segment}`)}
                    className="flex items-center gap-2 text-sm text-slate-grey hover:text-sky-blue transition-colors self-start"
                >
                    <ArrowLeft className="w-4 h-4" />
                    Back to Dashboard
                </button>

                {/* Digital Wallet */}
                <div className="flex flex-col gap-4">
                    <WalletCard
                        type="debit"
                        last4={customer.card_last4_debit}
                        name={customer.name}
                    />
                    {customer.has_credit_card === 1 && (
                        <WalletCard
                            type="credit"
                            last4={customer.card_last4_credit}
                            name={customer.name}
                        />
                    )}
                </div>

                {/* Live Balances */}
                <div className="card p-5">
                    <h4 className="text-xs text-slate-grey uppercase tracking-wide mb-3">Live Balances</h4>
                    <div className="space-y-3">
                        <div className="flex justify-between items-center">
                            <span className="text-sm text-slate-grey">Debit Balance</span>
                            <span className="font-bold text-oxford-blue">₹{customer.debit_balance?.toLocaleString('en-IN')}</span>
                        </div>
                        {customer.has_credit_card === 1 && (
                            <div className="flex justify-between items-center">
                                <span className="text-sm text-slate-grey">Credit Limit Remaining</span>
                                <span className="font-bold text-oxford-blue">
                                    ₹{(customer.credit_limit - customer.credit_used)?.toLocaleString('en-IN')}
                                </span>
                            </div>
                        )}
                    </div>
                </div>

                {/* Customer Details */}
                <div className="card p-5 flex-1">
                    <h4 className="text-xs text-slate-grey uppercase tracking-wide mb-3">Customer Details</h4>
                    <div className="space-y-3 overflow-y-auto">
                        {details.map(d => (
                            <div key={d.label} className="flex justify-between items-center py-1 border-b border-slate-50 last:border-0">
                                <span className="text-sm text-slate-grey">{d.label}</span>
                                <span className="text-sm font-medium text-oxford-blue">{d.value}</span>
                            </div>
                        ))}
                    </div>
                </div>
            </aside>

            {/* Right Panel - 70% */}
            <main className="flex-1 p-6 overflow-y-auto max-h-screen">
                {/* Tab Navigation */}
                <div className="flex items-center border-b border-slate-200 mb-6">
                    {TABS.map((tab, i) => (
                        <button
                            key={tab}
                            onClick={() => setActiveTab(i)}
                            className="relative px-5 py-3 text-sm font-medium transition-colors"
                            style={{ color: activeTab === i ? '#00AEEF' : '#4A5C6D' }}
                        >
                            {tab}
                            {activeTab === i && (
                                <motion.div
                                    layoutId="tab-underline"
                                    className="absolute bottom-0 left-0 right-0 h-0.5 bg-sky-blue"
                                    transition={{ type: 'spring', stiffness: 500, damping: 30 }}
                                />
                            )}
                        </button>
                    ))}
                </div>

                {/* Tab Content */}
                <AnimatePresence mode="wait">
                    <motion.div
                        key={activeTab}
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: -10 }}
                        transition={{ duration: 0.2 }}
                    >
                        {activeTab === 0 && <ProfileTab customer={customer} />}
                        {activeTab === 1 && <FinancialTab customer={customer} />}
                        {activeTab === 2 && <TransactionsTab customerId={customer.id} />}
                        {activeTab === 3 && <InterventionTab customer={customer} />}
                    </motion.div>
                </AnimatePresence>
            </main>
        </div>
    );
}
