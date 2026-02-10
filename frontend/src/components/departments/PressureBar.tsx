import type { DeptUtilization } from '../../types/game';

interface Props {
  utilization: DeptUtilization;
}

function pressureColor(pressure: number): string {
  if (pressure >= 0.8) return 'bg-red-500';
  if (pressure >= 0.6) return 'bg-amber-500';
  if (pressure >= 0.4) return 'bg-yellow-500';
  return 'bg-green-500';
}

export function PressureBar({ utilization }: Props) {
  const pct = Math.min(utilization.pressure * 100, 100);

  return (
    <div className="group relative">
      <div className="h-1.5 bg-gray-700 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all ${pressureColor(utilization.pressure)}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      {/* Tooltip on hover */}
      <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-1 hidden group-hover:block z-10">
        <div className="bg-gray-800 border border-gray-700 rounded-lg px-2 py-1.5 text-[10px] whitespace-nowrap shadow-lg">
          <div className="text-gray-300 font-medium mb-0.5">Pressure: {(utilization.pressure * 100).toFixed(0)}%</div>
          <div className="text-gray-500">
            Staff: {(utilization.staff_utilization * 100).toFixed(0)}% ·
            Beds: {(utilization.bed_utilization * 100).toFixed(0)}%
            {utilization.overflow > 0 && ` · ${utilization.overflow} overflow`}
          </div>
        </div>
      </div>
    </div>
  );
}
