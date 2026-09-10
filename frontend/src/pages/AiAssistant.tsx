import React, { useState, useEffect, useRef } from 'react';
import { api } from '../services/api';
import { Bot, Send, User, Sparkles } from 'lucide-react';

interface ChatMessage {
  sender: 'user' | 'bot';
  text: string;
  timestamp: string;
}

export const AiAssistant: React.FC = () => {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      sender: 'bot',
      text: "Hello! I'm your EcoDriving AI Assistant. Ask me anything about your driving performance, fuel efficiency, or vehicle health!",
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    }
  ]);
  const [input, setInput] = useState('');
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const fetchSuggestions = async () => {
      try {
        const res = await api.get('/chatbot/suggestions');
        setSuggestions(res.data.suggestions || []);
      } catch (err) {
        console.error('Failed to fetch chatbot suggestions', err);
      }
    };
    fetchSuggestions();
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = async (textToSend?: string) => {
    const messageText = textToSend || input.trim();
    if (!messageText) return;

    const userMsg: ChatMessage = {
      sender: 'user',
      text: messageText,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    };

    setMessages(prev => [...prev, userMsg]);
    if (!textToSend) setInput('');
    setLoading(true);

    try {
      const res = await api.post('/chatbot/query', { message: messageText });
      const botMsg: ChatMessage = {
        sender: 'bot',
        text: res.data.response,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      };
      setMessages(prev => [...prev, botMsg]);
      if (res.data.suggestions && res.data.suggestions.length > 0) {
        setSuggestions(res.data.suggestions);
      }
    } catch (err) {
      const errorMsg: ChatMessage = {
        sender: 'bot',
        text: "Sorry, I couldn't process your request right now. Please try again.",
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      };
      setMessages(prev => [...prev, errorMsg]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto h-[calc(100vh-120px)] flex flex-col space-y-4">
      {/* Header */}
      <div className="glass-card p-4 rounded-2xl flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-brand-600 to-emerald-400 flex items-center justify-center glow-brand">
            <Bot className="w-6 h-6 text-white" />
          </div>
          <div>
            <h2 className="font-bold text-white text-lg">AI Vehicle Assistant</h2>
            <p className="text-xs text-slate-400">Powered by NLP Engine & Telemetry Analytics</p>
          </div>
        </div>
      </div>

      {/* Message Chat Feed */}
      <div className="flex-1 glass-card rounded-3xl p-6 overflow-y-auto space-y-4 border border-dark-border">
        {messages.map((msg, idx) => (
          <div
            key={idx}
            className={`flex items-start space-x-3 ${
              msg.sender === 'user' ? 'flex-row-reverse space-x-reverse' : ''
            }`}
          >
            <div className={`w-8 h-8 rounded-xl flex items-center justify-center shrink-0 ${
              msg.sender === 'user' ? 'bg-brand-600 text-white' : 'bg-slate-800 text-brand-400 border border-slate-700'
            }`}>
              {msg.sender === 'user' ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
            </div>

            <div className={`max-w-[75%] p-4 rounded-2xl text-sm leading-relaxed whitespace-pre-line ${
              msg.sender === 'user'
                ? 'bg-gradient-to-r from-brand-600 to-emerald-600 text-white rounded-tr-none shadow-md'
                : 'bg-slate-900/80 border border-dark-border text-slate-200 rounded-tl-none'
            }`}>
              {msg.text}
              <span className={`block text-[10px] mt-1.5 opacity-60 ${
                msg.sender === 'user' ? 'text-right' : 'text-left'
              }`}>
                {msg.timestamp}
              </span>
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex items-center space-x-2 text-xs text-slate-400 p-2">
            <Bot className="w-4 h-4 text-brand-400 animate-pulse" />
            <span>AI Assistant is analyzing telemetry...</span>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Quick Suggestions Pills */}
      {suggestions.length > 0 && (
        <div className="flex items-center space-x-2 overflow-x-auto pb-1">
          <Sparkles className="w-4 h-4 text-amber-400 shrink-0" />
          {suggestions.map((sug, idx) => (
            <button
              key={idx}
              onClick={() => handleSend(sug)}
              className="text-xs px-3 py-1.5 rounded-full bg-slate-800/80 hover:bg-slate-700 text-slate-300 border border-dark-border whitespace-nowrap transition-colors"
            >
              {sug}
            </button>
          ))}
        </div>
      )}

      {/* Input Bar */}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          handleSend();
        }}
        className="flex items-center space-x-2"
      >
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask your AI assistant..."
          className="flex-1 bg-slate-900/90 border border-dark-border rounded-2xl px-4 py-3.5 text-slate-200 placeholder-slate-500 focus:outline-none focus:border-brand-500 text-sm shadow-inner"
        />
        <button
          type="submit"
          disabled={loading || !input.trim()}
          className="p-3.5 rounded-2xl bg-gradient-to-r from-brand-600 to-emerald-600 hover:from-brand-500 hover:to-emerald-500 text-white font-semibold shadow-md glow-brand transition-all disabled:opacity-50"
        >
          <Send className="w-5 h-5" />
        </button>
      </form>
    </div>
  );
};
