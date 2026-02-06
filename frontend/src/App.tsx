import { useGameStore } from './store/gameStore';
import { MainLayout } from './components/layout/MainLayout';
import { GameOverOverlay } from './components/shared/GameOverOverlay';

function App() {
  const { state, loading, error, newGame, clearError } = useGameStore();

  // No active game — show start screen
  if (!state) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen gap-6">
        <h1 className="text-4xl font-bold tracking-tight">
          WHOP
        </h1>
        <p className="text-gray-400 text-lg">
          Workflow-guided Hospital Outcomes Platform
        </p>
        <button
          onClick={newGame}
          disabled={loading}
          className="px-8 py-3 bg-blue-600 hover:bg-blue-500 disabled:bg-gray-700 rounded-lg text-lg font-medium transition-colors cursor-pointer"
        >
          {loading ? 'Starting...' : 'New Game'}
        </button>
        {error && (
          <p className="text-red-400 text-sm">{error}</p>
        )}
      </div>
    );
  }

  return (
    <>
      <MainLayout />
      {state.is_finished && <GameOverOverlay />}
      {/* Error toast */}
      {error && (
        <div className="fixed top-4 right-4 bg-red-900/90 border border-red-700 rounded-lg px-4 py-3 max-w-md z-50">
          <div className="flex justify-between items-start gap-2">
            <p className="text-red-200 text-sm">{error}</p>
            <button onClick={clearError} className="text-red-400 hover:text-red-200 cursor-pointer">
              &times;
            </button>
          </div>
        </div>
      )}
    </>
  );
}

export default App;
