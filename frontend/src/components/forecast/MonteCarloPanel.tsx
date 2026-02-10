import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Line,
} from 'recharts';
import type { MonteCarloSummary } from '../../types/game';
import { formatCurrency } from '../../utils/formatters';

interface Props {
  mc: MonteCarloSummary;
}

export function MonteCarloPanel({ mc }: Props) {
  // Build chart data from expected snapshots — show p10/p50/p90 band
  const chartData = mc.expected_snapshots.map((snap) => ({
    round: snap.round_number,
    cumulative: snap.cumulative_financial + snap.cumulative_quality,
  }));

  const totalExpected = mc.expected_financial + mc.expected_quality;
  const bestCase = mc.p10_financial + mc.p10_quality;
  const worstCase = mc.p90_financial + mc.p90_quality;
  const riskRange = worstCase - bestCase;
  const median = mc.p50_financial + mc.p50_quality;

  const stats = [
    { label: 'Expected', value: totalExpected, color: 'text-indigo-400' },
    { label: 'Best (p10)', value: bestCase, color: 'text-green-400' },
    { label: 'Median (p50)', value: median, color: 'text-blue-400' },
    { label: 'Worst (p90)', value: worstCase, color: 'text-red-400' },
  ];

  return (
    <div className="space-y-4">
      <div>
        <div className="text-xs text-gray-400 font-medium uppercase tracking-wide mb-2">
          Monte Carlo Forecast ({mc.num_simulations} simulations, {mc.horizon} rounds)
        </div>

        {/* Stats grid */}
        <div className="grid grid-cols-2 gap-2 mb-3">
          {stats.map((s) => (
            <div key={s.label} className="bg-gray-800/50 rounded-lg p-2">
              <div className="text-[10px] text-gray-500 uppercase">{s.label}</div>
              <div className={`text-sm font-semibold ${s.color}`}>{formatCurrency(s.value)}</div>
            </div>
          ))}
        </div>

        {/* Risk range badge */}
        <div className="bg-gray-800/50 rounded-lg p-2 mb-3">
          <div className="text-[10px] text-gray-500 uppercase">Risk Range (p90 − p10)</div>
          <div className={`text-sm font-semibold ${riskRange > 5000 ? 'text-red-400' : riskRange > 2000 ? 'text-amber-400' : 'text-green-400'}`}>
            {formatCurrency(riskRange)}
          </div>
        </div>
      </div>

      {/* Cost trajectory chart */}
      {chartData.length > 0 && (
        <div>
          <div className="text-xs text-gray-400 font-medium mb-1">Cumulative Cost Trajectory</div>
          <ResponsiveContainer width="100%" height={160}>
            <AreaChart data={chartData} margin={{ left: 10, right: 10, top: 5, bottom: 5 }}>
              <defs>
                <linearGradient id="mcGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#6366f1" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#6366f1" stopOpacity={0.05} />
                </linearGradient>
              </defs>
              <XAxis dataKey="round" tick={{ fill: '#6b7280', fontSize: 10 }} label={{ value: 'Round', position: 'insideBottom', offset: -2, fill: '#6b7280', fontSize: 10 }} />
              <YAxis tick={{ fill: '#6b7280', fontSize: 10 }} tickFormatter={(v: number) => `$${(v / 1000).toFixed(0)}k`} />
              <Tooltip
                contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151', borderRadius: 8, fontSize: 12 }}
                // eslint-disable-next-line @typescript-eslint/no-explicit-any
                formatter={(value: any) => [formatCurrency(Number(value)), 'Cost']}
                labelFormatter={(label) => `Round ${label}`}
              />
              <Area type="monotone" dataKey="cumulative" stroke="#6366f1" fill="url(#mcGrad)" strokeWidth={2} />
              <Line type="monotone" dataKey="cumulative" stroke="#6366f1" strokeWidth={2} dot={false} />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Risk flags */}
      {mc.risk_flags.length > 0 && (
        <div className="space-y-1">
          <div className="text-xs text-gray-400 font-medium">Risk Flags</div>
          {mc.risk_flags.map((flag, i) => (
            <div key={i} className="text-xs text-amber-400 bg-amber-900/20 rounded px-2 py-1">
              {flag}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
