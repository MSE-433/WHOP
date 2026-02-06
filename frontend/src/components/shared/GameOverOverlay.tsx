import { useGameStore } from '../../store/gameStore';
import { formatCurrency } from '../../utils/formatters';
import * as api from '../../api/client';

export function GameOverOverlay() {
  const { state, gameId, endGame, fetchReplay } = useGameStore();
  if (!state || !state.is_finished) return null;

  const handleExportCSV = async () => {
    if (!gameId) return;
    try {
      await api.exportCSV(gameId);
    } catch {
      // non-critical
    }
  };

  return (
    <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4">
      <div className="bg-gray-900 border border-gray-700 rounded-xl max-w-lg w-full p-6 space-y-4">
        <h2 className="text-2xl font-bold text-center">Game Over</h2>
        <p className="text-gray-400 text-center">
          {state.round_costs.length >= 24 ? '24-hour shift complete!' : `Game ended after ${state.round_costs.length} rounds.`}
        </p>

        <div className="grid grid-cols-2 gap-4 bg-gray-800/50 rounded-lg p-4">
          <div className="text-center">
            <div className="text-sm text-gray-400">Total Financial</div>
            <div className="text-2xl font-bold text-yellow-400">
              {formatCurrency(state.total_financial_cost)}
            </div>
          </div>
          <div className="text-center">
            <div className="text-sm text-gray-400">Total Quality</div>
            <div className="text-2xl font-bold text-orange-400">
              {formatCurrency(state.total_quality_cost)}
            </div>
          </div>
        </div>

        {/* Per-round breakdown */}
        {state.round_costs.length > 0 && (
          <div className="max-h-48 overflow-y-auto">
            <table className="w-full text-sm">
              <thead className="text-gray-500 text-xs">
                <tr>
                  <th className="text-left py-1">Round</th>
                  <th className="text-right py-1">Financial</th>
                  <th className="text-right py-1">Quality</th>
                </tr>
              </thead>
              <tbody>
                {state.round_costs.map((rc) => (
                  <tr key={rc.round_number} className="border-t border-gray-800">
                    <td className="py-1 text-gray-300">{rc.round_number}</td>
                    <td className="py-1 text-right text-yellow-400/80">{formatCurrency(rc.financial)}</td>
                    <td className="py-1 text-right text-orange-400/80">{formatCurrency(rc.quality)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        <div className="flex gap-3">
          <button
            onClick={handleExportCSV}
            className="flex-1 py-3 bg-green-700 hover:bg-green-600 rounded-lg font-medium transition-colors cursor-pointer"
          >
            Export CSV
          </button>
          <button
            onClick={fetchReplay}
            className="flex-1 py-3 bg-purple-700 hover:bg-purple-600 rounded-lg font-medium transition-colors cursor-pointer"
          >
            View History
          </button>
        </div>

        <button
          onClick={endGame}
          className="w-full py-3 bg-blue-600 hover:bg-blue-500 rounded-lg font-medium text-lg transition-colors cursor-pointer"
        >
          New Game
        </button>
      </div>
    </div>
  );
}
