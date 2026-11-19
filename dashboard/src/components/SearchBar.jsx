import { Search } from 'lucide-react';

export default function SearchBar({ value, onChange }) {
    return (
        <div className="relative w-80">
            <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-grey/50" />
            <input
                type="text"
                placeholder="Search by ID, name, or city..."
                value={value}
                onChange={e => onChange(e.target.value)}
                className="w-full pl-10 pr-4 py-2.5 rounded-xl text-sm text-oxford-blue bg-white/80 backdrop-blur-md border border-white/20 focus:outline-none focus:ring-2 focus:ring-sky-blue/30 focus:border-sky-blue placeholder:text-slate-grey/40"
                style={{ boxShadow: '0 4px 20px rgba(0,0,0,0.04)' }}
            />
        </div>
    );
}
