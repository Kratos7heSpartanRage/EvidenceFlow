import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useEffect, useState } from 'react';
import { AmbientBackground } from '../components/ui/AmbientBackground';
import { CommandPalette } from '../components/ui/CommandPalette';
import { DataBoundary } from '../components/ui/DataBoundary';
import { KeyboardShortcutsModal } from '../components/ui/KeyboardShortcutsModal';
import { Modal } from '../components/ui/Modal';
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
import { RunsView } from '../features/runs/RunsView';
import { ScreeningQueue } from '../features/screening/ScreeningQueue';
import { SearchBuilder } from '../features/search/SearchBuilder';
import { api } from '../lib/api';
import { WorkspaceContext, useData } from '../lib/workspace';
import type { EntityId } from '../types/api';
import { Header } from './Header';
import { NavTab, Sidebar } from './Sidebar';

export function App() {
  const [view, setView] = useState<'landing' | 'workspace'>(() => {
    try {
      return (localStorage.getItem('evidenceflow_view') as 'landing' | 'workspace') || 'workspace';
    } catch {
      return 'workspace';
    }
  });

  const handleSetView = (nextView: 'landing' | 'workspace') => {
    setView(nextView);
    try {
      localStorage.setItem('evidenceflow_view', nextView);
    } catch {}
  };
  const [activeTab, setActiveTab] = useState<NavTab>('setup');
  const [isCommandPaletteOpen, setIsCommandPaletteOpen] = useState(false);
  const [isShortcutsOpen, setIsShortcutsOpen] = useState(false);
  const [isDark, setIsDark] = useState(() => {
    try {
      const saved = localStorage.getItem('evidenceflow_theme');
      return saved ? saved === 'dark' : true;
    } catch {
      return true;
    }
  });

  const client = useQueryClient();
  const [selectedId, setSelectedId] = useState(localStorage.getItem('evidenceflow_review') || '');
  const [creating, setCreating] = useState(false);
  const [title, setTitle] = useState('');
  const [question, setQuestion] = useState('');
  const [error, setError] = useState('');

  // Sync theme to document element
  useEffect(() => {
    try {
      if (isDark) {
        document.documentElement.classList.add('dark');
        localStorage.setItem('evidenceflow_theme', 'dark');
      } else {
        document.documentElement.classList.remove('dark');
        localStorage.setItem('evidenceflow_theme', 'light');
      }
    } catch {}
  }, [isDark]);

  // Global Command+K / Ctrl+K and shortcut listener
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        setIsCommandPaletteOpen(prev => !prev);
      }
      if (e.key === '?' && !['INPUT', 'TEXTAREA'].includes((e.target as HTMLElement)?.tagName)) {
        e.preventDefault();
        setIsShortcutsOpen(prev => !prev);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  const reviews = useQuery({ queryKey: ['reviews'], queryFn: api.listReviews, enabled: view === 'workspace' });
  const reviewId = reviews.data?.find(r => String(r.id) === selectedId)?.id || reviews.data?.[0]?.id;
  const reportError = (value: unknown) => setError(value instanceof Error ? value.message : String(value));

  const create = useMutation({
    mutationFn: () => api.createReview({ title: title.trim(), question: question.trim() }),
    onSuccess: async review => {
      setSelectedId(String(review.id));
      localStorage.setItem('evidenceflow_review', String(review.id));
      setCreating(false);
      setTitle('');
      setQuestion('');
      setActiveTab('setup');
      setError('');
      await client.invalidateQueries({ queryKey: ['reviews'] });
    },
    onError: reportError,
  });

  const handleRefresh = () => {
    setError('');
    void client.invalidateQueries();
  };

  if (view === 'landing') {
    return <LandingPage onEnterWorkspace={() => handleSetView('workspace')} isDark={isDark} />;
  }

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-[#070b13] text-slate-900 dark:text-slate-100 flex flex-col font-sans selection:bg-teal-500 selection:text-white transition-colors duration-300 relative">
      {/* Live Wallpaper & Subtle Parallax Ambient Background */}
      <AmbientBackground isDark={isDark} />

      {/* Streamlined Master Header */}
      <Header
        onRefresh={handleRefresh}
        onBackToLanding={() => handleSetView('landing')}
        onOpenCommandPalette={() => setIsCommandPaletteOpen(true)}
        onOpenShortcuts={() => setIsShortcutsOpen(true)}
        onToggleTheme={() => setIsDark(!isDark)}
        isDark={isDark}
        reviews={reviews.data || []}
        activeReviewId={reviewId}
        onSelectReview={id => {
          setSelectedId(String(id));
          localStorage.setItem('evidenceflow_review', String(id));
          setError('');
        }}
        onOpenCreateReview={() => setCreating(true)}
      />

      {error && (
        <div role="alert" className="px-6 py-2.5 bg-rose-500/10 border-b border-rose-500/30 text-rose-700 dark:text-rose-300 flex items-center justify-between text-xs backdrop-blur-md">
          <span>{error}</span>
          <button onClick={() => setError('')} aria-label="Dismiss error" className="font-semibold underline">
            Dismiss
          </button>
        </div>
      )}

      {/* Modal for Creating Systematic Review */}
      <Modal
        isOpen={creating}
        onClose={() => setCreating(false)}
        title="Initialize New Systematic Review"
        description="Establish the research question and PICO protocol for auditable systematic screening."
      >
        <form
          aria-label="Create review"
          className="space-y-4 text-xs"
          onSubmit={e => {
            e.preventDefault();
            create.mutate();
          }}
        >
          <div>
            <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
              Review Title:
            </label>
            <input
              required
              maxLength={255}
              value={title}
              onChange={e => setTitle(e.target.value)}
              placeholder="e.g. SGLT2 Inhibitors vs Metformin in Heart Failure"
              className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-800 rounded-lg text-slate-900 dark:text-slate-100 focus:outline-none focus:border-teal-500 text-xs"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
              PICO Research Question:
            </label>
            <textarea
              required
              maxLength={1000}
              value={question}
              onChange={e => setQuestion(e.target.value)}
              placeholder="e.g. In adults with chronic heart failure (P), does dapagliflozin (I) compared with standard care (C) reduce cardiovascular mortality (O)?"
              className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-800 rounded-lg text-slate-900 dark:text-slate-100 focus:outline-none focus:border-teal-500 text-xs min-h-[75px]"
            />
          </div>

          <div className="flex justify-end gap-2 pt-2 border-t border-slate-200 dark:border-slate-800">
            <button
              type="button"
              onClick={() => setCreating(false)}
              className="px-3 py-1.5 rounded-lg border border-slate-300 dark:border-slate-700 text-xs text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800"
            >
              Cancel
            </button>
            <button
              disabled={create.isPending || !title.trim() || !question.trim()}
              className="px-4 py-1.5 bg-teal-600 hover:bg-teal-500 rounded-lg text-xs font-semibold text-white disabled:opacity-50 shadow-sm transition"
            >
              {create.isPending ? 'Creating…' : 'Create Systematic Review'}
            </button>
          </div>
        </form>
      </Modal>

      {reviews.isPending && (
        <div role="status" className="p-12 text-center text-xs text-slate-500 dark:text-slate-400 animate-pulse">
          Connecting to EvidenceFlow review workspace…
        </div>
      )}

      {reviews.isError && (
        <div role="alert" className="p-10 text-center space-y-3">
          <p className="text-sm text-rose-600 dark:text-rose-400 font-medium">{reviews.error.message}</p>
          <button
            className="bg-teal-600 hover:bg-teal-500 text-white rounded-lg px-4 py-2 text-xs font-semibold shadow transition"
            onClick={() => reviews.refetch()}
          >
            Retry connection
          </button>
        </div>
      )}

      {!reviews.isPending && !reviews.isError && !reviewId && (
        <div className="p-16 text-center text-slate-500 dark:text-slate-400 space-y-4 max-w-md mx-auto">
          <h3 className="text-base font-bold text-slate-800 dark:text-slate-200">No Review Workspace Found</h3>
          <p className="text-xs leading-relaxed">
            Initialize your first systematic review to formulate Boolean search expressions and screen literature records.
          </p>
          <button
            onClick={() => setCreating(true)}
            className="px-4 py-2 rounded-lg bg-teal-600 hover:bg-teal-500 text-white font-semibold text-xs shadow-md transition"
          >
            + Create Review
          </button>
        </div>
      )}

      {reviewId && (
        <WorkspaceContext.Provider value={{ reviewId, reportError }}>
          <DataBoundary key={`${reviewId}-${activeTab}`}>
            <Workspace reviewId={reviewId} activeTab={activeTab} setActiveTab={setActiveTab} />
          </DataBoundary>
        </WorkspaceContext.Provider>
      )}

      {/* Global Command Palette */}
      <CommandPalette
        isOpen={isCommandPaletteOpen}
        onClose={() => setIsCommandPaletteOpen(false)}
        onSelectTab={setActiveTab}
        onToggleTheme={() => setIsDark(!isDark)}
        isDark={isDark}
        onBackToLanding={() => {
          setIsCommandPaletteOpen(false);
          handleSetView('landing');
        }}
      />

      {/* Global Keyboard Shortcuts Help */}
      <KeyboardShortcutsModal
        isOpen={isShortcutsOpen}
        onClose={() => setIsShortcutsOpen(false)}
      />
    </div>
  );
}

