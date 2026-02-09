import { useState } from 'react';
import { AIPanel } from './AIPanel';
import { ChatPanel } from './ChatPanel';

type Tab = 'advisor' | 'chat';

export function AITabPanel() {
  const [activeTab, setActiveTab] = useState<Tab>('advisor');

  return (
    <div className="space-y-2">
      {/* Tab bar */}
      <div className="flex gap-1 bg-gray-900 border border-gray-800 rounded-lg p-1">
        <button
          onClick={() => setActiveTab('advisor')}
          className={`flex-1 text-sm py-1.5 rounded transition-colors cursor-pointer ${
            activeTab === 'advisor'
              ? 'bg-indigo-700/50 text-indigo-200'
              : 'text-gray-400 hover:text-gray-200'
          }`}
        >
          Advisor
        </button>
        <button
          onClick={() => setActiveTab('chat')}
          className={`flex-1 text-sm py-1.5 rounded transition-colors cursor-pointer ${
            activeTab === 'chat'
              ? 'bg-indigo-700/50 text-indigo-200'
              : 'text-gray-400 hover:text-gray-200'
          }`}
        >
          Chat
        </button>
      </div>

      {/* Panels — use hidden to preserve state/scroll */}
      <div className={activeTab === 'advisor' ? '' : 'hidden'}>
        <AIPanel />
      </div>
      <div className={activeTab === 'chat' ? '' : 'hidden'}>
        <ChatPanel />
      </div>
    </div>
  );
}
