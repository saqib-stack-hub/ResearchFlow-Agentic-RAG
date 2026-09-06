'use client';

import React, { useState, useEffect } from 'react';
import { Navbar } from '../components/Navbar';
import { DocumentUpload } from '../components/DocumentUpload';
import { DocumentList } from '../components/DocumentList';
import { ChatInterface } from '../components/ChatInterface';
import { GraphVisualizer } from '../components/GraphVisualizer';
import { SystemHealthDashboard } from '../components/SystemHealthDashboard';
import { fetchDocuments, Document } from '../lib/api';

export default function Home() {
  const [activeTab, setActiveTab] = useState('chat');
  const [documents, setDocuments] = useState<Document[]>([]);
  const [selectedDocIds, setSelectedDocIds] = useState<string[]>([]);
  const [sessionId, setSessionId] = useState<string>('');

  // Generate unique session ID on load
  useEffect(() => {
    setSessionId(`session-${Math.random().toString(36).substr(2, 9)}`);
    loadDocs();
  }, []);

  const loadDocs = async () => {
    try {
      const res = await fetchDocuments();
      setDocuments(res.documents || []);
    } catch (err) {
      console.log('Failed to fetch documents from API backend');
    }
  };

  const handleUploadSuccess = (doc: Document) => {
    setDocuments((prev) => [doc, ...prev]);
    loadDocs();
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans selection:bg-brand-500 selection:text-white">
      {/* Header Navigation */}
      <Navbar activeTab={activeTab} setActiveTab={setActiveTab} />

      {/* Main View Area */}
      <main className="flex-1 p-6 max-w-7xl mx-auto w-full space-y-6">
        {activeTab === 'chat' && (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
            {/* Sidebar Documents Quick Scope selector */}
            <div className="lg:col-span-4 space-y-6">
              <DocumentUpload onUploadSuccess={handleUploadSuccess} />
              <DocumentList
                documents={documents}
                onRefresh={loadDocs}
                selectedDocIds={selectedDocIds}
                setSelectedDocIds={setSelectedDocIds}
              />
            </div>

            {/* Main Interactive Chat Engine */}
            <div className="lg:col-span-8">
              <ChatInterface sessionId={sessionId} selectedDocIds={selectedDocIds} />
            </div>
          </div>
        )}

        {activeTab === 'documents' && (
          <div className="max-w-4xl mx-auto space-y-6">
            <DocumentUpload onUploadSuccess={handleUploadSuccess} />
            <DocumentList
              documents={documents}
              onRefresh={loadDocs}
              selectedDocIds={selectedDocIds}
              setSelectedDocIds={setSelectedDocIds}
            />
          </div>
        )}

        {activeTab === 'graph' && (
          <div className="max-w-5xl mx-auto">
            <GraphVisualizer />
          </div>
        )}

        {activeTab === 'health' && (
          <div className="max-w-5xl mx-auto">
            <SystemHealthDashboard />
          </div>
        )}
      </main>
    </div>
  );
}
