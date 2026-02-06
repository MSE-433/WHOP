import axios from 'axios';
import type {
  GameState,
  NewGameResponse,
  HistoryResponse,
  RecommendationResponse,
  ReplayResponse,
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

export interface CustomGameConfig {
  er?: DeptConfig;
  surgery?: DeptConfig;
  cc?: DeptConfig;
  sd?: DeptConfig;
}

export async function createGame(config?: CustomGameConfig): Promise<NewGameResponse> {
  const { data } = await api.post<NewGameResponse>('/new', config ?? null);
  return data;
}

export async function getState(gameId: string): Promise<GameState> {
  const { data } = await api.get<GameState>(`/${gameId}/state`);
  return data;
}

export async function stepEvent(gameId: string, seed?: number): Promise<GameState> {
  const params = seed !== undefined ? { event_seed: seed } : {};
  const { data } = await api.post<GameState>(`/${gameId}/step/event`, null, { params });
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
