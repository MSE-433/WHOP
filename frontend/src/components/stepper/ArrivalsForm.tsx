import { useState, useEffect } from 'react';
import { useGameStore } from '../../store/gameStore';
import type { ArrivalsAction, DepartmentId } from '../../types/game';
import { ALL_DEPARTMENTS } from '../../types/game';
import { DEPT_NAMES, DEPT_TEXT } from '../../utils/formatters';
import { totalIdle, bedsAvailable, hasHallway, totalRequestsWaiting } from '../../utils/staffUtils';

export function ArrivalsForm() {
  const { state, loading, recommendation, roundCards, submitArrivals } = useGameStore();
  const [admissions, setAdmissions] = useState<Record<DepartmentId, number>>(
    { er: 0, surgery: 0, cc: 0, sd: 0 }
  );
  const [accepts, setAccepts] = useState<Record<string, number>>({});
  const [arrivalOverrides, setArrivalOverrides] = useState<Record<DepartmentId, number>>(
    { er: 0, surgery: 0, cc: 0, sd: 0 }
  );

  // Compute default card arrivals for this round (accounting for diversion & shift_change)
  function getDefaultArrivals(): Record<DepartmentId, number> {
    const defaults: Record<DepartmentId, number> = { er: 0, surgery: 0, cc: 0, sd: 0 };
    if (!state || !roundCards) return defaults;

    for (const id of ALL_DEPARTMENTS) {
      const dept = state.departments[id];
      const hasShiftChange = dept.active_events.some(e => e.effect.shift_change);
      if (hasShiftChange) {
        defaults[id] = 0;
        continue;
      }
      const card = roundCards.departments[id];
      if (!card) continue;
      if (id === 'er') {
        const walkin = card.walkin ?? 0;
        const ambulance = state.ambulances_diverted_this_round > 0 ? 0 : (card.ambulance ?? 0);
        defaults[id] = walkin + ambulance;
      } else {
        defaults[id] = card.arrivals;
      }
    }
    return defaults;
  }

  // Initialize arrival overrides from card defaults when roundCards loads
  useEffect(() => {
    if (roundCards && state) {
      setArrivalOverrides(getDefaultArrivals());
    }
  }, [roundCards, state?.round_number]);

  if (!state) return null;

  const cardDefaults = getDefaultArrivals();

  function setAdmit(dept: DepartmentId, val: number) {
    setAdmissions((prev) => ({ ...prev, [dept]: Math.max(0, val) }));
  }

  function setAccept(dept: DepartmentId, fromDept: DepartmentId, val: number) {
    setAccepts((prev) => ({ ...prev, [`${dept}-${fromDept}`]: Math.max(0, val) }));
  }

  function setArrivalOverride(dept: DepartmentId, val: number) {
    setArrivalOverrides((prev) => ({ ...prev, [dept]: Math.max(0, val) }));
  }

  function applyRecommendation() {
    if (!recommendation?.recommended_action) return;
    const action = recommendation.recommended_action as unknown as ArrivalsAction;
    const newAdmissions: Record<DepartmentId, number> = { er: 0, surgery: 0, cc: 0, sd: 0 };
    const newAccepts: Record<string, number> = {};
    for (const adm of action.admissions ?? []) {
      newAdmissions[adm.department as DepartmentId] = adm.admit_count;
    }
    for (const acc of action.transfer_accepts ?? []) {
      newAccepts[`${acc.department}-${acc.from_dept}`] = acc.accept_count;
    }
    setAdmissions(newAdmissions);
    setAccepts(newAccepts);
  }

  function handleSubmit() {
    // Build overrides: only include depts where the user changed the value
    const overrides: Record<string, number> = {};
    for (const id of ALL_DEPARTMENTS) {
      if (arrivalOverrides[id] !== cardDefaults[id]) {
        overrides[id] = arrivalOverrides[id];
      }
    }

    const action: ArrivalsAction = {
      admissions: ALL_DEPARTMENTS
        .filter((id) => admissions[id] > 0)
        .map((id) => ({ department: id, admit_count: admissions[id] })),
      transfer_accepts: Object.entries(accepts)
        .filter(([, count]) => count > 0)
        .map(([key, count]) => {
          const [dept, from] = key.split('-') as [DepartmentId, DepartmentId];
          return { department: dept, from_dept: from, accept_count: count };
        }),
      ...(Object.keys(overrides).length > 0 ? { arrival_overrides: overrides as Record<DepartmentId, number> } : {}),
    };
    submitArrivals(action);
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === 'Enter' && !(e.target instanceof HTMLInputElement && e.target.type === 'number')) {
      handleSubmit();
    }
  }

  return (
    <div className="space-y-4" onKeyDown={handleKeyDown}>
      <div className="flex items-center justify-between">
        <h3 className="font-semibold text-lg">Arrivals</h3>
        {recommendation && (
          <button
            onClick={applyRecommendation}
            className="text-xs px-2 py-1 bg-green-700/50 hover:bg-green-700 text-green-300 rounded transition-colors cursor-pointer"
          >
            Apply AI Suggestion
          </button>
        )}
      </div>

      {/* Editable arrival card values */}
      {roundCards && (
        <div className="bg-gray-800/50 border border-gray-700/50 rounded-lg p-3 space-y-2">
          <div className="text-xs text-gray-400 font-medium uppercase tracking-wide">
            Arrival Card Values (editable)
          </div>
          <div className="grid grid-cols-2 gap-2">
            {ALL_DEPARTMENTS.map((id) => {
              const isChanged = arrivalOverrides[id] !== cardDefaults[id];
              return (
                <div key={id} className="flex items-center justify-between bg-gray-900/50 rounded px-2.5 py-1.5">
                  <span className={`text-xs font-medium ${DEPT_TEXT[id]}`}>{DEPT_NAMES[id]}</span>
                  <div className="flex items-center gap-1.5">
                    {isChanged && (
                      <span className="text-[10px] text-amber-400" title={`Card default: ${cardDefaults[id]}`}>
                        (was {cardDefaults[id]})
                      </span>
                    )}
                    <input
                      type="number"
                      min={0}
                      value={arrivalOverrides[id]}
                      onChange={(e) => setArrivalOverride(id, parseInt(e.target.value) || 0)}
                      className={`w-14 bg-gray-700 border rounded px-1.5 py-0.5 text-xs text-center ${
                        isChanged ? 'border-amber-500/60 text-amber-300' : 'border-gray-600'
                      }`}
                    />
                  </div>
                </div>
              );
            })}
          </div>
          {Object.keys(arrivalOverrides).some((id) => arrivalOverrides[id as DepartmentId] !== cardDefaults[id as DepartmentId]) && (
            <button
              onClick={() => setArrivalOverrides(cardDefaults)}
              className="text-[10px] text-gray-500 hover:text-gray-300 cursor-pointer"
            >
              Reset to card defaults
            </button>
          )}
        </div>
      )}

      <p className="text-gray-400 text-xs">
        Choose how many waiting patients to admit from each department.
      </p>

      {/* Admit arrivals */}
      {ALL_DEPARTMENTS.map((id) => {
        const dept = state.departments[id];
        // Use overridden arrivals_waiting: current + delta from override
        const overrideDelta = arrivalOverrides[id] - cardDefaults[id];
        const effectiveWaiting = Math.max(0, dept.arrivals_waiting + overrideDelta);
        const idle = totalIdle(dept.staff);
        const beds = bedsAvailable(dept);
        const maxAdmit = Math.min(effectiveWaiting, idle, hasHallway(id) ? Infinity : beds);
        const reqWaiting = totalRequestsWaiting(dept);

        if (effectiveWaiting === 0 && reqWaiting === 0) return null;

        return (
          <div key={id} className="bg-gray-800/50 rounded-lg p-3 space-y-2">
            <div className={`text-sm font-medium ${DEPT_TEXT[id]}`}>{DEPT_NAMES[id]}</div>

            {effectiveWaiting > 0 && (
              <div className="flex items-center justify-between gap-2">
                <span className="text-sm text-gray-300">
                  Admit ({effectiveWaiting} waiting, {idle} idle staff, {beds === Infinity ? '\u221E' : beds} beds)
                </span>
                <input
                  type="number"
                  min={0}
                  max={maxAdmit === Infinity ? effectiveWaiting : maxAdmit}
                  value={admissions[id]}
                  onChange={(e) => setAdmit(id, parseInt(e.target.value) || 0)}
                  className="w-16 bg-gray-700 border border-gray-600 rounded px-2 py-1 text-sm text-center"
                />
              </div>
            )}

            {/* Accept transfers */}
            {Object.entries(dept.requests_waiting).map(([fromId, count]) => {
              if (count === 0) return null;
              return (
                <div key={fromId} className="flex items-center justify-between gap-2">
                  <span className="text-sm text-gray-300">
                    Accept from {DEPT_NAMES[fromId as DepartmentId]} ({count} waiting)
                  </span>
                  <input
                    type="number"
                    min={0}
                    max={count}
                    value={accepts[`${id}-${fromId}`] ?? 0}
                    onChange={(e) => setAccept(id, fromId as DepartmentId, parseInt(e.target.value) || 0)}
                    className="w-16 bg-gray-700 border border-gray-600 rounded px-2 py-1 text-sm text-center"
                  />
                </div>
              );
            })}
          </div>
        );
      })}

      <div className="pt-3 sticky bottom-0 bg-gradient-to-t from-gray-900 via-gray-900">
        <button
          onClick={handleSubmit}
          disabled={loading}
          className="w-full py-2 bg-blue-600 hover:bg-blue-500 disabled:bg-gray-700 rounded-lg font-medium transition-colors cursor-pointer"
        >
          {loading ? 'Processing...' : 'Submit Arrivals'}
        </button>
      </div>
    </div>
  );
}
