'use client';

import React, { useState } from 'react';
import { FileText, Trash2, CheckCircle2, Clock, AlertTriangle, Layers, Search, RefreshCw } from 'lucide-react';
import { Document, deleteDocument } from '../lib/api';

interface DocumentListProps {
  documents: Document[];
  onRefresh: () => void;
  selectedDocIds: string[];
  setSelectedDocIds: (ids: string[]) => void;
}

export const DocumentList: React.FC<DocumentListProps> = ({
  documents,
  onRefresh,
  selectedDocIds,
  setSelectedDocIds,
}) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const filteredDocs = documents.filter((doc) =>
    doc.original_name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const handleDelete = async (id: string) => {
    if (!confirm('Are you sure you want to delete this document and its vector embeddings?')) return;
    setDeletingId(id);
    try {
      await deleteDocument(id);
      onRefresh();
      setSelectedDocIds(selectedDocIds.filter((docId) => docId !== id));
    } catch (err) {
      alert('Failed to delete document');
    } finally {
      setDeletingId(null);
    }
  };

  const toggleSelect = (id: string) => {
    if (selectedDocIds.includes(id)) {
      setSelectedDocIds(selectedDocIds.filter((docId) => docId !== id));
    } else {
      setSelectedDocIds([...selectedDocIds, id]);
    }
  };

  const toggleSelectAll = () => {
    if (selectedDocIds.length === documents.length) {
      setSelectedDocIds([]);
    } else {
      setSelectedDocIds(documents.map((d) => d.id));
    }
  };

  const getStatusBadge = (status: Document['status']) => {
    switch (status) {
      case 'COMPLETED':
        return (
          <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-[11px] font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            <CheckCircle2 className="w-3 h-3" />
            <span>Indexed</span>
          </span>
        );
      case 'PROCESSING':
        return (
          <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-[11px] font-medium bg-amber-500/10 text-amber-400 border border-amber-500/20">
            <Clock className="w-3 h-3 animate-spin" />
            <span>Processing</span>
          </span>
        );
      case 'FAILED':
        return (
          <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-[11px] font-medium bg-rose-500/10 text-rose-400 border border-rose-500/20">
            <AlertTriangle className="w-3 h-3" />
            <span>Failed</span>
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-[11px] font-medium bg-slate-800 text-slate-400">
            <Clock className="w-3 h-3" />
            <span>Pending</span>
          </span>
        );
    }
  };

  return (
    <div className="glass-panel rounded-2xl p-6 border border-slate-800 shadow-xl space-y-4">
      {/* Header & Controls */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h2 className="text-base font-bold text-slate-100 flex items-center space-x-2">
            <span>Knowledge Base Documents</span>
            <span className="text-xs bg-slate-800 px-2 py-0.5 rounded-md text-slate-400">
              {documents.length} Total
            </span>
          </h2>
          <p className="text-xs text-slate-400">Select specific documents to target chat research</p>
        </div>

        <div className="flex items-center space-x-2">
          <div className="relative">
            <Search className="w-3.5 h-3.5 absolute left-3 top-2.5 text-slate-400" />
            <input
              type="text"
              placeholder="Search documents..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-8 pr-3 py-1.5 bg-slate-900/80 border border-slate-700/80 rounded-xl text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-brand-500 w-48"
            />
          </div>

          <button
            onClick={onRefresh}
            className="p-1.5 bg-slate-900 border border-slate-700/80 rounded-xl text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition"
            title="Refresh List"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Select All Bar */}
      {documents.length > 0 && (
        <div className="flex items-center justify-between text-xs bg-slate-900/40 p-2.5 rounded-xl border border-slate-800">
          <label className="flex items-center space-x-2 cursor-pointer text-slate-300">
            <input
              type="checkbox"
              checked={selectedDocIds.length === documents.length && documents.length > 0}
              onChange={toggleSelectAll}
              className="rounded bg-slate-800 border-slate-700 text-brand-500 focus:ring-0"
            />
            <span>Select All for Query Context ({selectedDocIds.length} selected)</span>
          </label>

          {selectedDocIds.length > 0 && (
            <button
              onClick={() => setSelectedDocIds([])}
              className="text-[11px] text-brand-400 hover:underline"
            >
              Clear selection
            </button>
          )}
        </div>
      )}

      {/* Document List */}
      {filteredDocs.length === 0 ? (
        <div className="text-center py-12 border border-dashed border-slate-800 rounded-xl">
          <FileText className="w-10 h-10 text-slate-600 mx-auto mb-2" />
          <p className="text-sm font-medium text-slate-400">No documents found</p>
          <p className="text-xs text-slate-600 mt-1">Upload a PDF, TXT, or DOCX above to get started</p>
        </div>
      ) : (
        <div className="space-y-2 max-h-[400px] overflow-y-auto pr-1">
          {filteredDocs.map((doc) => {
            const isSelected = selectedDocIds.includes(doc.id);
            return (
              <div
                key={doc.id}
                className={`glass-card p-3.5 rounded-xl flex items-center justify-between transition-all duration-200 ${
                  isSelected ? 'border-brand-500/50 bg-brand-500/10' : ''
                }`}
              >
                <div className="flex items-center space-x-3 min-w-0">
                  <input
                    type="checkbox"
                    checked={isSelected}
                    onChange={() => toggleSelect(doc.id)}
                    className="rounded bg-slate-800 border-slate-700 text-brand-500 focus:ring-0 cursor-pointer"
                  />

                  <div className="w-9 h-9 rounded-lg bg-slate-800/80 flex items-center justify-center flex-shrink-0 text-slate-300">
                    <FileText className="w-4 h-4 text-brand-400" />
                  </div>

                  <div className="min-w-0">
                    <p className="text-xs font-semibold text-slate-200 truncate">{doc.original_name}</p>
                    <div className="flex items-center space-x-3 text-[11px] text-slate-400 mt-0.5">
                      <span>{(doc.file_size / 1024).toFixed(1)} KB</span>
                      <span>•</span>
                      <span className="flex items-center space-x-1">
                        <Layers className="w-3 h-3 text-slate-500" />
                        <span>{doc.num_chunks || 0} Chunks</span>
                      </span>
                    </div>
                  </div>
                </div>

                <div className="flex items-center space-x-3 flex-shrink-0">
                  {getStatusBadge(doc.status)}

                  <button
                    onClick={() => handleDelete(doc.id)}
                    disabled={deletingId === doc.id}
                    className="p-1.5 text-slate-500 hover:text-rose-400 hover:bg-rose-500/10 rounded-lg transition"
                    title="Delete document"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
