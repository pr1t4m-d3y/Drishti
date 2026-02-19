import { useEffect, useState, useCallback } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import Sidebar from '../components/Sidebar';
import SearchBar from '../components/SearchBar';
import BentoGrid from '../components/BentoGrid';
import CustomerTable from '../components/CustomerTable';
import { fetchStats, fetchCustomers } from '../api';

export default function Dashboard() {
    const [searchParams] = useSearchParams();
    const navigate = useNavigate();
    const segment = searchParams.get('segment') || 'all';

    const [stats, setStats] = useState(null);
    const [customers, setCustomers] = useState([]);
    const [total, setTotal] = useState(0);
    const [search, setSearch] = useState('');
    const [riskFilter, setRiskFilter] = useState(null);
    const [activeFilter, setActiveFilter] = useState(null);
    const [selectedCustomer, setSelectedCustomer] = useState('');
    const [loading, setLoading] = useState(true);

    const loadData = useCallback(async () => {
        setLoading(true);
        try {
            const [statsData, custData] = await Promise.all([
                fetchStats(segment),
                fetchCustomers({ segment, risk: riskFilter, search, filter: activeFilter, limit: 1000 }),
            ]);
            setStats(statsData);
            setCustomers(custData.customers);
            setTotal(custData.total);
        } catch (e) {
            console.error('Failed to load data', e);
        }
        setLoading(false);
    }, [segment, riskFilter, search, activeFilter]);

    useEffect(() => {
        loadData();
    }, [loadData]);

    const handleBentoClick = (filterKey) => {
        setActiveFilter(prev => prev === filterKey ? null : filterKey);
    };

    const handleCustomerSelect = (id) => {
        if (id) navigate(`/customer/${id}?segment=${segment}`);
    };

    const handleRiskFilter = (risk) => {
        setRiskFilter(prev => prev === risk ? null : risk);
    };

    return (
        <div className="flex min-h-screen bg-page-bg">
            {/* Left Sidebar */}
            <Sidebar
                segment={segment}
                stats={stats}
                customers={customers}
                selectedCustomer={selectedCustomer}
                onCustomerSelect={handleCustomerSelect}
                riskFilter={riskFilter}
                onRiskFilter={handleRiskFilter}
            />

            {/* Right Content */}
            <main className="flex-1 ml-[25%] p-8 overflow-y-auto">
                {/* Search Bar */}
                <div className="flex justify-end mb-6">
                    <SearchBar value={search} onChange={setSearch} />
                </div>

                {/* Bento Grid */}
                <BentoGrid stats={stats} activeFilter={activeFilter} onFilterClick={handleBentoClick} />

                {/* Customer Table */}
                <div className="mt-6">
                    <CustomerTable
                        customers={customers}
                        total={total}
                        loading={loading}
                        segment={segment}
                    />
                </div>
            </main>
        </div>
    );
}
