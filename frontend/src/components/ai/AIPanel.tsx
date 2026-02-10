import { useGameStore } from '../../store/gameStore';
import { DECISION_STEPS } from '../../types/game';
import { formatCurrency } from '../../utils/formatters';
import { CandidateChart } from './CandidateChart';

export function AIPanel() {
  const { state, recommendation, fetchRecommendation } = useGameStore();

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
        <div className="flex items-center gap-2 text-gray-400 text-sm">
          <div className="w-4 h-4 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
          <span>Analyzing...</span>
        </div>
      )}

      {recommendation && (
        <>
          {/* Header: Source Badge + Confidence */}
          <div className="flex items-center gap-2">
            <span className={`px-2 py-0.5 text-xs rounded-full ${
              recommendation.source === 'llm'
                ? 'bg-purple-600/30 text-purple-300'
                : 'bg-gray-600/30 text-gray-300'
            }`}>
              {recommendation.source === 'llm' ? 'LLM' : 'Optimizer'}
            </span>
            {recommendation.confidence > 0 && (
              <div className="flex items-center gap-1.5 flex-1">
                <div className="h-1.5 flex-1 bg-gray-700 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-indigo-500 rounded-full transition-all"
                    style={{ width: `${recommendation.confidence * 100}%` }}
                  />
                </div>
                <span className="text-xs text-gray-500 shrink-0">
                  {Math.round(recommendation.confidence * 100)}%
                </span>
              </div>
            )}
          </div>

          {/* Reasoning Section */}
          {recommendation.reasoning_steps && recommendation.reasoning_steps.length > 0 ? (
            <div className="space-y-1">
              <div className="text-xs text-gray-400 font-medium">Reasoning</div>
              <ol className="list-decimal list-inside space-y-0.5">
                {recommendation.reasoning_steps.map((step, i) => (
                  <li key={i} className="text-sm text-gray-300">{step}</li>
                ))}
              </ol>
            </div>
          ) : (
            <p className="text-sm text-gray-300">{recommendation.reasoning}</p>
          )}

          {/* Cost Impact Card */}
          {(recommendation.baseline_cost > 0 || recommendation.cost_breakdown) && (
            <div className="bg-gray-800/50 rounded-lg p-3 space-y-2">
              <div className="text-xs text-gray-400 font-medium">Cost Impact</div>
              {recommendation.baseline_cost > 0 && (
                <div className="flex items-center justify-between text-xs">
                  <span className="text-gray-500">
                    Baseline ({recommendation.horizon_used}r)
                  </span>
                  <span className="text-gray-300">{formatCurrency(recommendation.baseline_cost)}</span>
                </div>
              )}
              {recommendation.cost_impact != null && recommendation.cost_impact !== 0 && (
                <div className="flex items-center justify-between text-xs">
                  <span className="text-gray-500">Delta</span>
                  <span className={`font-medium px-1.5 py-0.5 rounded ${
                    recommendation.cost_impact <= 0
                      ? 'bg-green-600/20 text-green-400'
                      : 'bg-red-600/20 text-red-400'
                  }`}>
                    {recommendation.cost_impact <= 0 ? '' : '+'}
                    {formatCurrency(recommendation.cost_impact)}
                  </span>
                </div>
              )}
              {recommendation.cost_breakdown && (
                <div className="border-t border-gray-700/50 pt-2 space-y-1">
                  <div className="flex justify-between text-[10px]">
                    <span className="text-gray-500">Action cost</span>
                    <span className="text-red-400">{formatCurrency(recommendation.cost_breakdown.action_cost)}</span>
                  </div>
                  <div className="flex justify-between text-[10px]">
                    <span className="text-gray-500">Avoided cost</span>
                    <span className="text-green-400">{formatCurrency(recommendation.cost_breakdown.avoided_cost)}</span>
                  </div>
                  <div className="flex justify-between text-[10px] font-medium">
                    <span className="text-gray-400">Net impact</span>
                    <span className={recommendation.cost_breakdown.net_impact <= 0 ? 'text-green-400' : 'text-red-400'}>
                      {formatCurrency(recommendation.cost_breakdown.net_impact)}
                    </span>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Key Tradeoffs */}
          {recommendation.key_tradeoffs && recommendation.key_tradeoffs.length > 0 && (
            <div className="space-y-1">
              {recommendation.key_tradeoffs.map((t, i) => (
                <div key={i} className="text-xs text-amber-300 bg-amber-900/15 border border-amber-600/20 rounded px-2 py-1.5">
                  {t}
                </div>
              ))}
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

          {/* Candidate Comparison Chart */}
          {recommendation.optimizer_candidates.length > 0 && (
            <CandidateChart
              candidates={recommendation.optimizer_candidates}
              baselineCost={recommendation.baseline_cost}
            />
          )}
        </>
      )}
    </div>
  );
}
