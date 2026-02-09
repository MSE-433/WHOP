import { GameHeader } from './GameHeader';
import { DepartmentGrid } from '../departments/DepartmentGrid';
import { StepPanel } from '../stepper/StepPanel';
import { AITabPanel } from '../ai/AITabPanel';
import { CostChart } from '../costs/CostChart';

export function MainLayout() {
  return (
    <div className="h-screen flex flex-col overflow-hidden">
      <GameHeader />
      <main className="flex-1 min-h-0 p-4 grid grid-cols-1 lg:grid-cols-5 gap-4">
        {/* Left column: departments + cost chart */}
        <div className="lg:col-span-3 min-h-0 overflow-y-auto flex flex-col gap-4">
          <DepartmentGrid />
          <CostChart />
        </div>
        {/* Right column: step panel + AI */}
        <div className="lg:col-span-2 min-h-0 overflow-y-auto flex flex-col gap-4 order-first lg:order-none">
          <StepPanel />
          <AITabPanel />
        </div>
      </main>
    </div>
  );
}
