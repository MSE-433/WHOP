import { useState } from 'react';
import { useGameStore } from '../../store/gameStore';
import { DECISION_STEPS } from '../../types/game';
import { formatCurrency } from '../../utils/formatters';

export function AIPanel() {
  const { state, recommendation, fetchRecommendation } = useGameStore();
  const [showCandidates, setShowCandidates] = useState(false);

  if (!state) return null;

  const isDecisionStep = DECISION_STEPS.includes(state.current_step);

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-lg p-4 space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="font-semibold">AI Advisor</h3>
        {isDecisionStep && (
          <button
            onClick={fetchRecommendation}
            className="text-xs px-2 py-1 bg-indigo-700/50 hover:bg-indigo-700 text-indigo-300 rounded transition-colors cursor-pointer"
          >
            Ask AI
          </button>
        )}
      </div>

      {!isDecisionStep && (
        <p className="text-gray-500 text-sm">
          AI recommendations available during decision steps.
        </p>
      )}

      {isDecisionStep && !recommendation && (
        <p className="text-gray-500 text-sm">Loading recommendation...</p>
      )}

      {recommendation && (
        <>
          {/* Source Badge */}
          <div className="flex items-center gap-2">
            <span className={`px-2 py-0.5 text-xs rounded-full ${
              recommendation.source === 'llm'
                ? 'bg-purple-600/30 text-purple-300'
                : 'bg-gray-600/30 text-gray-300'
            }`}>
              {recommendation.source === 'llm' ? 'LLM' : 'Optimizer'}
            </span>
            {recommendation.confidence > 0 && (
              <span className="text-xs text-gray-500">
                {Math.round(recommendation.confidence * 100)}% confidence
              </span>
            )}
          </div>

          {/* Reasoning */}
          <p className="text-sm text-gray-300">{recommendation.reasoning}</p>

          {/* Cost Impact */}
          {recommendation.baseline_cost > 0 && (
            <div className="text-xs text-gray-400">
              Baseline cost: {formatCurrency(recommendation.baseline_cost)} over {recommendation.horizon_used} rounds
            </div>
          )}

          {/* Risk Flags */}
          {recommendation.risk_flags.length > 0 && (
            <div className="space-y-1">
              {recommendation.risk_flags.map((flag, i) => (
                <div key={i} className="text-xs text-amber-400 bg-amber-900/20 rounded px-2 py-1">
                  {flag}
                </div>
              ))}
            </div>
          )}

          {/* Optimizer Candidates */}
          {recommendation.optimizer_candidates.length > 0 && (
            <div>
              <button
                onClick={() => setShowCandidates(!showCandidates)}
                className="text-xs text-gray-500 hover:text-gray-300 cursor-pointer"
              >
                {showCandidates ? 'Hide' : 'Show'} {recommendation.optimizer_candidates.length} candidates
              </button>
              {showCandidates && (
                <div className="mt-2 space-y-2">
                  {recommendation.optimizer_candidates.map((c, i) => (
                    <div key={i} className="bg-gray-800/50 rounded p-2 text-xs">
                      <div className="font-medium text-gray-300">{c.description}</div>
                      <div className="text-gray-500 mt-1">
                        Total: {formatCurrency(c.expected_total)} | Delta: {formatCurrency(c.delta_vs_baseline)}
                      </div>
                      {c.reasoning && (
                        <div className="text-gray-400 mt-1">{c.reasoning}</div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
}
