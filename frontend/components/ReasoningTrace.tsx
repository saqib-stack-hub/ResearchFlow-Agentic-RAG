'use client';

import React, { useState } from 'react';
import { ChevronDown, ChevronUp, Cpu, CheckCircle, AlertTriangle, Info, Zap } from 'lucide-react';
import { ReasoningStep } from '../lib/api';

interface ReasoningTraceProps {
  reasoning: ReasoningStep[];
  queryIntent?: string;
  isHallucinationFree?: boolean;
  isAnswerRelevant?: boolean;
  executionTimeMs?: number;
}

export const ReasoningTrace: React.FC<ReasoningTraceProps> = ({
  reasoning = [],
  queryIntent,
  isHallucinationFree,
  isAnswerRelevant,
  executionTimeMs,
}) => {
  const [isOpen, setIsOpen] = useState(false);

  if (!reasoning || reasoning.length === 0) return null;

  const getStatusIcon = (status: ReasoningStep['status']) => {
    switch (status) {
      case 'SUCCESS':
        return <CheckCircle className="w-3.5 h-3.5 text-emerald-400" />;
      case 'WARNING':
        return <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />;
      default:
        return <Info className="w-3.5 h-3.5 text-brand-400" />;
    }
  };

  return (
    <div className="mt-3 border border-slate-800 rounded-xl overflow-hidden bg-slate-900/60 transition-all">
      {/* Accordion Toggle Header */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full px-4 py-2.5 flex items-center justify-between hover:bg-slate-800/40 text-left transition"
      >
        <div className="flex items-center space-x-2">
          <Cpu className="w-4 h-4 text-brand-400" />
          <span className="text-xs font-semibold text-slate-300">
            Agent Reasoning & CRAG Evaluation
          </span>
          <span className="text-[10px] px-2 py-0.5 rounded bg-brand-500/10 text-brand-300 border border-brand-500/20">
            {reasoning.length} Node Steps
          </span>
        </div>

        <div className="flex items-center space-x-3 text-xs text-slate-400">
          {executionTimeMs && (
            <span className="flex items-center space-x-1 text-[11px] text-slate-400">
              <Zap className="w-3 h-3 text-amber-400" />
              <span>{executionTimeMs} ms</span>
            </span>
          )}

          {isHallucinationFree !== undefined && (
            <span
              className={`text-[10px] px-2 py-0.5 rounded font-medium ${
                isHallucinationFree
                  ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                  : 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
              }`}
            >
              {isHallucinationFree ? 'Grounded' : 'Unverified'}
            </span>
          )}

          {isOpen ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
        </div>
      </button>

      {/* Accordion Content */}
      {isOpen && (
        <div className="p-4 border-t border-slate-800/80 space-y-3 bg-slate-950/50 text-xs">
          {/* Query Intent Badge */}
          {queryIntent && (
            <div className="p-2 rounded-lg bg-slate-900 border border-slate-800 flex items-center space-x-2">
              <span className="text-slate-400 font-medium">Intent Classified:</span>
              <span className="text-slate-200 font-mono font-semibold text-[11px] uppercase bg-slate-800 px-2 py-0.5 rounded">
                {queryIntent}
              </span>
            </div>
          )}

          {/* Node Execution Steps Timeline */}
          <div className="relative pl-4 space-y-2.5 border-l-2 border-slate-800">
            {reasoning.map((step, idx) => (
              <div key={idx} className="relative group">
                <div className="absolute -left-[21px] top-1 bg-slate-950 p-0.5 rounded-full border border-slate-800">
                  {getStatusIcon(step.status)}
                </div>

                <div className="bg-slate-900/80 p-2.5 rounded-lg border border-slate-800/80 hover:border-slate-700">
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-slate-200 font-mono text-[11px]">
                      {step.step}
                    </span>
                    {step.score !== undefined && (
                      <span className="text-[10px] bg-slate-800 text-brand-300 font-mono px-1.5 py-0.5 rounded">
                        Score: {(step.score * 100).toFixed(0)}%
                      </span>
                    )}
                  </div>
                  <p className="text-slate-400 text-[11px] mt-1 leading-relaxed">{step.details}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
