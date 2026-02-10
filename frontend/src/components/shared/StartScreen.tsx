import { useState } from 'react';
import { useGameStore } from '../../store/gameStore';
import type { CustomGameConfig, DeptConfig, CostConfig } from '../../api/client';
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

type CostKey = keyof CostConfig;

interface CostField {
  key: CostKey;
  label: string;
  defaultValue: number;
}

const COST_FIELDS: CostField[] = [
  { key: 'er_diversion_financial', label: 'ER Diversion (Financial)', defaultValue: 5000 },
  { key: 'er_diversion_quality', label: 'ER Diversion (Quality)', defaultValue: 200 },
  { key: 'er_waiting_financial', label: 'ER Waiting (Financial)', defaultValue: 150 },
  { key: 'er_waiting_quality', label: 'ER Waiting (Quality)', defaultValue: 20 },
  { key: 'extra_staff_financial', label: 'Extra Staff (Financial)', defaultValue: 40 },
  { key: 'extra_staff_quality', label: 'Extra Staff (Quality)', defaultValue: 5 },
  { key: 'arrivals_waiting_financial', label: 'Dept Arrivals Waiting (Financial)', defaultValue: 3750 },
  { key: 'arrivals_waiting_quality', label: 'Dept Arrivals Waiting (Quality)', defaultValue: 20 },
  { key: 'requests_waiting_financial', label: 'Transfer Requests Waiting (Financial)', defaultValue: 0 },
  { key: 'requests_waiting_quality', label: 'Transfer Requests Waiting (Quality)', defaultValue: 20 },
];

const COST_DEFAULTS: Record<CostKey, number> = Object.fromEntries(
  COST_FIELDS.map((f) => [f.key, f.defaultValue])
) as Record<CostKey, number>;

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
  const [showCosts, setShowCosts] = useState(false);
  const [params, setParams] = useState(DEFAULTS);
  const [unlimited, setUnlimited] = useState<UnlimitedFlags>(initUnlimited);
  const [costParams, setCostParams] = useState<Record<CostKey, number>>({ ...COST_DEFAULTS });

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

  function updateCost(key: CostKey, value: string) {
    const num = parseInt(value, 10);
    if (isNaN(num) || num < 0) return;
    setCostParams((prev) => ({ ...prev, [key]: num }));
  }

  function handleStart() {
    if (!showCustom && !showCosts) {
      newGame();
      return;
    }
    const config: CustomGameConfig = {};

    // Department overrides
    if (showCustom) {
      for (const dept of DEPT_ORDER) {
        const d = params[dept];
        const def = DEFAULTS[dept];
        const changes: DeptConfig = {};
        let hasChange = false;

        for (const field of FIELDS) {
          if (unlimited[dept][field]) {
            changes[field] = -1;
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
    }

    // Cost overrides
    if (showCosts) {
      const costOverrides: CostConfig = {};
      let hasCostChange = false;
      for (const field of COST_FIELDS) {
        if (costParams[field.key] !== field.defaultValue) {
          (costOverrides as Record<string, number>)[field.key] = costParams[field.key];
          hasCostChange = true;
        }
      }
      if (hasCostChange) {
        config.costs = costOverrides;
      }
    }

    const hasAnyConfig = Object.keys(config).length > 0;
    newGame(hasAnyConfig ? config : undefined);
  }

  function handleReset() {
    setParams(DEFAULTS);
    setUnlimited(initUnlimited());
    setCostParams({ ...COST_DEFAULTS });
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

        {/* Toggle buttons */}
        <div className="flex justify-center gap-4">
          <button
            onClick={() => setShowCustom(!showCustom)}
            className="text-sm text-blue-400 hover:text-blue-300 transition-colors cursor-pointer"
          >
            {showCustom ? 'Hide starting parameters' : 'Customize starting parameters'}
          </button>
          <span className="text-gray-600">|</span>
          <button
            onClick={() => setShowCosts(!showCosts)}
            className="text-sm text-blue-400 hover:text-blue-300 transition-colors cursor-pointer"
          >
            {showCosts ? 'Hide cost settings' : 'Customize cost constants'}
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

        {/* Cost constants form */}
        {showCosts && (
          <div className="bg-gray-800/50 border border-gray-700 rounded-xl p-5 space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-medium text-gray-300">Cost Constants</h3>
              <button
                onClick={() => setCostParams({ ...COST_DEFAULTS })}
                className="text-xs text-gray-500 hover:text-gray-300 transition-colors cursor-pointer"
              >
                Reset to defaults
              </button>
            </div>

            <div className="grid grid-cols-2 gap-3">
              {COST_FIELDS.map((field) => {
                const isChanged = costParams[field.key] !== field.defaultValue;
                return (
                  <div key={field.key} className="flex items-center justify-between gap-2 bg-gray-900/50 rounded px-3 py-2">
                    <div className="flex flex-col min-w-0">
                      <span className="text-xs text-gray-300 truncate">{field.label}</span>
                      {isChanged && (
                        <span className="text-[10px] text-amber-400">
                          default: ${field.defaultValue.toLocaleString()}
                        </span>
                      )}
                    </div>
                    <div className="flex items-center gap-1">
                      <span className="text-gray-500 text-xs">$</span>
                      <input
                        type="number"
                        min={0}
                        value={costParams[field.key]}
                        onChange={(e) => updateCost(field.key, e.target.value)}
                        className={`w-20 bg-gray-700 border rounded px-2 py-1 text-sm text-center ${
                          isChanged ? 'border-amber-500/60 text-amber-300' : 'border-gray-600 text-white'
                        } focus:border-blue-500 focus:outline-none`}
                      />
                    </div>
                  </div>
                );
              })}
            </div>

            <p className="text-xs text-gray-600">
              Financial costs affect the monetary score. Quality costs affect the quality score.
              Both are tracked per round and accumulated over the 24-round game.
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
