'use client';

import React, { useEffect, useState } from 'react';
import { Activity, Database, Server, Cpu, RefreshCw, Clock, CheckCircle2, AlertTriangle } from 'lucide-react';
import { fetchSystemHealth, SystemHealth } from '../lib/api';

export const SystemHealthDashboard: React.FC = () => {
  const [health, setHealth] = useState<SystemHealth | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadHealth = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await fetchSystemHealth();
      setHealth(data);
    } catch (err: any) {
      setError('Could not connect to FastAPI Backend. Ensure FastAPI is running on port 8000.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadHealth();
    const interval = setInterval(loadHealth, 15000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="glass-panel rounded-2xl p-6 border border-slate-800 shadow-2xl space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-base font-bold text-slate-100 flex items-center space-x-2">
            <Activity className="w-5 h-5 text-emerald-400" />
            <span>Infrastructure Health & Metrics</span>
          </h2>
          <p className="text-xs text-slate-400 mt-0.5">Real-time status monitoring for system services</p>
        </div>

        <button
          onClick={loadHealth}
          disabled={isLoading}
          className="flex items-center space-x-2 px-3 py-1.5 bg-slate-900 border border-slate-700 rounded-xl text-xs text-slate-300 hover:text-white transition disabled:opacity-50"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
          <span>Refresh</span>
        </button>
      </div>

      {error ? (
        <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs flex items-center space-x-3">
          <AlertTriangle className="w-5 h-5 flex-shrink-0" />
          <div>
            <p className="font-semibold">Backend Unreachable</p>
            <p className="text-slate-400 mt-0.5">{error}</p>
          </div>
        </div>
      ) : (
        health && (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {/* PostgreSQL */}
            <div className="glass-card p-4 rounded-xl border border-slate-800 space-y-2">
              <div className="flex items-center justify-between">
                <div className="w-8 h-8 rounded-lg bg-indigo-500/10 text-indigo-400 flex items-center justify-center">
                  <Database className="w-4 h-4" />
                </div>
                <span className="text-[10px] px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 font-semibold border border-emerald-500/20">
                  {health.services.postgres?.status}
                </span>
              </div>
              <div>
                <p className="text-xs font-semibold text-slate-200">PostgreSQL DB</p>
                <p className="text-xs text-slate-400 mt-1">Metadata & Documents</p>
              </div>
              <div className="pt-2 border-t border-slate-800 text-[11px] flex justify-between text-slate-400 font-mono">
                <span>Latency:</span>
                <span className="text-emerald-400">{health.services.postgres?.latency_ms} ms</span>
              </div>
            </div>

            {/* Qdrant */}
            <div className="glass-card p-4 rounded-xl border border-slate-800 space-y-2">
              <div className="flex items-center justify-between">
                <div className="w-8 h-8 rounded-lg bg-brand-500/10 text-brand-400 flex items-center justify-center">
                  <Server className="w-4 h-4" />
                </div>
                <span className="text-[10px] px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 font-semibold border border-emerald-500/20">
                  {health.services.qdrant?.status}
                </span>
              </div>
              <div>
                <p className="text-xs font-semibold text-slate-200">Qdrant Vector DB</p>
                <p className="text-xs text-slate-400 mt-1">Embedding Search</p>
              </div>
              <div className="pt-2 border-t border-slate-800 text-[11px] flex justify-between text-slate-400 font-mono">
                <span>Latency:</span>
                <span className="text-emerald-400">{health.services.qdrant?.latency_ms} ms</span>
              </div>
            </div>

            {/* Redis */}
            <div className="glass-card p-4 rounded-xl border border-slate-800 space-y-2">
              <div className="flex items-center justify-between">
                <div className="w-8 h-8 rounded-lg bg-rose-500/10 text-rose-400 flex items-center justify-center">
                  <Clock className="w-4 h-4" />
                </div>
                <span className="text-[10px] px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 font-semibold border border-emerald-500/20">
                  {health.services.redis?.status}
                </span>
              </div>
              <div>
                <p className="text-xs font-semibold text-slate-200">Redis Cache & Tasks</p>
                <p className="text-xs text-slate-400 mt-1">State & Session Store</p>
              </div>
              <div className="pt-2 border-t border-slate-800 text-[11px] flex justify-between text-slate-400 font-mono">
                <span>Latency:</span>
                <span className="text-emerald-400">{health.services.redis?.latency_ms} ms</span>
              </div>
            </div>

            {/* LLM Engine */}
            <div className="glass-card p-4 rounded-xl border border-slate-800 space-y-2">
              <div className="flex items-center justify-between">
                <div className="w-8 h-8 rounded-lg bg-amber-500/10 text-amber-400 flex items-center justify-center">
                  <Cpu className="w-4 h-4" />
                </div>
                <span className="text-[10px] px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 font-semibold border border-emerald-500/20">
                  {health.services.llm?.status}
                </span>
              </div>
              <div>
                <p className="text-xs font-semibold text-slate-200">Gemini LLM Engine</p>
                <p className="text-xs text-slate-400 mt-1">LangChain Orchestration</p>
              </div>
              <div className="pt-2 border-t border-slate-800 text-[11px] flex justify-between text-slate-400 font-mono">
                <span>Latency:</span>
                <span className="text-emerald-400">{health.services.llm?.latency_ms} ms</span>
              </div>
            </div>
          </div>
        )
      )}
    </div>
  );
};
