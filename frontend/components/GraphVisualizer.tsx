'use client';

import React from 'react';
import { GitMerge, Database, ShieldCheck, Cpu, RefreshCw, FileCheck, CheckCircle2 } from 'lucide-react';

export const GraphVisualizer: React.FC = () => {
  const nodes = [
    {
      id: 'query_analyzer',
      name: 'Query Analyzer Node',
      type: 'ENTRY',
      description: 'Classifies intent, extracts keywords, and determines if vector retrieval or general reasoning is required.',
      icon: Cpu,
      color: 'border-brand-500 bg-brand-500/10 text-brand-300',
    },
    {
      id: 'retriever',
      name: 'Vector Retriever Node',
      type: 'RETRIEVAL',
      description: 'Generates embedding and performs cosine similarity search across Qdrant vector database.',
      icon: Database,
      color: 'border-indigo-500 bg-indigo-500/10 text-indigo-300',
    },
    {
      id: 'relevance_grader',
      name: 'Relevance Grader Node',
      type: 'EVALUATION',
      description: 'Evaluates each retrieved passage for exact relevance to user query, discarding noisy context.',
      icon: ShieldCheck,
      color: 'border-amber-500 bg-amber-500/10 text-amber-300',
    },
    {
      id: 'answer_generator',
      name: 'Answer Generator Node',
      type: 'GENERATION',
      description: 'Synthesizes evidence-backed answer using only verified relevance passages with precise citations.',
      icon: GitMerge,
      color: 'border-emerald-500 bg-emerald-500/10 text-emerald-300',
    },
    {
      id: 'hallucination_grader',
      name: 'Hallucination Grader Node',
      type: 'GUARDRAIL',
      description: 'Verifies whether generated response is strictly grounded in facts from retrieved documents.',
      icon: FileCheck,
      color: 'border-rose-500 bg-rose-500/10 text-rose-300',
    },
    {
      id: 'answer_grader',
      name: 'Answer Relevance Grader Node',
      type: 'FINAL_CHECK',
      description: 'Confirms answer directly addresses user query. Triggers query rewrite if insufficient.',
      icon: CheckCircle2,
      color: 'border-purple-500 bg-purple-500/10 text-purple-300',
    },
  ];

  return (
    <div className="glass-panel rounded-2xl p-6 border border-slate-800 shadow-2xl space-y-6">
      <div>
        <h2 className="text-base font-bold text-slate-100 flex items-center space-x-2">
          <GitMerge className="w-5 h-5 text-brand-400" />
          <span>LangGraph Corrective RAG (CRAG) Agent Topology</span>
        </h2>
        <p className="text-xs text-slate-400 mt-1">
          Visual architecture of state transitions, conditional self-reflection loops, and hallucination guardrails.
        </p>
      </div>

      {/* Nodes Flow Diagram */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {nodes.map((node, index) => {
          const Icon = node.icon;
          return (
            <div
              key={node.id}
              className={`p-5 rounded-2xl border ${node.color} transition-all duration-200 hover:scale-[1.02] shadow-lg flex flex-col justify-between`}
            >
              <div>
                <div className="flex items-center justify-between mb-3">
                  <div className="w-10 h-10 rounded-xl bg-slate-900/80 flex items-center justify-center border border-slate-800">
                    <Icon className="w-5 h-5" />
                  </div>
                  <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-slate-900 border border-slate-800">
                    Step 0{index + 1}
                  </span>
                </div>

                <h3 className="text-sm font-bold text-slate-100 mb-1">{node.name}</h3>
                <p className="text-xs text-slate-400 leading-relaxed">{node.description}</p>
              </div>

              <div className="mt-4 pt-3 border-t border-slate-800/60 flex items-center justify-between text-[11px]">
                <span className="font-mono text-slate-500">{node.type}</span>
                <span className="text-emerald-400 font-medium">Active Node</span>
              </div>
            </div>
          );
        })}
      </div>

      {/* Self-Correction Loop Banner */}
      <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 flex items-center space-x-3">
        <RefreshCw className="w-5 h-5 text-brand-400 flex-shrink-0 animate-spin" />
        <div className="text-xs">
          <p className="font-semibold text-slate-200">Self-Correction & Fallback Loop active</p>
          <p className="text-slate-400 mt-0.5">
            If passage relevance grading fails or hallucination is detected, the workflow rewrites the prompt, re-retrieves, or triggers web search fallback.
          </p>
        </div>
      </div>
    </div>
  );
};
