import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  ReferenceArea,
  Legend,
} from 'recharts';
import type { ForecastRoundSnapshot } from '../../types/game';

const DEPT_CHART_COLORS: Record<string, string> = {
  er: '#ef4444',
  surgery: '#3b82f6',
  cc: '#a855f7',
  sd: '#22c55e',
};

const DEPT_LABELS: Record<string, string> = {
  er: 'ER',
  surgery: 'Surgery',
  cc: 'CC',
  sd: 'Step Down',
};

interface Props {
  snapshots: ForecastRoundSnapshot[];
}

export function ForecastTimeline({ snapshots }: Props) {
  if (snapshots.length === 0) return null;

  const data = snapshots.map((snap) => {
    const row: Record<string, number> = { round: snap.round_number };
    for (const [deptId, d] of Object.entries(snap.departments)) {
      row[deptId] = d.census;
    }
    return row;
  });

  const deptIds = Object.keys(snapshots[0]?.departments ?? {});

  return (
    <div>
      <div className="text-xs text-gray-400 font-medium uppercase tracking-wide mb-2">
        Predicted Census by Department
      </div>
      <ResponsiveContainer width="100%" height={180}>
        <LineChart data={data} margin={{ left: 10, right: 10, top: 5, bottom: 5 }}>
          <XAxis dataKey="round" tick={{ fill: '#6b7280', fontSize: 10 }} />
          <YAxis tick={{ fill: '#6b7280', fontSize: 10 }} />
          <Tooltip
            contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151', borderRadius: 8, fontSize: 12 }}
            labelFormatter={(label) => `Round ${label}`}
          />
          <Legend
            wrapperStyle={{ fontSize: 11 }}
            formatter={(value: string) => DEPT_LABELS[value] || value}
          />
          {/* Bed capacity reference areas */}
          <ReferenceArea y1={9} y2={9} stroke="#3b82f680" strokeDasharray="4 4" label={{ value: 'Surg cap', fill: '#3b82f680', fontSize: 9, position: 'right' }} />
          <ReferenceArea y1={18} y2={18} stroke="#a855f780" strokeDasharray="4 4" label={{ value: 'CC cap', fill: '#a855f780', fontSize: 9, position: 'right' }} />
          {deptIds.map((deptId) => (
            <Line
              key={deptId}
              type="monotone"
              dataKey={deptId}
              stroke={DEPT_CHART_COLORS[deptId] || '#888'}
              strokeWidth={2}
              dot={false}
              name={deptId}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
