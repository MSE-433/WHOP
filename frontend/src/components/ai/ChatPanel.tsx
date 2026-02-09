import { useState, useRef, useEffect } from 'react';
import Markdown from 'react-markdown';
import { useGameStore } from '../../store/gameStore';

export function ChatPanel() {
  const { chatMessages, chatLoading, sendChatMessage, clearChat } = useGameStore();
  const [input, setInput] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatMessages, chatLoading]);

  const handleSend = () => {
    const trimmed = input.trim();
    if (!trimmed || chatLoading) return;
    setInput('');
    sendChatMessage(trimmed);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-lg flex flex-col h-80">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-gray-800">
        <h3 className="font-semibold text-sm">Chat</h3>
        {chatMessages.length > 0 && (
          <button
            onClick={clearChat}
            className="text-xs px-2 py-0.5 text-gray-500 hover:text-gray-300 transition-colors cursor-pointer"
          >
            Clear
          </button>
        )}
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-2 space-y-3">
        {chatMessages.length === 0 && !chatLoading && (
          <p className="text-gray-500 text-sm text-center mt-8">
            Ask about strategy, game rules, or what to do next.
          </p>
        )}
        {chatMessages.map((msg) => (
          <div
            key={msg.id}
            className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-[85%] rounded-lg px-3 py-2 text-sm ${
                msg.role === 'user'
                  ? 'bg-indigo-700/60 text-indigo-100 whitespace-pre-wrap'
                  : 'bg-gray-800 text-gray-300 prose prose-sm prose-invert prose-p:my-1 prose-ul:my-1 prose-ol:my-1 prose-li:my-0.5 prose-headings:my-2 prose-headings:text-gray-200 max-w-none'
              }`}
            >
              {msg.role === 'user' ? msg.content : <Markdown>{msg.content}</Markdown>}
            </div>
          </div>
        ))}
        {chatLoading && (
          <div className="flex justify-start">
            <div className="bg-gray-800 rounded-lg px-3 py-2 text-sm text-gray-400">
              <span className="inline-flex gap-1">
                <span className="animate-bounce" style={{ animationDelay: '0ms' }}>.</span>
                <span className="animate-bounce" style={{ animationDelay: '150ms' }}>.</span>
                <span className="animate-bounce" style={{ animationDelay: '300ms' }}>.</span>
              </span>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="px-3 py-2 border-t border-gray-800 flex gap-2">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask the AI advisor..."
          className="flex-1 bg-gray-800 border border-gray-700 rounded px-3 py-1.5 text-sm text-gray-200 placeholder-gray-500 focus:outline-none focus:border-indigo-600"
          disabled={chatLoading}
        />
        <button
          onClick={handleSend}
          disabled={!input.trim() || chatLoading}
          className="px-3 py-1.5 bg-indigo-700 hover:bg-indigo-600 disabled:bg-gray-700 disabled:text-gray-500 text-sm text-white rounded transition-colors cursor-pointer"
        >
          Send
        </button>
      </div>
    </div>
  );
}
