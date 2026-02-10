import { useState } from 'react';
import { AIPanel } from './AIPanel';
import { ChatPanel } from './ChatPanel';
import { useGameStore } from '../../store/gameStore';
import { MonteCarloPanel } from '../forecast/MonteCarloPanel';
import { ForecastTimeline } from '../forecast/ForecastTimeline';
import { CapacityChart } from '../forecast/CapacityChart';
import { AnalysisPanel } from '../forecast/AnalysisPanel';

type Tab = 'advisor' | 'forecast' | 'chat';

export function AITabPanel() {
  const [activeTab, setActiveTab] = useState<Tab>('advisor');
  const { forecast } = useGameStore();

  const tabs: { key: Tab; label: string }[] = [
    { key: 'advisor', label: 'Advisor' },
    { key: 'forecast', label: 'Forecast' },
    { key: 'chat', label: 'Chat' },
  ];

  return (
    <div className="space-y-2">
      {/* Tab bar */}
      <div className="flex gap-1 bg-gray-900 border border-gray-800 rounded-lg p-1">
        {tabs.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`flex-1 text-sm py-1.5 rounded transition-colors cursor-pointer ${
              activeTab === tab.key
                ? 'bg-indigo-700/50 text-indigo-200'
                : 'text-gray-400 hover:text-gray-200'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Panels — use hidden to preserve state/scroll */}
      <div className={activeTab === 'advisor' ? '' : 'hidden'}>
        <AIPanel />
      </div>
      <div className={activeTab === 'forecast' ? '' : 'hidden'}>
        {forecast ? (
          <div className="bg-gray-900 border border-gray-800 rounded-lg p-4 space-y-6">
            <MonteCarloPanel mc={forecast.monte_carlo} />
            {forecast.monte_carlo.expected_snapshots.length > 0 && (
              <ForecastTimeline snapshots={forecast.monte_carlo.expected_snapshots} />
            )}
            <CapacityChart capacityForecast={forecast.capacity_forecast} />
            <AnalysisPanel
              bottlenecks={forecast.bottlenecks}
              staffEfficiency={forecast.staff_efficiency}
              diversionRoi={forecast.diversion_roi}
            />
          </div>
        ) : (
          <div className="bg-gray-900 border border-gray-800 rounded-lg p-4">
            <p className="text-gray-500 text-sm">
              Forecast data loads automatically during decision steps.
            </p>
          </div>
        )}
      </div>
      <div className={activeTab === 'chat' ? '' : 'hidden'}>
        <ChatPanel />
      </div>
    </div>
  );
}
