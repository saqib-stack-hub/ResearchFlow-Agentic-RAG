'use client';

import React from 'react';
import { X, FileText, ExternalLink, Bookmark, Award } from 'lucide-react';
import { SourceCitation } from '../lib/api';

interface SourceCitationModalProps {
  source: SourceCitation | null;
  onClose: () => void;
}

export const SourceCitationModal: React.FC<SourceCitationModalProps> = ({ source, onClose }) => {
  if (!source) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-fade-in">
      <div className="glass-panel w-full max-w-2xl rounded-2xl border border-slate-700 shadow-2xl overflow-hidden flex flex-col max-h-[85vh]">
        {/* Header */}
        <div className="p-5 border-b border-slate-800 flex items-center justify-between bg-slate-900/90">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-xl bg-brand-500/10 text-brand-400 flex items-center justify-center border border-brand-500/20">
              <FileText className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-slate-100 flex items-center space-x-2">
                <span>{source.document_name}</span>
              </h3>
              <p className="text-xs text-slate-400">Retrieved Document Context Chunk</p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Metadata Bar */}
        <div className="px-5 py-3 bg-slate-900/50 border-b border-slate-800 flex items-center justify-between text-xs">
          <div className="flex items-center space-x-4">
            <span className="flex items-center space-x-1.5 text-slate-300">
              <Award className="w-4 h-4 text-emerald-400" />
              <span>Similarity Score:</span>
              <strong className="text-emerald-400 font-mono">
                {(source.similarity_score * 100).toFixed(1)}%
              </strong>
            </span>

            {source.page_number && (
              <span className="flex items-center space-x-1 text-slate-400">
                <Bookmark className="w-3.5 h-3.5" />
                <span>Page {source.page_number}</span>
              </span>
            )}
          </div>

          <span className="text-[11px] font-mono text-slate-500">ID: {source.id.slice(0, 8)}...</span>
        </div>

        {/* Passage Content */}
        <div className="p-6 overflow-y-auto space-y-4 font-sans leading-relaxed text-sm text-slate-200 bg-slate-950/60">
          <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 font-mono text-xs text-slate-300 whitespace-pre-wrap">
            {source.content}
          </div>
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-slate-800 bg-slate-900/90 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold rounded-xl transition"
          >
            Close View
          </button>
        </div>
      </div>
    </div>
  );
};
