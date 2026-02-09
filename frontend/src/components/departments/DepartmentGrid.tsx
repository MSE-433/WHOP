import { useGameStore } from '../../store/gameStore';
import { DepartmentCard } from './DepartmentCard';
import { ALL_DEPARTMENTS } from '../../types/game';

export function DepartmentGrid() {
  const state = useGameStore((s) => s.state);
  if (!state) return null;

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 items-start">
      {ALL_DEPARTMENTS.map((id) => (
        <DepartmentCard key={id} dept={state.departments[id]} />
      ))}
    </div>
  );
}
