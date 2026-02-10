import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ReferenceLine,
} from 'recharts';
import type { CapacityForecastEntry } from '../../types/game';

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
  capacityForecast: Record<string, CapacityForecastEntry[]>;
}

export function CapacityChart({ capacityForecast }: Props) {
  const deptIds = Object.keys(capacityForecast);
  if (deptIds.length === 0) return null;

  // Show net flow per dept
  const rounds = capacityForecast[deptIds[0]]?.map((e) => e.round) ?? [];
  const netData = rounds.map((rn) => {
    const row: Record<string, number> = { round: rn };
    for (const deptId of deptIds) {
      const entry = capacityForecast[deptId]?.find((e) => e.round === rn);
      if (entry) {
        row[deptId] = entry.net_flow;
      }
    }
    return row;
  });

  return (
    <div>
      <div className="text-xs text-gray-400 font-medium uppercase tracking-wide mb-2">
        Net Patient Flow (arrivals − exits)
      </div>
      <ResponsiveContainer width="100%" height={160}>
        <BarChart data={netData} margin={{ left: 10, right: 10, top: 5, bottom: 5 }}>
          <XAxis dataKey="round" tick={{ fill: '#6b7280', fontSize: 10 }} />
          <YAxis tick={{ fill: '#6b7280', fontSize: 10 }} />
          <Tooltip
            contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151', borderRadius: 8, fontSize: 12 }}
            labelFormatter={(label) => `Round ${label}`}
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            formatter={(value: any, name: any) => {
              const v = Number(value);
              return [v > 0 ? `+${v}` : `${v}`, DEPT_LABELS[String(name)] || String(name)];
            }}
          />
          <Legend
            wrapperStyle={{ fontSize: 11 }}
            formatter={(value: string) => DEPT_LABELS[value] || value}
          />
          <ReferenceLine y={0} stroke="#4b5563" />
          {deptIds.map((deptId) => (
            <Bar
              key={deptId}
              dataKey={deptId}
              fill={DEPT_CHART_COLORS[deptId] || '#888'}
              fillOpacity={0.7}
              stackId="a"
              name={deptId}
            />
          ))}
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
