'use client';

import React, { useState, useRef, useEffect } from 'react';
import {
  Send,
  Sparkles,
  Bot,
  User,
  BookOpen,
  HelpCircle,
  RefreshCw,
  FileText,
  CheckCircle2,
  AlertCircle,
  Clock,
  Zap,
} from 'lucide-react';
import { ChatMessage, sendChatMessage, SourceCitation } from '../lib/api';
import { ReasoningTrace } from './ReasoningTrace';
import { SourceCitationModal } from './SourceCitationModal';

interface ChatInterfaceProps {
  sessionId: string;
  selectedDocIds: string[];
}

export const ChatInterface: React.FC<ChatInterfaceProps> = ({ sessionId, selectedDocIds }) => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [activeSource, setActiveSource] = useState<SourceCitation | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const samplePrompts = [
    'What are the key findings and conclusions in the uploaded research papers?',
    'Summarize the methodology used across the documents.',
    'List all technical specifications or metrics mentioned.',
    'What are the main limitations identified in the study?',
  ];

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  const handleSend = async (textToSend?: string) => {
    const query = textToSend || input;
    if (!query.trim() || isLoading) return;

    const userMessage: ChatMessage = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: query,
      timestamp: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    try {
      const response = await sendChatMessage(query, sessionId, selectedDocIds);
      setMessages((prev) => [...prev, response]);
    } catch (err: any) {
      const errorMessage: ChatMessage = {
        id: `err-${Date.now()}`,
        role: 'assistant',
        content: `Sorry, I encountered an error executing your query: ${err.message || 'Server error'}. Please verify system health or try asking again.`,
        timestamp: new Date().toISOString(),
        confidence: 'LOW',
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="glass-panel rounded-2xl border border-slate-800 shadow-2xl flex flex-col h-[calc(100vh-140px)] min-h-[500px]">
      {/* Active Context Header */}
      <div className="px-6 py-3 border-b border-slate-800 bg-slate-900/60 flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <BookOpen className="w-4 h-4 text-brand-400" />
          <span className="text-xs font-semibold text-slate-300">Active Research Scope:</span>
          {selectedDocIds.length > 0 ? (
            <span className="px-2.5 py-0.5 rounded-full bg-brand-500/20 text-brand-300 border border-brand-500/30 text-xs font-medium">
              {selectedDocIds.length} Targeted Document(s)
            </span>
          ) : (
            <span className="px-2.5 py-0.5 rounded-full bg-slate-800 text-slate-400 text-xs font-medium">
              Entire Knowledge Base
            </span>
          )}
        </div>

        <button
          onClick={() => setMessages([])}
          className="text-xs text-slate-400 hover:text-slate-200 flex items-center space-x-1"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          <span>Clear Chat</span>
        </button>
      </div>

      {/* Messages Scroll Area */}
      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center max-w-xl mx-auto space-y-6">
            <div className="w-16 h-16 rounded-2xl bg-gradient-to-tr from-brand-600 to-indigo-600 p-0.5 shadow-xl shadow-brand-500/20">
              <div className="w-full h-full bg-slate-950 rounded-[14px] flex items-center justify-center">
                <Sparkles className="w-8 h-8 text-brand-400" />
              </div>
            </div>

            <div>
              <h3 className="text-lg font-bold text-slate-100">Welcome to ResearchFlow AI</h3>
              <p className="text-xs text-slate-400 mt-1 leading-relaxed">
                Powered by Corrective RAG (CRAG) & LangGraph Agentic Workflows. Ask anything about your uploaded documents and get verifiable, evidence-backed answers.
              </p>
            </div>

            {/* Suggested Prompts */}
            <div className="w-full space-y-2">
              <p className="text-xs font-semibold text-slate-400 text-left">Suggested Research Queries:</p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-left">
                {samplePrompts.map((prompt, idx) => (
                  <button
                    key={idx}
                    onClick={() => handleSend(prompt)}
                    className="glass-card p-3 rounded-xl text-xs text-slate-300 hover:text-white transition group border border-slate-800 text-left"
                  >
                    <p className="group-hover:text-brand-300">{prompt}</p>
                  </button>
                ))}
              </div>
            </div>
          </div>
        ) : (
          messages.map((msg) => (
            <div
              key={msg.id}
              className={`flex items-start space-x-3.5 ${
                msg.role === 'user' ? 'justify-end' : 'justify-start'
              }`}
            >
              {msg.role === 'assistant' && (
                <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-brand-600 to-indigo-600 p-0.5 flex-shrink-0 shadow-lg shadow-brand-500/10">
                  <div className="w-full h-full bg-slate-950 rounded-[10px] flex items-center justify-center">
                    <Bot className="w-4 h-4 text-brand-400" />
                  </div>
                </div>
              )}

              <div
                className={`max-w-[85%] rounded-2xl p-4 transition-all ${
                  msg.role === 'user'
                    ? 'bg-gradient-to-r from-brand-600 to-indigo-600 text-white rounded-tr-none shadow-lg shadow-brand-600/20'
                    : 'glass-panel border border-slate-800 text-slate-200 rounded-tl-none shadow-xl'
                }`}
              >
                {/* Assistant Badges Bar */}
                {msg.role === 'assistant' && (
                  <div className="flex items-center justify-between mb-3 text-xs border-b border-slate-800/80 pb-2">
                    <div className="flex items-center space-x-2">
                      <span className="font-bold text-slate-200">Research Assistant</span>
                      {msg.confidence && (
                        <span
                          className={`text-[10px] px-2 py-0.5 rounded-full font-semibold ${
                            msg.confidence === 'HIGH'
                              ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                              : msg.confidence === 'MEDIUM'
                              ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                              : 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                          }`}
                        >
                          {msg.confidence} CONFIDENCE
                        </span>
                      )}
                    </div>
                  </div>
                )}

                {/* Message Body */}
                <div className="text-sm leading-relaxed whitespace-pre-wrap font-sans">
                  {msg.content}
                </div>

                {/* Source Citations */}
                {msg.sources && msg.sources.length > 0 && (
                  <div className="mt-4 pt-3 border-t border-slate-800/80">
                    <p className="text-xs font-semibold text-slate-400 mb-2 flex items-center space-x-1">
                      <FileText className="w-3.5 h-3.5 text-brand-400" />
                      <span>Retrieved Evidence & Citations ({msg.sources.length}):</span>
                    </p>
                    <div className="flex flex-wrap gap-2">
                      {msg.sources.map((src, idx) => (
                        <button
                          key={idx}
                          onClick={() => setActiveSource(src)}
                          className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-slate-900/90 border border-slate-700/80 hover:border-brand-500/50 hover:bg-slate-800 text-xs text-slate-300 transition"
                        >
                          <FileText className="w-3.5 h-3.5 text-brand-400" />
                          <span className="truncate max-w-[150px]">{src.document_name}</span>
                          <span className="text-[10px] font-mono text-emerald-400 bg-emerald-500/10 px-1 rounded">
                            {(src.similarity_score * 100).toFixed(0)}%
                          </span>
                        </button>
                      ))}
                    </div>
                  </div>
                )}

                {/* Agent Reasoning Accordion */}
                {msg.reasoning && (
                  <ReasoningTrace
                    reasoning={msg.reasoning}
                    queryIntent={msg.query_intent}
                    isHallucinationFree={msg.is_hallucination_free}
                    isAnswerRelevant={msg.is_answer_relevant}
                    executionTimeMs={msg.execution_time_ms}
                  />
                )}
              </div>

              {msg.role === 'user' && (
                <div className="w-9 h-9 rounded-xl bg-slate-800 flex items-center justify-center text-slate-300 flex-shrink-0">
                  <User className="w-4 h-4" />
                </div>
              )}
            </div>
          ))
        )}

        {/* Loading Indicator */}
        {isLoading && (
          <div className="flex items-start space-x-3.5">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-brand-600 to-indigo-600 p-0.5 flex-shrink-0">
              <div className="w-full h-full bg-slate-950 rounded-[10px] flex items-center justify-center">
                <Bot className="w-4 h-4 text-brand-400 animate-spin" />
              </div>
            </div>
            <div className="glass-panel p-4 rounded-2xl border border-slate-800 text-slate-400 text-xs flex items-center space-x-3">
              <Clock className="w-4 h-4 animate-spin text-brand-400" />
              <span>Analyzing query, retrieving vectors, and evaluating evidence with CRAG workflow...</span>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Form */}
      <div className="p-4 border-t border-slate-800 bg-slate-900/90">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSend();
          }}
          className="flex items-center space-x-3"
        >
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask a question about your uploaded research documents..."
            disabled={isLoading}
            className="flex-1 px-4 py-3 bg-slate-950/80 border border-slate-700/80 rounded-xl text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-brand-500 transition"
          />

          <button
            type="submit"
            disabled={isLoading || !input.trim()}
            className="px-5 py-3 bg-gradient-to-r from-brand-600 to-indigo-600 hover:from-brand-500 hover:to-indigo-500 text-white rounded-xl font-semibold transition-all duration-200 shadow-lg shadow-brand-600/30 disabled:opacity-50 flex items-center space-x-2"
          >
            <Send className="w-4 h-4" />
            <span className="hidden sm:inline text-xs">Research</span>
          </button>
        </form>
      </div>

      {/* Citation Detail Modal */}
      <SourceCitationModal source={activeSource} onClose={() => setActiveSource(null)} />
    </div>
  );
};
