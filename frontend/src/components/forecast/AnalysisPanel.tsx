import type { BottleneckAlert, StaffEfficiency, DiversionROI } from '../../types/game';
import { formatCurrency } from '../../utils/formatters';

const DEPT_LABELS: Record<string, string> = {
  er: 'ER',
  surgery: 'Surgery',
  cc: 'CC',
  sd: 'Step Down',
};

const SEVERITY_STYLES: Record<string, string> = {
  high: 'bg-red-600/20 text-red-400 border-red-600/30',
  medium: 'bg-amber-600/20 text-amber-400 border-amber-600/30',
  low: 'bg-green-600/20 text-green-400 border-green-600/30',
};

interface Props {
  bottlenecks: BottleneckAlert[];
  staffEfficiency: Record<string, StaffEfficiency>;
  diversionRoi: DiversionROI;
}

export function AnalysisPanel({ bottlenecks, staffEfficiency, diversionRoi }: Props) {
  return (
    <div className="space-y-4">
      {/* Bottleneck Alerts */}
      <div>
        <div className="text-xs text-gray-400 font-medium uppercase tracking-wide mb-2">
          Bottleneck Alerts
        </div>
        {bottlenecks.length === 0 ? (
          <div className="text-xs text-gray-500 bg-gray-800/50 rounded-lg p-2">
            No bottleneck risks detected
          </div>
        ) : (
          <div className="space-y-1.5">
            {bottlenecks.map((b, i) => (
              <div
                key={i}
                className={`text-xs rounded-lg border px-3 py-2 ${SEVERITY_STYLES[b.severity] || SEVERITY_STYLES.low}`}
              >
                <span className="font-semibold">{DEPT_LABELS[b.department] || b.department}</span>
                <span className="mx-1.5">·</span>
                <span className="uppercase text-[10px] font-bold">{b.severity}</span>
                <div className="mt-0.5 opacity-80">{b.reason}</div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Staff Efficiency */}
      <div>
        <div className="text-xs text-gray-400 font-medium uppercase tracking-wide mb-2">
          Staff Efficiency
        </div>
        <div className="grid grid-cols-2 gap-2">
          {Object.entries(staffEfficiency).map(([deptId, s]) => (
            <div key={deptId} className="bg-gray-800/50 rounded-lg p-2">
              <div className="text-[10px] text-gray-500 uppercase font-medium mb-1">
                {DEPT_LABELS[deptId] || deptId}
              </div>
              <div className="flex flex-wrap gap-1 text-[10px]">
                <span className="text-gray-400">
                  Idle: <span className={s.idle > 0 ? 'text-green-400' : 'text-gray-500'}>{s.idle}</span>
                </span>
                {s.deficit > 0 && (
                  <span className="text-red-400">Deficit: {s.deficit}</span>
                )}
                {s.extra_on_duty > 0 && (
                  <span className="text-blue-400">Extra: {s.extra_on_duty}</span>
                )}
              </div>
              <div className="flex flex-wrap gap-1 mt-1">
                {s.recommend_extra > 0 && (
                  <span className="text-[10px] px-1.5 py-0.5 bg-green-600/20 text-green-400 rounded-full">
                    Call +{s.recommend_extra}
                  </span>
                )}
                {s.recommend_return > 0 && (
                  <span className="text-[10px] px-1.5 py-0.5 bg-blue-600/20 text-blue-400 rounded-full">
                    Return {s.recommend_return}
                  </span>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Diversion ROI */}
      <div>
        <div className="text-xs text-gray-400 font-medium uppercase tracking-wide mb-2">
          Diversion ROI
        </div>
        <div className={`rounded-lg border p-3 ${
          diversionRoi.recommend_diversion
            ? 'bg-green-600/10 border-green-600/30'
            : 'bg-red-600/10 border-red-600/30'
        }`}>
          <div className={`text-sm font-semibold ${
            diversionRoi.recommend_diversion ? 'text-green-400' : 'text-red-400'
          }`}>
            {diversionRoi.recommend_diversion ? 'Consider Diversion' : 'Diversion NOT Recommended'}
          </div>
          <div className="text-xs text-gray-400 mt-1">{diversionRoi.reason}</div>
          <div className="grid grid-cols-3 gap-2 mt-2 text-[10px]">
            <div>
              <div className="text-gray-500">Diversion Cost</div>
              <div className="text-red-400 font-medium">{formatCurrency(diversionRoi.diversion_cost)}</div>
            </div>
            <div>
              <div className="text-gray-500">Avoided Waiting</div>
              <div className="text-green-400 font-medium">{formatCurrency(diversionRoi.avoided_waiting_cost)}</div>
            </div>
            <div>
              <div className="text-gray-500">Net Savings</div>
              <div className={`font-medium ${diversionRoi.net_savings >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                {formatCurrency(diversionRoi.net_savings)}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
