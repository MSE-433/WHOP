import { useState } from 'react';
import { useGameStore } from '../../store/gameStore';
import type { ExitsAction, ExitRouting, DepartmentId } from '../../types/game';
import { ALL_DEPARTMENTS } from '../../types/game';
import { DEPT_NAMES, DEPT_TEXT } from '../../utils/formatters';
import { FLOW_GRAPH } from '../../utils/flowGraph';

export function ExitsForm() {
  const { state, loading, recommendation, submitExits } = useGameStore();

  // Track walkout counts and transfer counts per department
  const [walkouts, setWalkouts] = useState<Record<DepartmentId, number>>(
    { er: 0, surgery: 0, cc: 0, sd: 0 }
  );
  const [transfers, setTransfers] = useState<Record<string, number>>({});

  if (!state) return null;

  // Compute available exits from game state
  // During exits step, patients_in_beds + patients_in_hallway represent those who can exit
  // The server validates the actual available exits count

  function applyRecommendation() {
    if (!recommendation?.recommended_action) return;
    const action = recommendation.recommended_action as unknown as ExitsAction;
    const newWalkouts: Record<DepartmentId, number> = { er: 0, surgery: 0, cc: 0, sd: 0 };
    const newTransfers: Record<string, number> = {};
    for (const r of action.routings ?? []) {
      newWalkouts[r.from_dept as DepartmentId] = r.walkout_count;
      for (const [dest, count] of Object.entries(r.transfers ?? {})) {
        newTransfers[`${r.from_dept}-${dest}`] = count;
      }
    }
    setWalkouts(newWalkouts);
    setTransfers(newTransfers);
  }

  function handleSubmit() {
    const routings: ExitRouting[] = ALL_DEPARTMENTS
      .map((id) => {
        const transferMap: Record<DepartmentId, number> = {} as Record<DepartmentId, number>;
        for (const dest of FLOW_GRAPH[id]) {
          const count = transfers[`${id}-${dest}`] ?? 0;
          if (count > 0) transferMap[dest] = count;
        }
        return {
          from_dept: id,
          walkout_count: walkouts[id],
          transfers: transferMap,
        };
      })
      .filter((r) => r.walkout_count > 0 || Object.keys(r.transfers).length > 0);

    submitExits({ routings });
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="font-semibold text-lg">Exits</h3>
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
        Route exiting patients: discharge (walkout) or transfer to another department.
      </p>

      {ALL_DEPARTMENTS.map((id) => {
        const dept = state.departments[id];
        const destinations = FLOW_GRAPH[id];

        return (
          <div key={id} className="bg-gray-800/50 rounded-lg p-3 space-y-2">
            <div className={`text-sm font-medium ${DEPT_TEXT[id]}`}>
              {DEPT_NAMES[id]}
              <span className="text-gray-500 ml-2 text-xs">
                ({dept.patients_in_beds + dept.patients_in_hallway} patients)
              </span>
            </div>

            {/* Walkout */}
            <div className="flex items-center justify-between gap-2">
              <span className="text-sm text-gray-300">Discharge</span>
              <input
                type="number"
                min={0}
                value={walkouts[id]}
                onChange={(e) => setWalkouts((prev) => ({ ...prev, [id]: Math.max(0, parseInt(e.target.value) || 0) }))}
                className="w-16 bg-gray-700 border border-gray-600 rounded px-2 py-1 text-sm text-center"
              />
            </div>

            {/* Transfers */}
            {destinations.map((dest) => (
              <div key={dest} className="flex items-center justify-between gap-2">
                <span className="text-sm text-gray-300">
                  Transfer to {DEPT_NAMES[dest]}
                </span>
                <input
                  type="number"
                  min={0}
                  value={transfers[`${id}-${dest}`] ?? 0}
                  onChange={(e) => setTransfers((prev) => ({
                    ...prev,
                    [`${id}-${dest}`]: Math.max(0, parseInt(e.target.value) || 0),
                  }))}
                  className="w-16 bg-gray-700 border border-gray-600 rounded px-2 py-1 text-sm text-center"
                />
              </div>
            ))}
          </div>
        );
      })}

      <button
        onClick={handleSubmit}
        disabled={loading}
        className="w-full py-2 bg-blue-600 hover:bg-blue-500 disabled:bg-gray-700 rounded-lg font-medium transition-colors cursor-pointer"
      >
        {loading ? 'Processing...' : 'Submit Exits'}
      </button>
    </div>
  );
}
