import { useState } from 'react';
import { useGameStore } from '../../store/gameStore';
import type { StaffingAction, StaffTransfer, DepartmentId } from '../../types/game';
import { ALL_DEPARTMENTS } from '../../types/game';
import { DEPT_NAMES, DEPT_TEXT } from '../../utils/formatters';
import { extraIdle } from '../../utils/staffUtils';
import { FLOW_GRAPH } from '../../utils/flowGraph';

export function StaffingForm() {
  const { state, loading, recommendation, submitStaffing } = useGameStore();

  const [extra, setExtra] = useState<Record<DepartmentId, number>>(
    { er: 0, surgery: 0, cc: 0, sd: 0 }
  );
  const [returns, setReturns] = useState<Record<DepartmentId, number>>(
    { er: 0, surgery: 0, cc: 0, sd: 0 }
  );
  const [staffTransfers, setStaffTransfers] = useState<StaffTransfer[]>([]);

  if (!state) return null;

  function applyRecommendation() {
    if (!recommendation?.recommended_action) return;
    const action = recommendation.recommended_action as unknown as StaffingAction;
    const newExtra: Record<DepartmentId, number> = { er: 0, surgery: 0, cc: 0, sd: 0 };
    const newReturns: Record<DepartmentId, number> = { er: 0, surgery: 0, cc: 0, sd: 0 };
    for (const [dept, count] of Object.entries(action.extra_staff ?? {})) {
      newExtra[dept as DepartmentId] = count;
    }
    for (const [dept, count] of Object.entries(action.return_extra ?? {})) {
      newReturns[dept as DepartmentId] = count;
    }
    setExtra(newExtra);
    setReturns(newReturns);
    setStaffTransfers(action.transfers ?? []);
  }

  function addTransfer() {
    setStaffTransfers([...staffTransfers, { from_dept: 'er', to_dept: 'surgery', count: 1 }]);
  }

  function removeTransfer(index: number) {
    setStaffTransfers(staffTransfers.filter((_, i) => i !== index));
  }

  function updateTransfer(index: number, field: keyof StaffTransfer, value: string | number) {
    setStaffTransfers(staffTransfers.map((t, i) =>
      i === index ? { ...t, [field]: value } : t
    ));
  }

  function handleSubmit() {
    const action: StaffingAction = {
      extra_staff: Object.fromEntries(
        ALL_DEPARTMENTS.filter((id) => extra[id] > 0).map((id) => [id, extra[id]])
      ) as Record<DepartmentId, number>,
      return_extra: Object.fromEntries(
        ALL_DEPARTMENTS.filter((id) => returns[id] > 0).map((id) => [id, returns[id]])
      ) as Record<DepartmentId, number>,
      transfers: staffTransfers.filter((t) => t.count > 0),
    };
    submitStaffing(action);
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="font-semibold text-lg">Staffing</h3>
        {recommendation && (
          <button
            onClick={applyRecommendation}
            className="text-xs px-2 py-1 bg-green-700/50 hover:bg-green-700 text-green-300 rounded transition-colors cursor-pointer"
          >
            Apply AI Suggestion
          </button>
        )}
      </div>

      {/* Call Extra Staff */}
      <div>
        <p className="text-xs text-gray-500 uppercase tracking-wide mb-2">Call Extra Staff ($40 + $5 quality each)</p>
        {ALL_DEPARTMENTS.map((id) => (
          <div key={id} className="flex items-center justify-between py-1">
            <span className={`text-sm ${DEPT_TEXT[id]}`}>{DEPT_NAMES[id]}</span>
            <input
              type="number"
              min={0}
              value={extra[id]}
              onChange={(e) => setExtra((prev) => ({ ...prev, [id]: Math.max(0, parseInt(e.target.value) || 0) }))}
              className="w-16 bg-gray-700 border border-gray-600 rounded px-2 py-1 text-sm text-center"
            />
          </div>
        ))}
      </div>

      {/* Return Extra Staff */}
      <div>
        <p className="text-xs text-gray-500 uppercase tracking-wide mb-2">Return Extra Staff</p>
        {ALL_DEPARTMENTS.map((id) => {
          const maxReturn = extraIdle(state.departments[id].staff);
          if (maxReturn === 0 && returns[id] === 0) return null;
          return (
            <div key={id} className="flex items-center justify-between py-1">
              <span className={`text-sm ${DEPT_TEXT[id]}`}>
                {DEPT_NAMES[id]} <span className="text-gray-500 text-xs">(max {maxReturn})</span>
              </span>
              <input
                type="number"
                min={0}
                max={maxReturn}
                value={returns[id]}
                onChange={(e) => setReturns((prev) => ({ ...prev, [id]: Math.max(0, Math.min(maxReturn, parseInt(e.target.value) || 0)) }))}
                className="w-16 bg-gray-700 border border-gray-600 rounded px-2 py-1 text-sm text-center"
              />
            </div>
          );
        })}
      </div>

      {/* Staff Transfers */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <p className="text-xs text-gray-500 uppercase tracking-wide">Staff Transfers</p>
          <button
            onClick={addTransfer}
            className="text-xs px-2 py-1 bg-gray-700 hover:bg-gray-600 rounded transition-colors cursor-pointer"
          >
            + Add
          </button>
        </div>
        {staffTransfers.map((t, i) => (
          <div key={i} className="flex items-center gap-2 py-1">
            <select
              value={t.from_dept}
              onChange={(e) => updateTransfer(i, 'from_dept', e.target.value)}
              className="bg-gray-700 border border-gray-600 rounded px-2 py-1 text-sm flex-1"
            >
              {ALL_DEPARTMENTS.map((id) => (
                <option key={id} value={id}>{DEPT_NAMES[id]}</option>
              ))}
            </select>
            <span className="text-gray-500 text-xs">to</span>
            <select
              value={t.to_dept}
              onChange={(e) => updateTransfer(i, 'to_dept', e.target.value)}
              className="bg-gray-700 border border-gray-600 rounded px-2 py-1 text-sm flex-1"
            >
              {(FLOW_GRAPH[t.from_dept as DepartmentId] ?? []).map((id) => (
                <option key={id} value={id}>{DEPT_NAMES[id]}</option>
              ))}
            </select>
            <input
              type="number"
              min={1}
              value={t.count}
              onChange={(e) => updateTransfer(i, 'count', Math.max(1, parseInt(e.target.value) || 1))}
              className="w-14 bg-gray-700 border border-gray-600 rounded px-2 py-1 text-sm text-center"
            />
            <button
              onClick={() => removeTransfer(i)}
              className="text-red-400 hover:text-red-300 text-sm cursor-pointer"
            >
              &times;
            </button>
          </div>
        ))}
      </div>

      <button
        onClick={handleSubmit}
        disabled={loading}
        className="w-full py-2 bg-blue-600 hover:bg-blue-500 disabled:bg-gray-700 rounded-lg font-medium transition-colors cursor-pointer"
      >
        {loading ? 'Processing...' : 'Submit Staffing'}
      </button>
    </div>
  );
}
