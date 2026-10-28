import {
  AlertTriangle,
  CheckCircle,
  ChevronLeft,
  ChevronRight,
  HelpCircle,
  Keyboard,
  Search,
  ShieldCheck,
  XCircle
} from 'lucide-react';
import { useCallback, useDeferredValue, useEffect, useState } from 'react';
import { HumanDecisionBadge, MachineSuggestionBadge } from '../../components/ui/Badge';
import { KeyboardShortcutsModal } from '../../components/ui/KeyboardShortcutsModal';
import { ReasonModal } from '../../components/ui/ReasonModal';
import { api, getActiveReviewer } from '../../lib/api';
import { useAction, useData, useWorkspace } from '../../lib/workspace';
import type { EntityId } from '../../types/api';

export function ScreeningQueue() {
  const { reviewId } = useWorkspace();



  const [selectedRecordId, setSelectedRecordId] = useState<EntityId | null>(null);

  // Filters
  const [filterDecision, setFilterDecision] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [showHiddenDuplicates, setShowHiddenDuplicates] = useState(false);

  // Modals
  const [isReasonModalOpen, setIsReasonModalOpen] = useState(false);
  const [isShortcutsModalOpen, setIsShortcutsModalOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const [criteriaVer] = useData(['criteria'], () => api.getCriteria(reviewId));
  const criteria = criteriaVer?.criteria || [];
  const deferredSearch = useDeferredValue(searchQuery);
  const params = {
    show_hidden: showHiddenDuplicates, decision: filterDecision === 'all' ? undefined : filterDecision,
    q: deferredSearch.trim() || undefined
  };
  const [result, , loadData] = useData(['records', params], () => api.getRecords(reviewId, params));
  const records = result.items;
  const summary = records.find(r => r.id === selectedRecordId) || records[0];
  const [activeRecord] = useData(['record', summary?.id], () => summary ? api.getRecord(summary.id) : Promise.resolve(null));

  // Navigate next/previous
  const handleNavigate = useCallback((direction: 'next' | 'prev') => {
    if (!activeRecord || records.length === 0) return;
    const currentIndex = records.findIndex(r => r.id === activeRecord.id);
    if (currentIndex === -1) return;

    if (direction === 'next') {
      const nextIndex = (currentIndex + 1) % records.length;
      setSelectedRecordId(records[nextIndex].id);
    } else {
      const prevIndex = (currentIndex - 1 + records.length) % records.length;
      setSelectedRecordId(records[prevIndex].id);
    }
  }, [activeRecord, records]);

  // Screening decision handlers
  const handleDecision = useAction(async (decision: 'include' | 'exclude' | 'maybe', reasonData?: { criterion_id?: EntityId | null; reason_text: string; note?: string; }) => {
    if (!activeRecord) return;

    if (decision === 'exclude' && !reasonData) {
      // Must open reason modal to enforce client-side requirement
      setIsReasonModalOpen(true);
      return;
    }

    try {
      setSubmitting(true);
      await api.submitScreeningDecision(activeRecord.id, {
        decision,
        criterion_id: reasonData?.criterion_id || null,
        reason_text: reasonData?.reason_text,
        note: reasonData?.note,
        reviewer: getActiveReviewer()
      });

      // Reload and advance to next record
      await loadData();
      handleNavigate('next');
    } finally {
      setSubmitting(false);
    }
  });

  // Keyboard hotkeys: I, E, M, N, P, ?
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Don't trigger if user is typing in an input or textarea
      if (submitting || isReasonModalOpen || isShortcutsModalOpen) return;
      if (['INPUT', 'TEXTAREA', 'SELECT'].includes((e.target as HTMLElement).tagName)) {
        return;
      }

      if (e.key === 'i' || e.key === 'I') {
        e.preventDefault();
        handleDecision('include');
      } else if (e.key === 'e' || e.key === 'E') {
        e.preventDefault();
        handleDecision('exclude');
      } else if (e.key === 'm' || e.key === 'M') {
        e.preventDefault();
        handleDecision('maybe');
      } else if (e.key === 'n' || e.key === 'N') {
        e.preventDefault();
        handleNavigate('next');
      } else if (e.key === 'p' || e.key === 'P') {
        e.preventDefault();
        handleNavigate('prev');
      } else if (e.key === '?') {
        e.preventDefault();
        setIsShortcutsModalOpen(true);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleDecision, handleNavigate, submitting, isReasonModalOpen, isShortcutsModalOpen]);

  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      {/* Top Banner */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 p-5 rounded-xl bg-slate-900/60 border border-slate-800 shadow-xl">
        <div>
          <div className="flex items-center gap-2">
            <span className="px-2 py-0.5 rounded text-[11px] font-bold font-mono uppercase bg-brand-500/20 text-brand-300 border border-brand-500/30">
              Step 5: Screening
            </span>
            <span className="text-xs text-slate-400 font-mono">Include ? Exclude with Reason ? Maybe</span>
          </div>
          <h2 className="text-xl font-bold text-slate-100 mt-1">Title & Abstract Screening Queue</h2>
          <p className="text-xs text-slate-400">
            Machine evidence suggests eligibility; humans stay in charge. Decisions apply across duplicate groups.
          </p>
        </div>

        {/* Hotkey Help Button */}
        <button
          onClick={() => setIsShortcutsModalOpen(true)}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition"
        >
          <Keyboard className="w-3.5 h-3.5 text-brand-400" />
          <span>Hotkeys: I / E / M / N (?)</span>
        </button>
      </div>

      {/* Filter and Search Bar */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 p-3 rounded-xl bg-slate-950/80 border border-slate-800 text-xs">
        {/* Decision Filter Pills */}
        <div className="flex items-center gap-1 overflow-x-auto">
          {[
            { id: 'all', label: 'All Records' },
            { id: 'unscreened', label: 'Unscreened' },
            { id: 'include', label: 'Included' },
            { id: 'exclude', label: 'Excluded' },
            { id: 'maybe', label: 'Maybe' }
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => setFilterDecision(tab.id)}
              className={`px-3 py-1.5 rounded-md font-medium whitespace-nowrap transition ${filterDecision === tab.id
                  ? 'bg-brand-600 text-white shadow'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
                }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Search input + Duplicate toggle */}
        <div className="flex items-center gap-3">
          <div className="relative flex-1 sm:w-64">
            <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Search title, abstract, or PMID..."
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}

              className="w-full pl-8 pr-3 py-1.5 bg-slate-900 border border-slate-800 rounded-lg text-slate-200 placeholder-slate-500 text-xs focus:outline-none focus:border-brand-500"
            />
          </div>

          <label className="flex items-center gap-1.5 cursor-pointer text-slate-400 hover:text-slate-300 text-xs whitespace-nowrap">
            <input
              type="checkbox"
              checked={showHiddenDuplicates}
              onChange={e => setShowHiddenDuplicates(e.target.checked)}
              className="rounded border-slate-700 text-brand-600 bg-slate-900 w-3.5 h-3.5"
            />
            <span>Show duplicate members</span>
          </label>
        </div>
      </div>

      {/* Main Split-Pane Layout */}
      {!activeRecord ? (
        <div className="p-12 text-center rounded-xl bg-slate-900/40 border border-slate-800 text-slate-400 text-sm">
          No records match the current screening criteria and search filter.
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Left Column: Records Queue List */}
          <div className="lg:col-span-5 space-y-2 max-h-[720px] overflow-y-auto pr-1">
            {records.map((r, idx) => {
              const isSelected = activeRecord?.id === r.id;
              return (
                <button
                  key={r.id}
                  onClick={() => setSelectedRecordId(r.id)}
                  className={`w-full text-left p-3.5 rounded-xl border text-xs transition-all space-y-2 ${isSelected
                      ? 'bg-slate-800/90 border-brand-500/60 shadow-lg'
                      : 'bg-slate-900/60 border-slate-800 hover:bg-slate-800/40'
                    }`}
                >
                  <div className="flex items-center justify-between gap-1">
                    <span className="font-mono text-[10px] text-slate-400">
                      #{idx + 1} ? Rec #{r.id}
                    </span>
                    <div className="flex items-center gap-1.5">
                      <MachineSuggestionBadge suggestion={r.suggestion} />
                      <HumanDecisionBadge decision={r.current_decision} />
                    </div>
                  </div>

                  <h4 className="font-semibold text-slate-100 line-clamp-2 text-xs leading-snug">
                    {r.title}
                  </h4>

                  <div className="flex items-center justify-between text-[11px] text-slate-400 font-mono">
                    <span>{r.first_author_norm || r.authors_json[0] || 'Unknown'} ({r.year || 'n.d.'})</span>
                    <span className="text-[10px] uppercase px-1.5 py-0.2 rounded bg-slate-800 text-slate-300">
                      {r.source}
                    </span>
                  </div>
                </button>
              );
            })}
          </div>

          {/* Right Column: Active Record Detail & Screening Actions */}
          <div className="lg:col-span-7 p-6 rounded-xl bg-slate-900/60 border border-slate-800 shadow-lg space-y-5">
            {/* Header with Title and Metadata */}
            <div className="space-y-3 pb-4 border-b border-slate-800">
              <div className="flex items-center justify-between text-[11px] text-slate-400 font-mono">
                <div className="flex items-center gap-2">
                  <span className="px-2 py-0.5 rounded bg-slate-800 text-slate-200 font-bold">
                    RECORD #{activeRecord.id}
                  </span>
                  <span>Source: <strong className="text-brand-300">{activeRecord.source}</strong></span>
                  {activeRecord.group_members_count && activeRecord.group_members_count > 1 && (
                    <span className="px-1.5 py-0.5 rounded bg-brand-500/10 text-brand-300 border border-brand-500/20 font-sans">
                      Group of {activeRecord.group_members_count} papers
                    </span>
                  )}
                </div>

                {/* Prev / Next buttons */}
                <div className="flex items-center gap-1">
                  <button
                    onClick={() => handleNavigate('prev')}
                    className="p-1 rounded hover:bg-slate-800 text-slate-400 hover:text-slate-200 transition"
                    title="Previous Record (P)"
                  >
                    <ChevronLeft className="w-4 h-4" />
                  </button>
                  <button
                    onClick={() => handleNavigate('next')}
                    className="p-1 rounded hover:bg-slate-800 text-slate-400 hover:text-slate-200 transition"
                    title="Next Record (N)"
                  >
                    <ChevronRight className="w-4 h-4" />
                  </button>
                </div>
              </div>

              <h3 className="text-base font-bold text-slate-100 leading-snug">
                {activeRecord.title}
              </h3>

              {/* Bibliographic details */}
              <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-slate-300 font-mono">
                <span>Authors: <strong className="text-slate-200">{activeRecord.authors_json.join(', ')}</strong></span>
                <span>Year: <strong>{activeRecord.year}</strong></span>
                <span>Journal: <strong className="italic text-slate-200">{activeRecord.journal}</strong></span>
                {activeRecord.doi_norm && (
                  <span className="text-brand-400">DOI: {activeRecord.doi_norm}</span>
                )}
                {activeRecord.pmid && (
                  <span className="text-slate-400">PMID: {activeRecord.pmid}</span>
                )}
              </div>
            </div>

            {/* Machine Suggestion & Evidence Panel */}
            {activeRecord.suggestion && (
              <div className="p-3.5 rounded-lg bg-slate-950/70 border border-slate-800/90 text-xs space-y-1.5">
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-slate-300 flex items-center gap-1.5">
                    <ShieldCheck className="w-4 h-4 text-brand-400" />
                    <span>Algorithmic Screening Recommendation:</span>
                  </span>
                  <MachineSuggestionBadge suggestion={activeRecord.suggestion} />
                </div>
                <p className="text-slate-300 leading-relaxed italic">
                  "{activeRecord.suggestion.evidence_json?.explanation}"
                </p>
              </div>
            )}

            {/* Abstract Text with formatted typography */}
            <div className="space-y-1.5">
              <span className="text-xs font-bold text-slate-400 uppercase tracking-wider block">
                Study Abstract
              </span>
              <div className="p-4 rounded-xl bg-slate-950/80 border border-slate-800 text-slate-200 text-xs leading-relaxed max-h-[300px] overflow-y-auto font-sans">
                {activeRecord.abstract ? (
                  activeRecord.abstract
                ) : (
                  <span className="text-amber-400/90 italic flex items-center gap-2">
                    <AlertTriangle className="w-4 h-4" />
                    No abstract provided in literature database record. Reviewer manual appraisal required.
                  </span>
                )}
              </div>
            </div>

            {/* Human Decision Status Bar */}
            <div className="flex items-center justify-between p-3 rounded-lg bg-slate-950/60 border border-slate-800 text-xs">
              <span className="text-slate-400">Current Human Status:</span>
              <HumanDecisionBadge decision={activeRecord.current_decision} />
            </div>

            {/* Action Buttons: Include, Exclude, Maybe */}
            <div className="pt-2 border-t border-slate-800 space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-slate-200">Submit Your Decision:</span>
                <span className="text-[11px] text-slate-400 font-mono">Reviewer: <strong className="text-brand-400">{getActiveReviewer()}</strong></span>
              </div>

              <div className="grid grid-cols-3 gap-3">
                <button
                  type="button"
                  disabled={submitting}
                  onClick={() => handleDecision('include')}
                  className="flex items-center justify-center gap-2 py-3 px-4 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs shadow-lg shadow-emerald-950/50 transition cursor-pointer active:scale-95"
                >
                  <CheckCircle className="w-4 h-4" />
                  <span>Include (I)</span>
                </button>

                <button
                  type="button"
                  disabled={submitting}
                  onClick={() => handleDecision('exclude')}
                  className="flex items-center justify-center gap-2 py-3 px-4 rounded-xl bg-rose-600 hover:bg-rose-500 text-white font-bold text-xs shadow-lg shadow-rose-950/50 transition cursor-pointer active:scale-95"
                >
                  <XCircle className="w-4 h-4" />
                  <span>Exclude (E)</span>
                </button>

                <button
                  type="button"
                  disabled={submitting}
                  onClick={() => handleDecision('maybe')}
                  className="flex items-center justify-center gap-2 py-3 px-4 rounded-xl bg-amber-600 hover:bg-amber-500 text-white font-bold text-xs shadow-lg shadow-amber-950/50 transition cursor-pointer active:scale-95"
                >
                  <HelpCircle className="w-4 h-4" />
                  <span>Maybe (M)</span>
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Mandatory Exclusion Reason Modal */}
      <ReasonModal
        isOpen={isReasonModalOpen}
        onClose={() => setIsReasonModalOpen(false)}
        criteria={criteria}
        recordTitle={activeRecord?.title}
        onConfirm={reasonData => handleDecision('exclude', reasonData)}
      />

      {/* Keyboard Shortcuts Reference Modal */}
      <KeyboardShortcutsModal
        isOpen={isShortcutsModalOpen}
        onClose={() => setIsShortcutsModalOpen(false)}
      />
    </div>
  );
}
