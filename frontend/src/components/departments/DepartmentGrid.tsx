import { useGameStore } from '../../store/gameStore';
import { DepartmentCard } from './DepartmentCard';
import { ALL_DEPARTMENTS } from '../../types/game';

export function DepartmentGrid() {
  const state = useGameStore((s) => s.state);
  const forecast = useGameStore((s) => s.forecast);
  if (!state) return null;

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 items-start">
      {ALL_DEPARTMENTS.map((id) => {
        const utilization = forecast?.utilization?.[id];
        // Find the highest-severity bottleneck for this department
        const deptBottlenecks = forecast?.bottlenecks?.filter((b) => b.department === id) ?? [];
        const bottleneck = deptBottlenecks.find((b) => b.severity === 'high')
          ?? deptBottlenecks.find((b) => b.severity === 'medium')
          ?? deptBottlenecks[0];

        return (
          <DepartmentCard
            key={id}
            dept={state.departments[id]}
            utilization={utilization}
            bottleneck={bottleneck}
          />
        );
      })}
    </div>
  );
}