function Workspace({
  reviewId,
  activeTab,
  setActiveTab
}: {
  reviewId: EntityId;
  activeTab: NavTab;
  setActiveTab: (tab: NavTab) => void;
}) {
  const [review] = useData(['review'], () => api.getReview(reviewId));

  return (
    <div className="flex-1 flex flex-col md:flex-row overflow-hidden">
      <Sidebar activeTab={activeTab} onSelectTab={setActiveTab} stats={review?.stats} />

      {/* Main Viewport Content with Airy Whitespace & Background Blur */}
      <main className="flex-1 min-w-0 overflow-y-auto p-4 md:p-6 lg:p-8 bg-transparent">
        <NcbiDisclaimer />
        {activeTab === 'setup' && <ReviewSetup onProceedToSearch={() => setActiveTab('search')} />}
        {activeTab === 'search' && <SearchBuilder onViewScreening={() => setActiveTab('screening')} />}
        {activeTab === 'runs' && <RunsView />}
        {activeTab === 'duplicates' && <DuplicatesQueue />}
        {activeTab === 'screening' && <ScreeningQueue />}
        {activeTab === 'pico' && <PicoWorkspace />}
        {activeTab === 'intelligence' && <ReviewIntelligence />}
        {activeTab === 'history' && <HistoryDiffView onNavigateToConflicts={() => setActiveTab('conflicts')} />}
        {activeTab === 'conflicts' && <ConflictsWorkspace />}
        {activeTab === 'audit' && <AuditTrail />}
        {activeTab === 'export' && <ExportView />}
      </main>
    </div>
  );
}

export default App;
