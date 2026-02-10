import axios from 'axios';
import type {
  GameState,
  NewGameResponse,
  HistoryResponse,
  RecommendationResponse,
  ReplayResponse,
  ForecastSnapshot,
  RoundCards,
  CardOverrides,
  ArrivalsAction,
  ExitsAction,
  ClosedAction,
  StaffingAction,
  StepType,
} from '../types/game';

const api = axios.create({ baseURL: '/api/game' });

export interface DeptConfig {
  patients?: number;
  core_staff?: number;
  bed_capacity?: number;
}

export interface CostConfig {
  er_diversion_financial?: number;
  er_diversion_quality?: number;
  er_waiting_financial?: number;
  er_waiting_quality?: number;
  extra_staff_financial?: number;
  extra_staff_quality?: number;
  arrivals_waiting_financial?: number;
  arrivals_waiting_quality?: number;
  requests_waiting_financial?: number;
  requests_waiting_quality?: number;
}

export interface CustomGameConfig {
  er?: DeptConfig;
  surgery?: DeptConfig;
  cc?: DeptConfig;
  sd?: DeptConfig;
  costs?: CostConfig;
}

export async function createGame(config?: CustomGameConfig): Promise<NewGameResponse> {
  const { data } = await api.post<NewGameResponse>('/new', config ?? null);
  return data;
}

export async function getState(gameId: string): Promise<GameState> {
  const { data } = await api.get<GameState>(`/${gameId}/state`);
  return data;
}

export async function stepEvent(gameId: string, seed?: number, cardOverrides?: CardOverrides): Promise<GameState> {
  const params = seed !== undefined ? { event_seed: seed } : {};
  const body = cardOverrides ?? null;
  const { data } = await api.post<GameState>(`/${gameId}/step/event`, body, { params });
  return data;
}

export async function stepArrivals(gameId: string, action: ArrivalsAction): Promise<GameState> {
  const { data } = await api.post<GameState>(`/${gameId}/step/arrivals`, action);
  return data;
}

export async function stepExits(gameId: string, action: ExitsAction): Promise<GameState> {
  const { data } = await api.post<GameState>(`/${gameId}/step/exits`, action);
  return data;
}

export async function stepClosed(gameId: string, action: ClosedAction): Promise<GameState> {
  const { data } = await api.post<GameState>(`/${gameId}/step/closed`, action);
  return data;
}

export async function stepStaffing(gameId: string, action: StaffingAction): Promise<GameState> {
  const { data } = await api.post<GameState>(`/${gameId}/step/staffing`, action);
  return data;
}

export async function stepPaperwork(gameId: string): Promise<GameState> {
  const { data } = await api.post<GameState>(`/${gameId}/step/paperwork`);
  return data;
}

export async function getHistory(gameId: string): Promise<HistoryResponse> {
  const { data } = await api.get<HistoryResponse>(`/${gameId}/history`);
  return data;
}

export async function getRoundCards(gameId: string, round: number): Promise<RoundCards> {
  const { data } = await api.get<RoundCards>(`/${gameId}/round-cards/${round}`);
  return data;
}

export async function getForecast(gameId: string): Promise<ForecastSnapshot> {
  const { data } = await api.get<ForecastSnapshot>(`/${gameId}/forecast-snapshot`);
  return data;
}

export async function getRecommendation(
  gameId: string,
  step: StepType,
): Promise<RecommendationResponse> {
  const { data } = await api.get<RecommendationResponse>(`/${gameId}/recommend/${step}`);
  return data;
}

export async function exportCSV(gameId: string): Promise<void> {
  const { data } = await api.get(`/${gameId}/export/csv`, { responseType: 'blob' });
  const url = window.URL.createObjectURL(new Blob([data], { type: 'text/csv' }));
  const link = document.createElement('a');
  link.href = url;
  link.download = `whop_game_${gameId.slice(0, 8)}.csv`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
}

export async function getReplay(gameId: string): Promise<ReplayResponse> {
  const { data } = await api.get<ReplayResponse>(`/${gameId}/replay`);
  return data;
}

// --- Chat ---

export interface ChatMessagePayload {
  role: 'user' | 'assistant';
  content: string;
}

export interface ChatRequest {
  message: string;
  history: ChatMessagePayload[];
}

export interface ChatResponse {
  reply: string;
  provider: string;
  model: string;
  llm_available: boolean;
}

export async function sendChat(gameId: string, req: ChatRequest): Promise<ChatResponse> {
  const { data } = await api.post<ChatResponse>(`/${gameId}/chat`, req);
  return data;
}
