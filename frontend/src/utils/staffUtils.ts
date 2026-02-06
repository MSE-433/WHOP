import type { StaffState, DepartmentState, DepartmentId } from '../types/game';

// Replicate backend @property fields not serialized in JSON

export function coreIdle(s: StaffState): number {
  return s.core_total - s.core_busy - s.unavailable;
}

export function extraIdle(s: StaffState): number {
  return s.extra_total - s.extra_busy;
}

export function totalIdle(s: StaffState): number {
  return coreIdle(s) + extraIdle(s);
}

export function totalBusy(s: StaffState): number {
  return s.core_busy + s.extra_busy;
}

export function totalOnDuty(s: StaffState): number {
  return s.core_total + s.extra_total - s.unavailable;
}

export function totalPatients(dept: DepartmentState): number {
  return dept.patients_in_beds + dept.patients_in_hallway;
}

export function bedsAvailable(dept: DepartmentState): number {
  if (dept.bed_capacity === null) return Infinity;
  return Math.max(0, dept.bed_capacity - dept.patients_in_beds);
}

export function hasHallway(deptId: DepartmentId): boolean {
  return deptId === 'er' || deptId === 'sd';
}

export function totalRequestsWaiting(dept: DepartmentState): number {
  return Object.values(dept.requests_waiting).reduce((a, b) => a + b, 0);
}
