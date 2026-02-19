import { motion } from 'framer-motion';

export default function GaugeChart({ score, size = 200 }) {
    const radius = (size - 20) / 2;
    const cx = size / 2;
    const cy = size / 2 + 10;

    // Semi-circle from 180° to 0° (left to right)
    const startAngle = Math.PI;
    const endAngle = 0;
    const scoreAngle = startAngle - (score / 100) * Math.PI;

    // Arc path
    const arcPath = (angle1, angle2, r) => {
        const x1 = cx + r * Math.cos(angle1);
        const y1 = cy - r * Math.sin(angle1);
        const x2 = cx + r * Math.cos(angle2);
        const y2 = cy - r * Math.sin(angle2);
        const largeArc = angle1 - angle2 > Math.PI ? 1 : 0;
        return `M ${x1} ${y1} A ${r} ${r} 0 ${largeArc} 1 ${x2} ${y2}`;
    };

    // Needle endpoint
    const needleAngle = scoreAngle;
    const needleLen = radius - 15;
    const nx = cx + needleLen * Math.cos(needleAngle);
    const ny = cy - needleLen * Math.sin(needleAngle);

    // Risk segment + color
    let riskLabel, riskColor;
    if (score >= 75) { riskLabel = 'CRITICAL'; riskColor = '#D32F2F'; }
    else if (score >= 50) { riskLabel = 'HIGH RISK'; riskColor = '#D32F2F'; }
    else if (score >= 30) { riskLabel = 'MEDIUM RISK'; riskColor = '#FFA000'; }
    else { riskLabel = 'SAFE'; riskColor = '#388E3C'; }

    return (
        <div className="flex flex-col items-center">
            <svg width={size} height={size / 2 + 40} viewBox={`0 0 ${size} ${size / 2 + 40}`}>
                {/* Background arc */}
                <path
                    d={arcPath(startAngle, endAngle, radius)}
                    fill="none"
                    stroke="#E5E7EB"
                    strokeWidth="12"
                    strokeLinecap="round"
                />
                {/* Score arc */}
                <motion.path
                    d={arcPath(startAngle, scoreAngle, radius)}
                    fill="none"
                    stroke={riskColor}
                    strokeWidth="12"
                    strokeLinecap="round"
                    initial={{ pathLength: 0 }}
                    animate={{ pathLength: 1 }}
                    transition={{ duration: 1.5, ease: 'easeOut' }}
                />
                {/* Needle */}
                <motion.line
                    x1={cx}
                    y1={cy}
                    x2={nx}
                    y2={ny}
                    stroke="#001C38"
                    strokeWidth="2.5"
                    strokeLinecap="round"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: 0.8 }}
                />
                <circle cx={cx} cy={cy} r="5" fill="#001C38" />

                {/* Score text */}
                <text x={cx} y={cy - 15} textAnchor="middle" className="text-2xl font-bold" fill="#001C38">
                    {score.toFixed(1)}
                </text>
            </svg>
            <span className="text-xs font-semibold uppercase tracking-wider mt-1" style={{ color: riskColor }}>
                {riskLabel}
            </span>
        </div>
    );
}
