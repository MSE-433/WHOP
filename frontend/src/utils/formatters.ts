import type { DepartmentId } from '../types/game';

export const DEPT_NAMES: Record<DepartmentId, string> = {
  er: 'Emergency',
  surgery: 'Surgery',
  cc: 'Critical Care',
  sd: 'Step Down',
};

export const DEPT_COLORS: Record<DepartmentId, string> = {
  er: 'red',
  surgery: 'blue',
  cc: 'purple',
  sd: 'green',
};

export const DEPT_ACCENTS: Record<DepartmentId, string> = {
  er: 'border-red-500',
  surgery: 'border-blue-500',
  cc: 'border-purple-500',
  sd: 'border-green-500',
};

export const DEPT_BG: Record<DepartmentId, string> = {
  er: 'bg-red-500/10',
  surgery: 'bg-blue-500/10',
  cc: 'bg-purple-500/10',
  sd: 'bg-green-500/10',
};

export const DEPT_TEXT: Record<DepartmentId, string> = {
  er: 'text-red-400',
  surgery: 'text-blue-400',
  cc: 'text-purple-400',
  sd: 'text-green-400',
};

export function formatCurrency(amount: number): string {
  return '$' + amount.toLocaleString();
}

export const STEP_LABELS: Record<string, string> = {
  event: 'Events',
  arrivals: 'Arrivals',
  exits: 'Exits',
  closed: 'Close/Divert',
  staffing: 'Staffing',
  paperwork: 'Paperwork',
};
