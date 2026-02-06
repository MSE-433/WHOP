import { create } from 'zustand';
import type {
  GameState,
  RecommendationResponse,
  ArrivalsAction,
  ExitsAction,
  ClosedAction,
  StaffingAction,
} from '../types/game';
import { DECISION_STEPS } from '../types/game';
import * as api from '../api/client';
import axios from 'axios';

interface GameStore {
  gameId: string | null;
  state: GameState | null;
  recommendation: RecommendationResponse | null;
  loading: boolean;
  error: string | null;

  newGame: () => Promise<void>;
  submitEvent: (seed?: number) => Promise<void>;
  submitArrivals: (action: ArrivalsAction) => Promise<void>;
  submitExits: (action: ExitsAction) => Promise<void>;
  submitClosed: (action: ClosedAction) => Promise<void>;
  submitStaffing: (action: StaffingAction) => Promise<void>;
  submitPaperwork: () => Promise<void>;
  fetchRecommendation: () => Promise<void>;
  clearError: () => void;
}

function extractError(err: unknown): string {
  if (axios.isAxiosError(err)) {
    const detail = err.response?.data?.detail;
    if (typeof detail === 'string') return detail;
    if (detail) return JSON.stringify(detail);
    return err.message;
  }
  return String(err);
}

export const useGameStore = create<GameStore>((set, get) => {
  async function afterStep(newState: GameState) {
    set({ state: newState, recommendation: null, loading: false, error: null });
    // Auto-fetch recommendation for decision steps
    if (!newState.is_finished && DECISION_STEPS.includes(newState.current_step)) {
      const { gameId } = get();
      if (!gameId) return;
      try {
        const rec = await api.getRecommendation(gameId, newState.current_step);
        set({ recommendation: rec });
      } catch {
        // Non-critical — recommendation is optional
      }
    }
  }

  return {
    gameId: null,
    state: null,
    recommendation: null,
    loading: false,
    error: null,

    clearError: () => set({ error: null }),

    newGame: async () => {
      set({ loading: true, error: null });
      try {
        const { game_id, state } = await api.createGame();
        set({ gameId: game_id, state, recommendation: null, loading: false });
      } catch (err) {
        set({ loading: false, error: extractError(err) });
      }
    },

    submitEvent: async (seed?: number) => {
      const { gameId } = get();
      if (!gameId) return;
      set({ loading: true, error: null });
      try {
        const newState = await api.stepEvent(gameId, seed);
        await afterStep(newState);
      } catch (err) {
        set({ loading: false, error: extractError(err) });
      }
    },

    submitArrivals: async (action: ArrivalsAction) => {
      const { gameId } = get();
      if (!gameId) return;
      set({ loading: true, error: null });
      try {
        const newState = await api.stepArrivals(gameId, action);
        await afterStep(newState);
      } catch (err) {
        set({ loading: false, error: extractError(err) });
      }
    },

    submitExits: async (action: ExitsAction) => {
      const { gameId } = get();
      if (!gameId) return;
      set({ loading: true, error: null });
      try {
        const newState = await api.stepExits(gameId, action);
        await afterStep(newState);
      } catch (err) {
        set({ loading: false, error: extractError(err) });
      }
    },

    submitClosed: async (action: ClosedAction) => {
      const { gameId } = get();
      if (!gameId) return;
      set({ loading: true, error: null });
      try {
        const newState = await api.stepClosed(gameId, action);
        await afterStep(newState);
      } catch (err) {
        set({ loading: false, error: extractError(err) });
      }
    },

    submitStaffing: async (action: StaffingAction) => {
      const { gameId } = get();
      if (!gameId) return;
      set({ loading: true, error: null });
      try {
        const newState = await api.stepStaffing(gameId, action);
        await afterStep(newState);
      } catch (err) {
        set({ loading: false, error: extractError(err) });
      }
    },

    submitPaperwork: async () => {
      const { gameId } = get();
      if (!gameId) return;
      set({ loading: true, error: null });
      try {
        const newState = await api.stepPaperwork(gameId);
        await afterStep(newState);
      } catch (err) {
        set({ loading: false, error: extractError(err) });
      }
    },

    fetchRecommendation: async () => {
      const { gameId, state } = get();
      if (!gameId || !state) return;
      if (!DECISION_STEPS.includes(state.current_step)) return;
      try {
        const rec = await api.getRecommendation(gameId, state.current_step);
        set({ recommendation: rec });
      } catch (err) {
        set({ error: extractError(err) });
      }
    },
  };
});
