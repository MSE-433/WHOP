// Department & Step enums (match backend string values)
export type DepartmentId = 'er' | 'surgery' | 'cc' | 'sd';
export type StepType = 'event' | 'arrivals' | 'exits' | 'closed' | 'staffing' | 'paperwork';

export const STEP_ORDER: StepType[] = ['event', 'arrivals', 'exits', 'closed', 'staffing', 'paperwork'];
export const DECISION_STEPS: StepType[] = ['arrivals', 'exits', 'closed', 'staffing'];
export const ALL_DEPARTMENTS: DepartmentId[] = ['er', 'surgery', 'cc', 'sd'];

// --- Staff ---
export interface StaffState {
  core_total: number;
  core_busy: number;
  extra_total: number;
  extra_busy: number;
  extra_incoming: number;
  unavailable: number;
}

// --- Events ---
export interface EventEffect {
  staff_unavailable: number;
  staff_unavailable_permanent: boolean;
  no_exits: boolean;
  extra_staff_needed: number;
  bed_reduction: number;
  additional_arrivals: number;
  shift_change: boolean;
  no_new_arrivals: boolean;
}

export interface ActiveEvent {
  event_id: string;
  description: string;
  effect: EventEffect;
  rounds_remaining: number | null;
}

// --- Transfers ---
export interface TransferRequest {
  from_dept: DepartmentId;
  to_dept: DepartmentId;
  count: number;
  rounds_remaining: number;
}

// --- Department ---
export interface DepartmentState {
  id: DepartmentId;
  staff: StaffState;
  patients_in_beds: number;
  patients_in_hallway: number;
  bed_capacity: number | null;
  arrivals_waiting: number;
  requests_waiting: Record<DepartmentId, number>;
  outgoing_transfers: TransferRequest[];
  is_closed: boolean;
  is_diverting: boolean;
  active_events: ActiveEvent[];
}

// --- Costs ---
export interface RoundCostEntry {
  round_number: number;
  financial: number;
  quality: number;
  details: Record<string, number>;
}

// --- Game State ---
export interface GameState {
  game_id: string;
  round_number: number;
  current_step: StepType;
  departments: Record<DepartmentId, DepartmentState>;
  total_financial_cost: number;
  total_quality_cost: number;
  round_costs: RoundCostEntry[];
  is_finished: boolean;
  er_diverted_last_round: boolean;
  ambulances_diverted_this_round: number;
}

// --- Actions ---
export interface AdmitDecision {
  department: DepartmentId;
  admit_count: number;
}

export interface AcceptTransferDecision {
  department: DepartmentId;
  from_dept: DepartmentId;
  accept_count: number;
}

export interface ArrivalsAction {
  admissions: AdmitDecision[];
  transfer_accepts: AcceptTransferDecision[];
}

export interface ExitRouting {
  from_dept: DepartmentId;
  walkout_count: number;
  transfers: Record<DepartmentId, number>;
}

export interface ExitsAction {
  routings: ExitRouting[];
}

export interface ClosedAction {
  close_departments: DepartmentId[];
  open_departments: DepartmentId[];
  divert_er: boolean;
}

export interface StaffTransfer {
  from_dept: DepartmentId;
  to_dept: DepartmentId;
  count: number;
}

export interface StaffingAction {
  extra_staff: Record<DepartmentId, number>;
  return_extra: Record<DepartmentId, number>;
  transfers: StaffTransfer[];
}

// --- API Responses ---
export interface NewGameResponse {
  game_id: string;
  state: GameState;
}

export interface HistoryResponse {
  game_id: string;
  round_costs: RoundCostEntry[];
  total_financial_cost: number;
  total_quality_cost: number;
}

// --- Recommendations ---
export interface ScoredCandidate {
  description: string;
  action: Record<string, unknown>;
  expected_financial: number;
  expected_quality: number;
  expected_total: number;
  delta_vs_baseline: number;
  p10_total: number;
  p90_total: number;
  reasoning: string;
}

export interface RecommendationResponse {
  step: string;
  recommended_action: Record<string, unknown>;
  reasoning: string;
  alternatives: Record<string, unknown>[];
  cost_impact: Record<string, unknown>;
  risk_flags: string[];
  confidence: number;
  source: 'llm' | 'optimizer_fallback';
  llm_available: boolean;
  optimizer_candidates: ScoredCandidate[];
  baseline_cost: number;
  horizon_used: number;
}
