import { useGameStore } from '../../store/gameStore';
import { ALL_DEPARTMENTS } from '../../types/game';
import { DEPT_NAMES, DEPT_TEXT } from '../../utils/formatters';
import { isEventRound } from '../../utils/timeMapping';

export function EventView() {
  const { state, loading, submitEvent } = useGameStore();
  if (!state) return null;

  const isEvent = isEventRound(state.round_number);

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

      <button
        onClick={() => submitEvent()}
        disabled={loading}
        className="w-full py-2 bg-blue-600 hover:bg-blue-500 disabled:bg-gray-700 rounded-lg font-medium transition-colors cursor-pointer"
      >
        {loading ? 'Processing...' : 'Continue'}
      </button>
    </div>
  );
}
