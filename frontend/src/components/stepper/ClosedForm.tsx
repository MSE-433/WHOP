import { useState, useEffect } from 'react';
import { useGameStore } from '../../store/gameStore';
import type { ClosedAction, DepartmentId } from '../../types/game';
import { ALL_DEPARTMENTS } from '../../types/game';
import { DEPT_NAMES, DEPT_TEXT } from '../../utils/formatters';

export function ClosedForm() {
  const { state, loading, recommendation, submitClosed } = useGameStore();

  const [closed, setClosed] = useState<Record<DepartmentId, boolean>>(
    { er: false, surgery: false, cc: false, sd: false }
  );
  const [divert, setDivert] = useState(false);

  // Init from current state
  useEffect(() => {
    if (!state) return;
    const init: Record<DepartmentId, boolean> = { er: false, surgery: false, cc: false, sd: false };
    for (const id of ALL_DEPARTMENTS) {
      init[id] = state.departments[id].is_closed;
    }
    setClosed(init);
    setDivert(state.departments.er.is_diverting);
  }, [state?.round_number, state?.current_step]);

  if (!state) return null;

  function applyRecommendation() {
    if (!recommendation?.recommended_action) return;
    const action = recommendation.recommended_action as unknown as ClosedAction;
    const newClosed = { ...closed };
    for (const id of action.close_departments ?? []) {
      newClosed[id as DepartmentId] = true;
    }
    for (const id of action.open_departments ?? []) {
      newClosed[id as DepartmentId] = false;
    }
    setClosed(newClosed);
    setDivert(action.divert_er ?? false);
  }

  function handleSubmit() {
    const action: ClosedAction = {
      close_departments: ALL_DEPARTMENTS.filter((id) => closed[id] && !state!.departments[id].is_closed),
      open_departments: ALL_DEPARTMENTS.filter((id) => !closed[id] && state!.departments[id].is_closed),
      divert_er: divert,
    };
    submitClosed(action);
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === 'Enter') {
      handleSubmit();
    }
  }

  return (
    <div className="space-y-4" onKeyDown={handleKeyDown}>
      <div className="flex items-center justify-between">
        <h3 className="font-semibold text-lg">Close / Divert</h3>
        {recommendation && (
          <button
            onClick={applyRecommendation}
            className="text-xs px-2 py-1 bg-green-700/50 hover:bg-green-700 text-green-300 rounded transition-colors cursor-pointer"
          >
            Apply AI Suggestion
          </button>
        )}
      </div>

      <p className="text-gray-400 text-xs">
        Toggle departments closed (signals only, does not stop arrivals).
      </p>

      {ALL_DEPARTMENTS.map((id) => (
        <div key={id} className="flex items-center justify-between bg-gray-800/50 rounded-lg px-3 py-2">
          <span className={`text-sm ${DEPT_TEXT[id]}`}>{DEPT_NAMES[id]}</span>
          <label className="flex items-center gap-2 cursor-pointer">
            <span className="text-xs text-gray-400">{closed[id] ? 'Closed' : 'Open'}</span>
            <input
              type="checkbox"
              checked={closed[id]}
              onChange={(e) => setClosed((prev) => ({ ...prev, [id]: e.target.checked }))}
              className="accent-red-500"
            />
          </label>
        </div>
      ))}

      {/* ER Diversion */}
      <div className="bg-orange-900/20 border border-orange-800/50 rounded-lg p-3">
        <div className="flex items-center justify-between">
          <div>
            <span className="text-sm text-orange-300">ER Ambulance Diversion</span>
            <p className="text-xs text-orange-400/60 mt-1">
              Stops ambulance arrivals next round. Cost: $5,000 + $200/diverted.
            </p>
          </div>
          <label className="flex items-center gap-2 cursor-pointer">
            <span className="text-xs text-gray-400">{divert ? 'On' : 'Off'}</span>
            <input
              type="checkbox"
              checked={divert}
              onChange={(e) => setDivert(e.target.checked)}
              className="accent-orange-500"
            />
          </label>
        </div>
      </div>

      <div className="pt-3 sticky bottom-0 bg-gradient-to-t from-gray-900 via-gray-900">
        <button
          onClick={handleSubmit}
          disabled={loading}
          className="w-full py-2 bg-blue-600 hover:bg-blue-500 disabled:bg-gray-700 rounded-lg font-medium transition-colors cursor-pointer"
        >
          {loading ? 'Processing...' : 'Submit Close/Divert'}
        </button>
      </div>
    </div>
  );
}
