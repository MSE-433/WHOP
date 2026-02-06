import { useState } from 'react';
import { useGameStore } from '../../store/gameStore';
import { STEP_ORDER } from '../../types/game';
import { roundToTime, isEventRound } from '../../utils/timeMapping';
import { formatCurrency, STEP_LABELS } from '../../utils/formatters';

export function GameHeader() {
  const state = useGameStore((s) => s.state);
  const endGame = useGameStore((s) => s.endGame);
  const [showConfirm, setShowConfirm] = useState(false);

  if (!state) return null;

  const stepIndex = STEP_ORDER.indexOf(state.current_step);

  return (
    <header className="bg-gray-900 border-b border-gray-800 px-6 py-3">
      <div className="flex flex-wrap items-center justify-between gap-4">
        {/* Round + Clock */}
        <div className="flex items-center gap-3">
          <h2 className="text-lg font-semibold">
            Round {state.round_number}
          </h2>
          <span className="text-gray-400">
            {roundToTime(state.round_number)}
          </span>
          {isEventRound(state.round_number) && (
            <span className="px-2 py-0.5 bg-amber-600/20 text-amber-400 text-xs rounded-full font-medium">
              Event Round
            </span>
          )}
        </div>

        {/* Step Indicator */}
        <div className="flex gap-1">
          {STEP_ORDER.map((step, i) => (
            <div
              key={step}
              className={`px-3 py-1 rounded-full text-xs font-medium transition-colors ${
                i === stepIndex
                  ? 'bg-blue-600 text-white'
                  : i < stepIndex
                    ? 'bg-gray-700 text-gray-400'
                    : 'bg-gray-800 text-gray-500'
              }`}
            >
              {STEP_LABELS[step]}
            </div>
          ))}
        </div>

        {/* Running Costs + End Game */}
        <div className="flex items-center gap-4 text-sm">
          <span>
            Financial: <span className="text-yellow-400 font-medium">{formatCurrency(state.total_financial_cost)}</span>
          </span>
          <span>
            Quality: <span className="text-orange-400 font-medium">{formatCurrency(state.total_quality_cost)}</span>
          </span>

          {/* End Game button */}
          {!showConfirm ? (
            <button
              onClick={() => setShowConfirm(true)}
              className="ml-2 px-3 py-1 text-xs bg-gray-700 hover:bg-red-600/80 text-gray-300 hover:text-white rounded transition-colors cursor-pointer"
            >
              End Game
            </button>
          ) : (
            <div className="flex items-center gap-2 ml-2">
              <span className="text-xs text-red-400">End game?</span>
              <button
                onClick={() => { endGame(); setShowConfirm(false); }}
                className="px-2 py-1 text-xs bg-red-600 hover:bg-red-500 text-white rounded cursor-pointer"
              >
                Yes
              </button>
              <button
                onClick={() => setShowConfirm(false)}
                className="px-2 py-1 text-xs bg-gray-700 hover:bg-gray-600 text-gray-300 rounded cursor-pointer"
              >
                No
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
