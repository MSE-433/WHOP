import {
  ComposedChart,
  Bar,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import { useGameStore } from '../../store/gameStore';

interface ChartRow {
  round: string;
  financial: number;
  quality: number;
  cumFinancial: number;
  cumQuality: number;
}

export function CostChart() {
  const state = useGameStore((s) => s.state);
  if (!state || state.round_costs.length === 0) return null;

  let cumFin = 0;
  let cumQual = 0;
  const data: ChartRow[] = state.round_costs.map((rc) => {
    cumFin += rc.financial;
    cumQual += rc.quality;
    return {
      round: String(rc.round_number),
      financial: rc.financial,
      quality: rc.quality,
      cumFinancial: cumFin,
      cumQuality: cumQual,
    };
  });

  const fmt = (v: number) => `$${v.toLocaleString()}`;

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-lg p-4">
      <h3 className="font-semibold mb-3">Cost Overview</h3>
      <ResponsiveContainer width="100%" height={250}>
        <ComposedChart data={data} barGap={2} barCategoryGap="25%">
          <XAxis
            dataKey="round"
            type="category"
            tick={{ fill: '#9ca3af', fontSize: 11 }}
            stroke="#374151"
          />
          <YAxis
            yAxisId="round"
            tick={{ fill: '#9ca3af', fontSize: 11 }}
            stroke="#374151"
            tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`}
          />
          <YAxis
            yAxisId="cumulative"
            orientation="right"
            tick={{ fill: '#9ca3af', fontSize: 11 }}
            stroke="#374151"
            tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: '#1f2937',
              border: '1px solid #374151',
              borderRadius: 8,
              fontSize: 12,
            }}
            formatter={(value?: number, name?: string) => value != null ? [fmt(value), name ?? ''] : []}
            labelFormatter={(label) => `Round ${label}`}
          />
          <Legend wrapperStyle={{ fontSize: 11 }} />
          <Bar
            yAxisId="round"
            dataKey="financial"
            name="Round Financial"
            fill="#eab308"
            opacity={0.7}
            maxBarSize={24}
          />
          <Bar
            yAxisId="round"
            dataKey="quality"
            name="Round Quality"
            fill="#f97316"
            opacity={0.7}
            maxBarSize={24}
          />
          <Line
            yAxisId="cumulative"
            type="monotone"
            dataKey="cumFinancial"
            name="Cumulative Financial"
            stroke="#facc15"
            strokeWidth={2}
            dot={{ r: 3 }}
          />
          <Line
            yAxisId="cumulative"
            type="monotone"
            dataKey="cumQuality"
            name="Cumulative Quality"
            stroke="#fb923c"
            strokeWidth={2}
            dot={{ r: 3 }}
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
