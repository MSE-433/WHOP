import type { DepartmentId, DepartmentState } from '../../types/game';
import { DEPT_NAMES, DEPT_ACCENTS, DEPT_BG, DEPT_TEXT } from '../../utils/formatters';
import { totalIdle, totalBusy, totalOnDuty, totalRequestsWaiting } from '../../utils/staffUtils';

interface Props {
  dept: DepartmentState;
}

export function DepartmentCard({ dept }: Props) {
  const id = dept.id as DepartmentId;
  const idle = totalIdle(dept.staff);
  const busy = totalBusy(dept.staff);
  const onDuty = totalOnDuty(dept.staff);
  const reqWaiting = totalRequestsWaiting(dept);

  return (
    <div className={`rounded-lg border-l-4 ${DEPT_ACCENTS[id]} ${DEPT_BG[id]} p-4`}>
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <h3 className={`font-semibold ${DEPT_TEXT[id]}`}>{DEPT_NAMES[id]}</h3>
        <div className="flex gap-1">
          {dept.is_closed && (
            <span className="px-2 py-0.5 bg-red-600/30 text-red-400 text-xs rounded-full">Closed</span>
          )}
          {dept.is_diverting && (
            <span className="px-2 py-0.5 bg-orange-600/30 text-orange-400 text-xs rounded-full">Diverting</span>
          )}
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-2 gap-y-2 gap-x-4 text-sm">
        {/* Beds */}
        <div className="text-gray-400">Beds</div>
        <div className="text-right">
          <span className="text-white font-medium">{dept.patients_in_beds}</span>
          <span className="text-gray-500">
            /{dept.bed_capacity ?? '∞'}
          </span>
          {dept.patients_in_hallway > 0 && (
            <span className="text-yellow-400 ml-1">(+{dept.patients_in_hallway} hall)</span>
          )}
        </div>

        {/* Staff */}
        <div className="text-gray-400">Staff</div>
        <div className="text-right">
          <span className="text-white font-medium">{busy}</span>
          <span className="text-gray-500">/{onDuty}</span>
          <span className="text-green-400 ml-1">({idle} idle)</span>
        </div>

        {/* Extra Staff */}
        {(dept.staff.extra_total > 0 || dept.staff.extra_incoming > 0) && (
          <>
            <div className="text-gray-400">Extra</div>
            <div className="text-right text-blue-400 text-xs">
              {dept.staff.extra_total} on duty
              {dept.staff.extra_incoming > 0 && ` +${dept.staff.extra_incoming} incoming`}
            </div>
          </>
        )}

        {/* Unavailable */}
        {dept.staff.unavailable > 0 && (
          <>
            <div className="text-gray-400">Unavail.</div>
            <div className="text-right text-red-400">{dept.staff.unavailable}</div>
          </>
        )}

        {/* Waiting */}
        {(dept.arrivals_waiting > 0 || reqWaiting > 0) && (
          <>
            <div className="text-gray-400">Waiting</div>
            <div className="text-right text-yellow-400">
              {dept.arrivals_waiting > 0 && `${dept.arrivals_waiting} arrivals`}
              {dept.arrivals_waiting > 0 && reqWaiting > 0 && ', '}
              {reqWaiting > 0 && `${reqWaiting} transfers`}
            </div>
          </>
        )}
      </div>

      {/* Active Events */}
      {dept.active_events.length > 0 && (
        <div className="mt-3 border-t border-gray-700/50 pt-2">
          {dept.active_events.map((evt) => (
            <div key={evt.event_id} className="text-xs text-amber-300 flex justify-between">
              <span>{evt.description}</span>
              <span className="text-gray-500">
                {evt.rounds_remaining === null ? 'Perm' : `${evt.rounds_remaining}r`}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
