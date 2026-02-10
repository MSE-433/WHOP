import { useState, useEffect } from 'react';
import { useGameStore } from '../../store/gameStore';
import { ALL_DEPARTMENTS } from '../../types/game';
import type { DepartmentId, CardOverrides } from '../../types/game';
import { DEPT_NAMES, DEPT_TEXT } from '../../utils/formatters';
import { isEventRound } from '../../utils/timeMapping';

export function EventView() {
  const { state, loading, submitEvent, roundCards } = useGameStore();

  const [arrivalEdits, setArrivalEdits] = useState<Record<DepartmentId, number>>(
    { er: 0, surgery: 0, cc: 0, sd: 0 }
  );
  const [exitEdits, setExitEdits] = useState<Record<DepartmentId, number>>(
    { er: 0, surgery: 0, cc: 0, sd: 0 }
  );

  // Initialize edits from card defaults when roundCards loads
  useEffect(() => {
    if (roundCards) {
      const newArrivals: Record<DepartmentId, number> = { er: 0, surgery: 0, cc: 0, sd: 0 };
      const newExits: Record<DepartmentId, number> = { er: 0, surgery: 0, cc: 0, sd: 0 };
      for (const id of ALL_DEPARTMENTS) {
        const card = roundCards.departments[id];
        if (card) {
          newArrivals[id] = card.arrivals;
          newExits[id] = card.exits;
        }
      }
      setArrivalEdits(newArrivals);
      setExitEdits(newExits);
    }
  }, [roundCards]);

  if (!state) return null;

  const isEvent = isEventRound(state.round_number);

  function getCardDefault(id: DepartmentId, field: 'arrivals' | 'exits'): number {
    if (!roundCards) return 0;
    const card = roundCards.departments[id];
    return card ? card[field] : 0;
  }

  function handleContinue() {
    // Build overrides: only include depts where the user changed values
    const arrivalOverrides: Record<string, number> = {};
    const exitOverrides: Record<string, number> = {};
    let hasOverrides = false;

    for (const id of ALL_DEPARTMENTS) {
      if (arrivalEdits[id] !== getCardDefault(id, 'arrivals')) {
        arrivalOverrides[id] = arrivalEdits[id];
        hasOverrides = true;
      }
      if (exitEdits[id] !== getCardDefault(id, 'exits')) {
        exitOverrides[id] = exitEdits[id];
        hasOverrides = true;
      }
    }

    if (hasOverrides) {
      const overrides: CardOverrides = {};
      if (Object.keys(arrivalOverrides).length > 0) {
        overrides.arrivals = arrivalOverrides as Record<DepartmentId, number>;
      }
      if (Object.keys(exitOverrides).length > 0) {
        overrides.exits = exitOverrides as Record<DepartmentId, number>;
      }
      submitEvent(undefined, overrides);
    } else {
      submitEvent();
    }
  }

  const hasAnyChange = roundCards && ALL_DEPARTMENTS.some(
    (id) =>
      arrivalEdits[id] !== getCardDefault(id, 'arrivals') ||
      exitEdits[id] !== getCardDefault(id, 'exits')
  );

  function handleReset() {
    if (!roundCards) return;
    const newArrivals: Record<DepartmentId, number> = { er: 0, surgery: 0, cc: 0, sd: 0 };
    const newExits: Record<DepartmentId, number> = { er: 0, surgery: 0, cc: 0, sd: 0 };
    for (const id of ALL_DEPARTMENTS) {
      const card = roundCards.departments[id];
      if (card) {
        newArrivals[id] = card.arrivals;
        newExits[id] = card.exits;
      }
    }
    setArrivalEdits(newArrivals);
    setExitEdits(newExits);
  }

  return (
    <div className="space-y-4">
      <h3 className="font-semibold text-lg">Events</h3>

      {isEvent ? (
        <p className="text-amber-300 text-sm">
          This is an event round. Events will be drawn when you continue.
        </p>
      ) : (
        <p className="text-gray-400 text-sm">
          No events this round.
        </p>
      )}

      {/* Editable Round Card Draw */}
      {roundCards && (
        <div className="bg-gray-800/50 border border-gray-700/50 rounded-lg p-3 space-y-2">
          <div className="flex items-center justify-between">
            <div className="text-xs text-gray-400 font-medium uppercase tracking-wide">
              Round {roundCards.round} Card Draw (editable)
            </div>
            {hasAnyChange && (
              <button
                onClick={handleReset}
                className="text-[10px] text-gray-500 hover:text-gray-300 cursor-pointer"
              >
                Reset to defaults
              </button>
            )}
          </div>
          <div className="grid grid-cols-2 gap-2">
            {ALL_DEPARTMENTS.map((id: DepartmentId) => {
              const card = roundCards.departments[id];
              if (!card) return null;
              const arrDefault = card.arrivals;
              const extDefault = card.exits;
              const arrChanged = arrivalEdits[id] !== arrDefault;
              const extChanged = exitEdits[id] !== extDefault;

              return (
                <div key={id} className="bg-gray-900/50 rounded px-2.5 py-2 space-y-1.5">
                  <div className={`text-xs font-medium ${DEPT_TEXT[id]}`}>
                    {DEPT_NAMES[id]}
                  </div>
                  {/* Arrivals */}
                  <div className="flex items-center justify-between gap-2">
                    <div className="flex items-center gap-1">
                      <span className="text-xs text-green-400">Arrivals</span>
                      {arrChanged && (
                        <span className="text-[10px] text-amber-400">(was {arrDefault})</span>
                      )}
                    </div>
                    <input
                      type="number"
                      min={0}
                      value={arrivalEdits[id]}
                      onChange={(e) =>
                        setArrivalEdits((prev) => ({
                          ...prev,
                          [id]: Math.max(0, parseInt(e.target.value) || 0),
                        }))
                      }
                      className={`w-14 bg-gray-700 border rounded px-1.5 py-0.5 text-xs text-center ${
                        arrChanged ? 'border-amber-500/60 text-amber-300' : 'border-gray-600'
                      }`}
                    />
                  </div>
                  {/* Exits */}
                  <div className="flex items-center justify-between gap-2">
                    <div className="flex items-center gap-1">
                      <span className="text-xs text-blue-400">Exits</span>
                      {extChanged && (
                        <span className="text-[10px] text-amber-400">(was {extDefault})</span>
                      )}
                    </div>
                    <input
                      type="number"
                      min={0}
                      value={exitEdits[id]}
                      onChange={(e) =>
                        setExitEdits((prev) => ({
                          ...prev,
                          [id]: Math.max(0, parseInt(e.target.value) || 0),
                        }))
                      }
                      className={`w-14 bg-gray-700 border rounded px-1.5 py-0.5 text-xs text-center ${
                        extChanged ? 'border-amber-500/60 text-amber-300' : 'border-gray-600'
                      }`}
                    />
                  </div>
                  {/* ER detail hint */}
                  {id === 'er' && card.walkin != null && card.ambulance != null && !arrChanged && (
                    <div className="text-[10px] text-gray-500">
                      ({card.walkin} walk-in{card.ambulance > 0 ? `, ${card.ambulance} ambulance` : ''})
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Show current active events */}
      {ALL_DEPARTMENTS.some((id) => state.departments[id].active_events.length > 0) && (
        <div className="space-y-2">
          <p className="text-xs text-gray-500 uppercase tracking-wide">Active Events</p>
          {ALL_DEPARTMENTS.map((id) => {
            const events = state.departments[id].active_events;
            if (events.length === 0) return null;
            return (
              <div key={id}>
                <span className={`text-sm font-medium ${DEPT_TEXT[id]}`}>{DEPT_NAMES[id]}</span>
                {events.map((evt) => (
                  <p key={evt.event_id} className="text-xs text-gray-300 ml-2">
                    {evt.description}
                    <span className="text-gray-500 ml-1">
                      ({evt.rounds_remaining === null ? 'permanent' : `${evt.rounds_remaining} rounds left`})
                    </span>
                  </p>
                ))}
              </div>
            );
          })}
        </div>
      )}

      <div className="pt-3 sticky bottom-0 bg-gradient-to-t from-gray-900 via-gray-900">
        <button
          onClick={handleContinue}
          disabled={loading}
          className="w-full py-2 bg-blue-600 hover:bg-blue-500 disabled:bg-gray-700 rounded-lg font-medium transition-colors cursor-pointer"
        >
          {loading ? 'Processing...' : 'Continue'}
        </button>
      </div>
    </div>
  );
}
