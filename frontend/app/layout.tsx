import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'ResearchFlow AI — Agentic Document Research Assistant',
  description: 'Upload your documents. Ask anything. Get evidence-backed answers with Corrective RAG.',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="bg-slate-950 text-slate-100 font-sans antialiased">
        {children}
      </body>
    </html>
  );
}
