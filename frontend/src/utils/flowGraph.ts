import type { DepartmentId } from '../types/game';

export const FLOW_GRAPH: Record<DepartmentId, DepartmentId[]> = {
  er: ['surgery', 'cc', 'sd'],
  surgery: ['cc', 'sd'],
  cc: ['surgery', 'sd'],
  sd: ['surgery', 'cc'],
};

export function canTransfer(from: DepartmentId, to: DepartmentId): boolean {
  return (FLOW_GRAPH[from] ?? []).includes(to);
}
