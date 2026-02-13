import { useGameStore } from '../../store/gameStore';
import type { ExitRouting, DepartmentId } from '../../types/game';
import { ALL_DEPARTMENTS } from '../../types/game';
import { DEPT_NAMES, DEPT_TEXT } from '../../utils/formatters';

const _ER_PATTERN = ["out", "out", "out", "out", "out", "surgery", "out", "stepdown", "out", "criticalcare", "out", "criticalcare", "out", "stepdown", "out"];

const EXIT_SEQUENCES: Record<DepartmentId, string[]> = {
  er: Array(6).fill(_ER_PATTERN).flat(), // Repeat pattern 6 times to cover all 80 exits
  surgery: ["stepdown", "stepdown", "stepdown", "criticalcare", "stepdown", "stepdown", "criticalcare", "criticalcare", "stepdown", "stepdown", "stepdown", "criticalcare", "stepdown", "stepdown", "criticalcare", "criticalcare"],
  cc: Array(100).fill("stepdown"), // Always stepdown
  sd: Array(100).fill("out"), // Always out
};

const EXIT_COUNTS: Record<DepartmentId, number[]> = {
  er: [5, 2, 2, 4, 4, 2, 5, 5, 3, 1, 4, 3, 5, 2, 2, 4, 4, 2, 5, 5, 3, 1, 4, 3],
  surgery: [0, 0, 1, 2, 0, 0, 1, 2, 0, 0, 1, 2, 0, 0, 1, 2, 0, 0, 1, 2, 0, 0, 1, 2],
  cc: [0, 0, 1, 0, 1, 2, 0, 0, 1, 0, 1, 2, 0, 0, 1, 0, 1, 2, 0, 0, 1, 0, 1, 2],
  sd: [3, 2, 4, 3, 1, 2, 3, 2, 0, 0, 0, 0, 0, 0, 0, 0, 3, 2, 4, 3, 1, 2, 3, 2],
};

// Map sequence destination strings to DepartmentIds
function mapDestinationToDeptId(dest: string): DepartmentId | null {
  switch (dest) {
    case 'stepdown':
      return 'sd';
    case 'surgery':
      return 'surgery';
    case 'criticalcare':
      return 'cc';
    case 'out':
      return null; // discharge, not a dept
    default:
      return null;
  }
}

export function ExitsForm() {
  const { state, loading, submitExits } = useGameStore();

  if (!state) return null;

  function getExitOutcomes(deptId: DepartmentId): { destination: string; count: number }[] {
    const roundIdx = state!.round_number - 1;
    const exitCount = EXIT_COUNTS[deptId]?.[roundIdx] ?? 0;
    const sequence = EXIT_SEQUENCES[deptId] ?? [];
    
    // Calculate cumulative offset: how many exits occurred in all previous rounds
    let offset = 0;
    for (let r = 0; r < roundIdx; r++) {
      offset += EXIT_COUNTS[deptId]?.[r] ?? 0;
    }
    
    const outcomes: { destination: string; count: number }[] = [];
    
    for (let i = 0; i < exitCount; i++) {
      const dest = sequence[offset + i] ?? 'unknown';
      const existing = outcomes.find((o) => o.destination === dest);
      if (existing) {
        existing.count += 1;
      } else {
        outcomes.push({ destination: dest, count: 1 });
      }
    }
    
    return outcomes;
  }

  function handleSubmit() {
    // Automatically build routings based on sequences
    const routings: ExitRouting[] = ALL_DEPARTMENTS
      .map((id) => {
        const outcomes = getExitOutcomes(id);
        const transferMap: Record<DepartmentId, number> = {} as Record<DepartmentId, number>;
        let walkoutCount = 0;

        for (const outcome of outcomes) {
          if (outcome.destination === 'out') {
            walkoutCount += outcome.count;
          } else if (outcome.destination === 'stepdown') {
            transferMap['sd'] = (transferMap['sd'] ?? 0) + outcome.count;
          } else if (outcome.destination === 'surgery') {
            transferMap['surgery'] = (transferMap['surgery'] ?? 0) + outcome.count;
          } else if (outcome.destination === 'criticalcare') {
            transferMap['cc'] = (transferMap['cc'] ?? 0) + outcome.count;
          }
        }

        return {
          from_dept: id,
          walkout_count: walkoutCount,
          transfers: transferMap,
        };
      })
      .filter((r) => r.walkout_count > 0 || Object.keys(r.transfers).length > 0);

    submitExits({ routings });
  }

  return (
    <div className="space-y-4">
      <h3 className="font-semibold text-lg">Exits</h3>

      <p className="text-gray-400 text-xs">
        Exits are automatically routed per predetermined sequences. Outcomes shown below.
      </p>

      {ALL_DEPARTMENTS.map((id) => {
        const outcomes = getExitOutcomes(id);
        const totalExits = outcomes.reduce((sum, o) => sum + o.count, 0);

        if (totalExits === 0) return null;

        return (
          <div key={id} className="bg-gray-800/50 rounded-lg p-3 space-y-2">
            <div className={`text-sm font-medium ${DEPT_TEXT[id]}`}>
              {DEPT_NAMES[id]}
              <span className="text-gray-500 ml-2 text-xs">
                ({totalExits} exits)
              </span>
            </div>

            {/* Show sequence outcomes */}
            <div className="space-y-1">
              {outcomes.map((outcome, idx) => {
                let destName: string;
                if (outcome.destination === 'out') {
                  destName = 'Discharge';
                } else {
                  const mappedDeptId = mapDestinationToDeptId(outcome.destination);
                  destName = mappedDeptId ? `Transfer to ${DEPT_NAMES[mappedDeptId]}` : `Transfer to ${outcome.destination}`;
                }
                return (
                  <div key={idx} className="flex items-center justify-between gap-2 text-sm">
                    <span className="text-gray-300">{destName}</span>
                    <span className="text-blue-300 font-semibold">{outcome.count}</span>
                  </div>
                );
              })}
            </div>
          </div>
        );
      })}

      <div className="pt-3 sticky bottom-0 bg-gradient-to-t from-gray-900 via-gray-900">
        <button
          onClick={handleSubmit}
          disabled={loading}
          className="w-full py-2 bg-blue-600 hover:bg-blue-500 disabled:bg-gray-700 rounded-lg font-medium transition-colors cursor-pointer"
        >
          {loading ? 'Processing...' : 'Continue'}
        </button>
      </div>
    </div>
  );
}
