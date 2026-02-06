import { useGameStore } from '../../store/gameStore';
import { formatCurrency } from '../../utils/formatters';

export function PaperworkView() {
  const { state, loading, submitPaperwork } = useGameStore();
  if (!state) return null;

  // Show costs from current round if available
  const currentRoundCost = state.round_costs.find(
    (c) => c.round_number === state.round_number
  );

  return (
    <div className="space-y-4">
      <h3 className="font-semibold text-lg">Paperwork</h3>
      <p className="text-gray-400 text-sm">
        Calculate costs for this round and advance to the next round.
      </p>

      {currentRoundCost && (
        <div className="bg-gray-800/50 rounded-lg p-3 space-y-2">
          <div className="flex justify-between text-sm">
            <span className="text-gray-400">Round Financial</span>
            <span className="text-yellow-400">{formatCurrency(currentRoundCost.financial)}</span>
          </div>
          <div className="flex justify-between text-sm">
            <span className="text-gray-400">Round Quality</span>
            <span className="text-orange-400">{formatCurrency(currentRoundCost.quality)}</span>
          </div>
          {Object.keys(currentRoundCost.details).length > 0 && (
            <div className="border-t border-gray-700 pt-2 mt-2">
              {Object.entries(currentRoundCost.details).map(([key, val]) => (
                <div key={key} className="flex justify-between text-xs text-gray-500">
                  <span>{key}</span>
                  <span>{formatCurrency(val)}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      <button
        onClick={submitPaperwork}
        disabled={loading}
        className="w-full py-2 bg-blue-600 hover:bg-blue-500 disabled:bg-gray-700 rounded-lg font-medium transition-colors cursor-pointer"
      >
        {loading ? 'Processing...' : state.round_number >= 24 ? 'Finish Game' : 'Next Round'}
      </button>
    </div>
  );
}
