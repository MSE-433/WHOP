import { useGameStore } from './store/gameStore';
import { MainLayout } from './components/layout/MainLayout';
import { GameOverOverlay } from './components/shared/GameOverOverlay';
import { StartScreen } from './components/shared/StartScreen';

function App() {
  const { state, error, clearError } = useGameStore();

  // No active game — show start screen
  if (!state) {
    return <StartScreen />;
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
