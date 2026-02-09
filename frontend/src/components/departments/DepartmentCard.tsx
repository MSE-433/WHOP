import type { DepartmentId, DepartmentState } from '../../types/game';
import { DEPT_NAMES, DEPT_ACCENTS, DEPT_BG, DEPT_TEXT } from '../../utils/formatters';
import { coreIdle, extraIdle, totalPatients, bedsAvailable, totalRequestsWaiting } from '../../utils/staffUtils';

interface Props {
  dept: DepartmentState;
}

export function DepartmentCard({ dept }: Props) {
  const id = dept.id as DepartmentId;
  const cIdle = coreIdle(dept.staff);
  const eIdle = extraIdle(dept.staff);
  const reqWaiting = totalRequestsWaiting(dept);
  const patients = totalPatients(dept);
  const bedsLeft = bedsAvailable(dept);
  const totalWaiting = dept.arrivals_waiting + reqWaiting;

  // Count staff tied up with outgoing transfer patients (still occupied until accepted)
  const outgoingTransferStaff = dept.outgoing_transfers.reduce((sum, t) => sum + t.count, 0);

  return (
    <div className={`rounded-lg border-l-4 ${DEPT_ACCENTS[id]} ${DEPT_BG[id]} p-4`}>
      {/* Header */}
      <div className="flex items-center justify-between mb-2">
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

      {/* Summary row */}
      <div className="flex items-center gap-3 mb-3">
        <div className="text-lg font-medium text-white">
          {patients} <span className="text-xs text-gray-400 font-normal">patients</span>
        </div>
        <div className="text-sm text-gray-300">
          {bedsLeft === Infinity ? '~' : bedsLeft} <span className="text-xs text-gray-500">beds free</span>
        </div>
        {totalWaiting > 0 && (
          <span className="px-2 py-0.5 bg-yellow-600/20 text-yellow-400 text-xs font-medium rounded-full">
            {totalWaiting} waiting
          </span>
        )}
      </div>

      {/* Patients section */}
      <div className="space-y-1 text-xs mb-3 border-t border-gray-700/50 pt-2">
        <div className="flex justify-between">
          <span className="text-gray-500 pl-2">In beds</span>
          <span className="text-gray-300">
            {dept.patients_in_beds}
            <span className="text-gray-500">/{dept.bed_capacity ?? '~'}</span>
            {bedsLeft !== Infinity && bedsLeft > 0 && (
              <span className="text-green-400/70 ml-1">({bedsLeft} avail)</span>
            )}
            {bedsLeft === 0 && dept.bed_capacity !== null && (
              <span className="text-red-400/70 ml-1">(full)</span>
            )}
          </span>
        </div>
        {dept.patients_in_hallway > 0 && (
          <div className="flex justify-between">
            <span className="text-gray-500 pl-2">In hallway</span>
            <span className="text-yellow-400">{dept.patients_in_hallway}</span>
          </div>
        )}
      </div>

      {/* Staff section */}
      <div className="space-y-1 text-xs mb-3 border-t border-gray-700/50 pt-2">
        <div className="text-gray-400 font-medium uppercase tracking-wide mb-1">Staff</div>

        {/* Core staff */}
        <div className="flex justify-between">
          <span className="text-gray-500 pl-2">Core busy</span>
          <span className="text-gray-300">{dept.staff.core_busy}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-500 pl-2">Core idle</span>
          <span className={cIdle > 0 ? 'text-green-400 font-medium' : 'text-gray-500'}>{cIdle}</span>
        </div>

        {/* Extra staff */}
        {(dept.staff.extra_total > 0 || dept.staff.extra_incoming > 0) && (
          <>
            <div className="flex justify-between">
              <span className="text-gray-500 pl-2">Extra busy</span>
              <span className="text-blue-300">{dept.staff.extra_busy}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500 pl-2">Extra idle</span>
              <span className={eIdle > 0 ? 'text-blue-400 font-medium' : 'text-gray-500'}>{eIdle}</span>
            </div>
          </>
        )}

        {/* Extra incoming */}
        {dept.staff.extra_incoming > 0 && (
          <div className="flex justify-between">
            <span className="text-gray-500 pl-2">Incoming next round</span>
            <span className="text-cyan-400">+{dept.staff.extra_incoming}</span>
          </div>
        )}

        {/* Unavailable */}
        {dept.staff.unavailable > 0 && (
          <div className="flex justify-between">
            <span className="text-gray-500 pl-2">Unavailable (events)</span>
            <span className="text-red-400">{dept.staff.unavailable}</span>
          </div>
        )}

        {/* Outgoing transfer staff */}
        {outgoingTransferStaff > 0 && (
          <div className="flex justify-between">
            <span className="text-gray-500 pl-2">Holding transfers</span>
            <span className="text-amber-400">{outgoingTransferStaff}</span>
          </div>
        )}
      </div>

      {/* Waiting section */}
      {(dept.arrivals_waiting > 0 || reqWaiting > 0) && (
        <div className="space-y-1 text-xs mb-3 border-t border-gray-700/50 pt-2">
          <div className="text-gray-400 font-medium uppercase tracking-wide mb-1">Waiting</div>
          {dept.arrivals_waiting > 0 && (
            <div className="flex justify-between">
              <span className="text-gray-500 pl-2">Walk-in arrivals</span>
              <span className="text-yellow-400 font-medium">{dept.arrivals_waiting}</span>
            </div>
          )}
          {Object.entries(dept.requests_waiting).map(([fromDept, count]) => {
            if (count <= 0) return null;
            const fromName: Record<string, string> = { er: 'ER', surgery: 'Surgery', cc: 'CC', sd: 'SD' };
            return (
              <div key={fromDept} className="flex justify-between">
                <span className="text-gray-500 pl-2">Request from {fromName[fromDept] ?? fromDept}</span>
                <span className="text-yellow-400 font-medium">{count}</span>
              </div>
            );
          })}
        </div>
      )}

      {/* Active Events */}
      {dept.active_events.length > 0 && (
        <div className="border-t border-gray-700/50 pt-2">
          <div className="text-gray-400 text-xs font-medium uppercase tracking-wide mb-1">Events</div>
          {dept.active_events.map((evt) => (
            <div key={evt.event_id} className="text-xs text-amber-300 flex justify-between">
              <span className="truncate mr-2">{evt.description}</span>
              <span className="text-gray-500 shrink-0">
                {evt.rounds_remaining === null ? 'Perm' : `${evt.rounds_remaining}r`}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
