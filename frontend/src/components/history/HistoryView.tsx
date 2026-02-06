import { useGameStore } from '../../store/gameStore';
import { formatCurrency, DEPT_NAMES, DEPT_TEXT } from '../../utils/formatters';
import type { DepartmentId, ReplayRound } from '../../types/game';
import { ALL_DEPARTMENTS } from '../../types/game';

function RoundCard({ round }: { round: ReplayRound }) {
  const totalCost = round.costs.financial + round.costs.quality;

  return (
    <div className="bg-gray-800/50 border border-gray-700 rounded-lg p-4">
      <div className="flex justify-between items-center mb-3">
        <h3 className="text-lg font-semibold">Round {round.round_number}</h3>
        <div className="flex gap-4 text-sm">
          <span className="text-yellow-400">{formatCurrency(round.costs.financial)} fin</span>
          <span className="text-orange-400">{formatCurrency(round.costs.quality)} qual</span>
          <span className="text-gray-300 font-medium">{formatCurrency(totalCost)} total</span>
        </div>
      </div>

      {round.events.length > 0 && (
        <div className="mb-3 text-sm">
          <span className="text-amber-400 font-medium">Events: </span>
          <span className="text-gray-400">{round.events.join(' | ')}</span>
        </div>
      )}

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {ALL_DEPARTMENTS.map((deptId: DepartmentId) => {
          const d = round.departments[deptId];
          if (!d) return null;
          return (
            <div key={deptId} className="bg-gray-900/50 rounded p-2 text-xs space-y-1">
              <div className={`font-semibold ${DEPT_TEXT[deptId]}`}>{DEPT_NAMES[deptId]}</div>
              <div className="text-gray-400">
                {d.patients} pts | {d.staff_idle}/{d.staff_total} staff idle
              </div>
              <div className="text-gray-400">
                {d.beds_available >= 0 ? `${d.beds_available} beds` : 'unlimited'} | {d.arrivals_waiting} waiting
              </div>
              {(d.is_closed || d.is_diverting) && (
                <div className="text-amber-400">
                  {d.is_closed && 'CLOSED '}
                  {d.is_diverting && 'DIVERT'}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

export function HistoryView() {
  const { replay, closeReplay } = useGameStore();
  if (!replay) return null;

  return (
    <div className="fixed inset-0 bg-black/90 flex flex-col z-50">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-gray-700">
        <h2 className="text-xl font-bold">Game History</h2>
        <div className="flex items-center gap-6">
          <div className="text-sm text-gray-400">
            <span className="text-yellow-400 font-medium">{formatCurrency(replay.total_financial_cost)}</span> financial |{' '}
            <span className="text-orange-400 font-medium">{formatCurrency(replay.total_quality_cost)}</span> quality |{' '}
            <span className="text-white font-medium">
              {formatCurrency(replay.total_financial_cost + replay.total_quality_cost)}
            </span>{' '}
            total
          </div>
          <button
            onClick={closeReplay}
            className="px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg text-sm transition-colors cursor-pointer"
          >
            Close
          </button>
        </div>
      </div>

      {/* Round list */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {replay.rounds.length === 0 ? (
          <p className="text-gray-500 text-center mt-8">No rounds completed yet.</p>
        ) : (
          replay.rounds.map((round) => <RoundCard key={round.round_number} round={round} />)
        )}
      </div>
    </div>
  );
}
