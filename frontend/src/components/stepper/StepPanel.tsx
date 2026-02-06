import { useGameStore } from '../../store/gameStore';
import { EventView } from './EventView';
import { ArrivalsForm } from './ArrivalsForm';
import { ExitsForm } from './ExitsForm';
import { ClosedForm } from './ClosedForm';
import { StaffingForm } from './StaffingForm';
import { PaperworkView } from './PaperworkView';

export function StepPanel() {
  const state = useGameStore((s) => s.state);
  const loading = useGameStore((s) => s.loading);
  if (!state) return null;

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-lg p-4 relative">
      {loading && (
        <div className="absolute inset-0 bg-gray-900/60 rounded-lg flex items-center justify-center z-10">
          <div className="w-6 h-6 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
        </div>
      )}
      {state.current_step === 'event' && <EventView />}
      {state.current_step === 'arrivals' && <ArrivalsForm />}
      {state.current_step === 'exits' && <ExitsForm />}
      {state.current_step === 'closed' && <ClosedForm />}
      {state.current_step === 'staffing' && <StaffingForm />}
      {state.current_step === 'paperwork' && <PaperworkView />}
    </div>
  );
}
