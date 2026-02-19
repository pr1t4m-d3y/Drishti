import { motion } from 'framer-motion';

export default function WalletCard({ type, last4, name }) {
    const isCredit = type === 'credit';

    return (
        <motion.div
            initial={{ opacity: 0, y: 15 }}
            animate={{ opacity: 1, y: 0 }}
            whileHover={{ y: -4, boxShadow: '0px 15px 30px rgba(0,0,0,0.15)' }}
            className={`rounded-2xl p-5 text-white relative overflow-hidden h-[180px] flex flex-col justify-between ${isCredit
                    ? 'bg-gradient-to-br from-amber-500 via-yellow-500 to-amber-600'
                    : 'bg-gradient-to-br from-sky-blue via-blue-500 to-blue-600'
                }`}
        >
            {/* Background pattern */}
            <div className="absolute inset-0 opacity-10">
                <div className="absolute -right-8 -top-8 w-40 h-40 rounded-full border-[20px] border-white/20" />
                <div className="absolute -right-4 top-4 w-32 h-32 rounded-full border-[15px] border-white/10" />
            </div>

            <div className="flex justify-between items-start relative z-1">
                <div>
                    <p className="text-[10px] uppercase tracking-[3px] opacity-70">{isCredit ? 'Credit Card' : 'Debit Card'}</p>
                </div>
                <div className="text-right">
                    <p className="text-xs font-bold tracking-wider opacity-80">{isCredit ? 'GOLD' : 'PLATINUM'}</p>
                </div>
            </div>

            <div className="relative z-1">
                <p className="text-lg font-mono tracking-[4px] mb-3">
                    XXXX XXXX XXXX {last4 || '0000'}
                </p>
                <p className="text-xs uppercase tracking-wider opacity-80">{name}</p>
            </div>
        </motion.div>
    );
}
