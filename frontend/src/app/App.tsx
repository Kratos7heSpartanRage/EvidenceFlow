import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { DataBoundary } from '../components/ui/DataBoundary';
import { NcbiDisclaimer } from '../components/ui/NcbiDisclaimer';
import { AuditTrail } from '../features/audit/AuditTrail';
import { ConflictsWorkspace } from '../features/conflicts/ConflictsWorkspace';
import { DuplicatesQueue } from '../features/duplicates/DuplicatesQueue';
import { ExportView } from '../features/export/ExportView';
import { HistoryDiffView } from '../features/history/HistoryDiffView';
import { ReviewIntelligence } from '../features/intelligence/ReviewIntelligence';
import { LandingPage } from '../features/landing/LandingPage';
import { PicoWorkspace } from '../features/pico/PicoWorkspace';
import { ReviewSetup } from '../features/reviews/ReviewSetup';
import { ScreeningQueue } from '../features/screening/ScreeningQueue';
import { SearchBuilder } from '../features/search/SearchBuilder';
import { api } from '../lib/api';
import { WorkspaceContext, useData } from '../lib/workspace';
import type { EntityId } from '../types/api';
import { Header } from './Header';
import { NavTab, Sidebar } from './Sidebar';

export function App() {
  const [view, setView] = useState<'landing' | 'workspace'>('landing');
  const [activeTab, setActiveTab] = useState<NavTab>('setup');
  const client = useQueryClient();
  const [selectedId, setSelectedId] = useState(localStorage.getItem('evidenceflow_review') || '');
  const [creating, setCreating] = useState(false);
  const [title, setTitle] = useState('');
  const [question, setQuestion] = useState('');
  const [error, setError] = useState('');
  const reviews = useQuery({ queryKey: ['reviews'], queryFn: api.listReviews, enabled: view === 'workspace' });
  const reviewId = reviews.data?.find(r => String(r.id) === selectedId)?.id || reviews.data?.[0]?.id;
  const reportError = (value: unknown) => setError(value instanceof Error ? value.message : String(value));
  const create = useMutation({
    mutationFn: () => api.createReview({ title: title.trim(), question: question.trim() }),
    onSuccess: async review => {
      setSelectedId(String(review.id)); localStorage.setItem('evidenceflow_review', String(review.id));
      setCreating(false); setTitle(''); setQuestion(''); setActiveTab('setup'); setError('');
      await client.invalidateQueries({ queryKey: ['reviews'] });
    }, onError: reportError,
  });
  const handleRefresh = () => { setError(''); void client.invalidateQueries(); };

  // The landing page does not create or select server data.
  if (view === 'landing') {
    return <LandingPage onEnterWorkspace={() => setView('workspace')} />;
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans selection:bg-brand-500 selection:text-white">
      {/* Top Header */}
      <Header
        onRefresh={handleRefresh}
        onBackToLanding={() => setView('landing')}
      />

      <div className="px-6 py-3 border-b border-slate-800 flex flex-wrap items-center gap-3">
        <label htmlFor="active-review" className="text-sm text-slate-400">Review</label>
        <select id="active-review" className="bg-slate-900 border border-slate-700 rounded-lg p-2 max-w-md"
          value={reviewId || ''} onChange={e => {
            setSelectedId(e.target.value); localStorage.setItem('evidenceflow_review', e.target.value); setError('');
          }}>
          {!reviews.data?.length && <option value="">No reviews yet</option>}
          {reviews.data?.map(r => <option key={r.id} value={r.id}>{r.title}</option>)}
        </select>
        <button className="px-3 py-2 rounded-lg bg-brand-600" onClick={() => setCreating(!creating)}>New review</button>
      </div>
      {error && <div role="alert" className="px-6 py-3 bg-rose-950 text-rose-200 flex justify-between gap-3">
        <span>{error}</span><button onClick={() => setError('')} aria-label="Dismiss error">Dismiss</button>
      </div>}
      {creating && <form aria-label="Create review" className="p-6 space-y-3 border-b border-slate-800" onSubmit={e => { e.preventDefault(); create.mutate(); }}>
        <label className="block">Review title<input required maxLength={255} value={title} onChange={e => setTitle(e.target.value)} className="block p-2 mt-1 w-full bg-slate-900 border border-slate-700 rounded" /></label>
        <label className="block">Research question<textarea required maxLength={1000} value={question} onChange={e => setQuestion(e.target.value)} className="block p-2 mt-1 w-full bg-slate-900 border border-slate-700 rounded" /></label>
        <button disabled={create.isPending || !title.trim() || !question.trim()} className="px-4 py-2 bg-brand-600 rounded disabled:opacity-50">{create.isPending ? 'Creating…' : 'Create review'}</button>
      </form>}
      {reviews.isPending && <p role="status" className="p-6">Loading reviews…</p>}
      {reviews.isError && <div role="alert" className="p-6"><p>{reviews.error.message}</p><button className="mt-3 bg-brand-600 rounded p-2" onClick={() => reviews.refetch()}>Retry connection</button></div>}
      {!reviews.isPending && !reviews.isError && !reviewId && <p className="p-6 text-slate-400">Create a review to define your question, add criteria and search the literature.</p>}
      {reviewId && <WorkspaceContext.Provider value={{ reviewId, reportError }}>
        <DataBoundary key={`${reviewId}-${activeTab}`}>
          <Workspace reviewId={reviewId} activeTab={activeTab} setActiveTab={setActiveTab} />
        </DataBoundary>
      </WorkspaceContext.Provider>}
    </div>
  );
}

function Workspace({ reviewId, activeTab, setActiveTab }: { reviewId: EntityId; activeTab: NavTab; setActiveTab: (tab: NavTab) => void; }) {
  const [review] = useData(['review'], () => api.getReview(reviewId));
  return (
    <div className="flex-1 flex flex-col md:flex-row overflow-hidden">
      <Sidebar
        activeTab={activeTab}
        onSelectTab={setActiveTab}
        stats={review.stats}
      />

      {/* Viewport Content */}
      <main className="flex-1 min-w-0 overflow-y-auto p-4 md:p-8 bg-gradient-to-b from-slate-950 via-slate-900/40 to-slate-950">
        <NcbiDisclaimer />
        {activeTab === 'setup' && (
          <ReviewSetup onProceedToSearch={() => setActiveTab('search')} />
        )}
        {activeTab === 'search' && <SearchBuilder onViewScreening={() => setActiveTab('screening')} />}
        {activeTab === 'duplicates' && <DuplicatesQueue />}
        {activeTab === 'screening' && <ScreeningQueue />}
        {activeTab === 'pico' && <PicoWorkspace />}
        {activeTab === 'intelligence' && <ReviewIntelligence />}
        {activeTab === 'history' && (
          <HistoryDiffView onNavigateToConflicts={() => setActiveTab('conflicts')} />
        )}
        {activeTab === 'conflicts' && <ConflictsWorkspace />}
        {activeTab === 'audit' && <AuditTrail />}
        {activeTab === 'export' && <ExportView />}
      </main>
    </div>
  );
}

export default App;
