import { GameHeader } from './GameHeader';
import { DepartmentGrid } from '../departments/DepartmentGrid';
import { StepPanel } from '../stepper/StepPanel';
import { AIPanel } from '../ai/AIPanel';
import { CostChart } from '../costs/CostChart';

export function MainLayout() {
  return (
    <div className="min-h-screen flex flex-col">
      <GameHeader />
      <main className="flex-1 p-4 grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Left column: departments + cost chart */}
        <div className="lg:col-span-2 flex flex-col gap-4">
          <DepartmentGrid />
          <CostChart />
        </div>
        {/* Right column: step panel + AI */}
        <div className="flex flex-col gap-4">
          <StepPanel />
          <AIPanel />
        </div>
      </main>
    </div>
  );
}
