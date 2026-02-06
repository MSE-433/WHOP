import { useState } from 'react';
import { useGameStore } from '../../store/gameStore';
import type { CustomGameConfig, DeptConfig } from '../../api/client';
import type { DepartmentId } from '../../types/game';
import { DEPT_NAMES, DEPT_TEXT } from '../../utils/formatters';

const DEPT_ORDER: DepartmentId[] = ['er', 'surgery', 'cc', 'sd'];
const FIELDS: (keyof DeptConfig)[] = ['patients', 'core_staff', 'bed_capacity'];

const DEFAULTS: Record<DepartmentId, { patients: number; core_staff: number; bed_capacity: number }> = {
  er: { patients: 16, core_staff: 18, bed_capacity: 25 },
  surgery: { patients: 4, core_staff: 6, bed_capacity: 9 },
  cc: { patients: 12, core_staff: 13, bed_capacity: 18 },
  sd: { patients: 20, core_staff: 24, bed_capacity: 30 },
};

type UnlimitedFlags = Record<DepartmentId, Record<keyof DeptConfig, boolean>>;

function initUnlimited(): UnlimitedFlags {
  const out: Partial<UnlimitedFlags> = {};
  for (const dept of DEPT_ORDER) {
    out[dept] = { patients: false, core_staff: false, bed_capacity: false };
  }
  return out as UnlimitedFlags;
}

export function StartScreen() {
  const { loading, error, newGame } = useGameStore();
  const [showCustom, setShowCustom] = useState(false);
  const [params, setParams] = useState(DEFAULTS);
  const [unlimited, setUnlimited] = useState<UnlimitedFlags>(initUnlimited);

  function updateDept(dept: DepartmentId, field: keyof DeptConfig, value: string) {
    const num = parseInt(value, 10);
    if (isNaN(num) || num < 0) return;
    setParams((prev) => ({
      ...prev,
      [dept]: { ...prev[dept], [field]: num },
    }));
  }

  function toggleUnlimited(dept: DepartmentId, field: keyof DeptConfig) {
    setUnlimited((prev) => ({
      ...prev,
      [dept]: { ...prev[dept], [field]: !prev[dept][field] },
    }));
  }

  function handleStart() {
    if (!showCustom) {
      newGame();
      return;
    }
    const config: CustomGameConfig = {};
    for (const dept of DEPT_ORDER) {
      const d = params[dept];
      const def = DEFAULTS[dept];
      const changes: DeptConfig = {};
      let hasChange = false;

      for (const field of FIELDS) {
        if (unlimited[dept][field]) {
          changes[field] = -1; // -1 = unlimited in API
          hasChange = true;
        } else if (d[field] !== def[field]) {
          changes[field] = d[field];
          hasChange = true;
        }
      }

      if (hasChange) {
        (config as Record<string, DeptConfig>)[dept] = changes;
      }
    }
    newGame(Object.keys(config).length > 0 ? config : undefined);
  }

  function handleReset() {
    setParams(DEFAULTS);
    setUnlimited(initUnlimited());
  }

  function renderCell(dept: DepartmentId, field: keyof DeptConfig) {
    const isUnlimited = unlimited[dept][field];
    return (
      <div className="flex items-center gap-1">
        {isUnlimited ? (
          <span className="flex-1 text-center text-sm text-cyan-400 font-medium">
            &infin;
          </span>
        ) : (
          <input
            type="number"
            min={0}
            value={params[dept][field]}
            onChange={(e) => updateDept(dept, field, e.target.value)}
            className="flex-1 min-w-0 bg-gray-700 border border-gray-600 rounded px-2 py-1.5 text-sm text-center text-white focus:border-blue-500 focus:outline-none"
          />
        )}
        <button
          onClick={() => toggleUnlimited(dept, field)}
          title={isUnlimited ? 'Set fixed value' : 'Set unlimited'}
          className={`shrink-0 w-6 h-6 rounded text-xs font-bold cursor-pointer transition-colors ${
            isUnlimited
              ? 'bg-cyan-600 text-white'
              : 'bg-gray-700 text-gray-500 hover:bg-gray-600 hover:text-gray-300'
          }`}
        >
          &infin;
        </button>
      </div>
    );
  }

  return (
    <div className="flex flex-col items-center justify-center min-h-screen p-6">
      <div className="max-w-2xl w-full space-y-8">
        {/* Title */}
        <div className="text-center space-y-2">
          <h1 className="text-5xl font-bold tracking-tight">WHOP</h1>
          <p className="text-gray-400 text-lg">
            Workflow-guided Hospital Outcomes Platform
          </p>
          <p className="text-gray-500 text-sm">
            Friday Night at the ER — Intelligent Decision Support
          </p>
        </div>

        {/* Toggle custom params */}
        <div className="flex justify-center">
          <button
            onClick={() => setShowCustom(!showCustom)}
            className="text-sm text-blue-400 hover:text-blue-300 transition-colors cursor-pointer"
          >
            {showCustom ? 'Hide custom parameters' : 'Customize starting parameters'}
          </button>
        </div>

        {/* Custom params form */}
        {showCustom && (
          <div className="bg-gray-800/50 border border-gray-700 rounded-xl p-5 space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-medium text-gray-300">Starting Configuration</h3>
              <button
                onClick={handleReset}
                className="text-xs text-gray-500 hover:text-gray-300 transition-colors cursor-pointer"
              >
                Reset to defaults
              </button>
            </div>

            {/* Header row */}
            <div className="grid grid-cols-4 gap-3 text-xs text-gray-500 px-1">
              <div>Department</div>
              <div className="text-center">Patients</div>
              <div className="text-center">Core Staff</div>
              <div className="text-center">Bed Capacity</div>
            </div>

            {/* Department rows */}
            {DEPT_ORDER.map((dept) => (
              <div key={dept} className="grid grid-cols-4 gap-3 items-center">
                <div className={`text-sm font-medium ${DEPT_TEXT[dept]}`}>
                  {DEPT_NAMES[dept]}
                </div>
                {renderCell(dept, 'patients')}
                {renderCell(dept, 'core_staff')}
                {renderCell(dept, 'bed_capacity')}
              </div>
            ))}

            <p className="text-xs text-gray-600">
              Click the &infin; button to toggle unlimited for any parameter.
              Unlimited beds means hallway overflow with no cap.
              Unlimited patients/staff uses 999 as a large value.
            </p>
          </div>
        )}

        {/* Start button */}
        <button
          onClick={handleStart}
          disabled={loading}
          className="w-full py-3 bg-blue-600 hover:bg-blue-500 disabled:bg-gray-700 rounded-lg text-lg font-medium transition-colors cursor-pointer"
        >
          {loading ? 'Starting...' : 'Start Game'}
        </button>

        {error && (
          <p className="text-red-400 text-sm text-center">{error}</p>
        )}
      </div>
    </div>
  );
}
