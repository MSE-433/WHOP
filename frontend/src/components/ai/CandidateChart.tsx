import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ReferenceLine,
  Cell,
  ResponsiveContainer,
} from 'recharts';
import type { ScoredCandidate } from '../../types/game';
import { formatCurrency } from '../../utils/formatters';

interface Props {
  candidates: ScoredCandidate[];
  baselineCost: number;
}

export function CandidateChart({ candidates, baselineCost }: Props) {
  if (candidates.length === 0) return null;

  const data = candidates.map((c, i) => ({
    name: c.description.length > 30 ? c.description.slice(0, 27) + '...' : c.description,
    fullName: c.description,
    expected: c.expected_total,
    p10: c.p10_total,
    p90: c.p90_total,
    delta: c.delta_vs_baseline,
    reasoning: c.reasoning,
    isTop: i === 0,
  }));

  return (
    <div className="space-y-2">
      <div className="text-xs text-gray-400 font-medium uppercase tracking-wide">
        Candidate Comparison
      </div>
      <ResponsiveContainer width="100%" height={Math.max(120, candidates.length * 40 + 40)}>
        <BarChart data={data} layout="vertical" margin={{ left: 10, right: 20, top: 5, bottom: 5 }}>
          <XAxis type="number" tick={{ fill: '#9ca3af', fontSize: 10 }} tickFormatter={(v: number) => `$${(v / 1000).toFixed(0)}k`} />
          <YAxis type="category" dataKey="name" tick={{ fill: '#9ca3af', fontSize: 10 }} width={120} />
          <Tooltip
            contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151', borderRadius: 8 }}
            labelStyle={{ color: '#e5e7eb', fontWeight: 600, marginBottom: 4 }}
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            formatter={(value: any, _name: any, entry: any) => {
              const d = entry.payload;
              const v = Number(value);
              return [
                <span key="v" className="text-xs">
                  {formatCurrency(v)}
                  <br />
                  <span className="text-gray-400">
                    Range: {formatCurrency(d.p10)} – {formatCurrency(d.p90)}
                  </span>
                  <br />
                  <span className={d.delta <= 0 ? 'text-green-400' : 'text-red-400'}>
                    Delta: {d.delta <= 0 ? '-' : '+'}
                    {formatCurrency(Math.abs(d.delta))}
                  </span>
                </span>,
                '',
              ];
            }}
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            labelFormatter={(_label: any, payload: any) =>
              payload?.[0]?.payload?.fullName || String(_label)
            }
          />
          {baselineCost > 0 && (
            <ReferenceLine x={baselineCost} stroke="#6b7280" strokeDasharray="4 4" label={{ value: 'Baseline', fill: '#6b7280', fontSize: 10, position: 'top' }} />
          )}
          <Bar dataKey="expected" radius={[0, 4, 4, 0]} barSize={20}>
            {data.map((entry, index) => (
              <Cell
                key={index}
                fill={entry.isTop ? '#6366f1' : '#4b5563'}
                fillOpacity={entry.isTop ? 1 : 0.7}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
