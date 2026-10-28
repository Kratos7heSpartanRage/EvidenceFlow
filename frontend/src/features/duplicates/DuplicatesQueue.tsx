import { AlertTriangle, Check, GitMerge, ShieldAlert, X } from 'lucide-react';
import { useState } from 'react';
import { DedupTierBadge } from '../../components/ui/Badge';
import { api, getActiveReviewer } from '../../lib/api';
import { useAction, useData, useWorkspace } from '../../lib/workspace';
import type { EntityId } from '../../types/api';

export function DuplicatesQueue() {
  const { reviewId } = useWorkspace();

  const [tierFilter, setTierFilter] = useState<'all' | 'uncertain' | 'auto'>('all');
  const [activePairId, setActivePairId] = useState<EntityId | null>(null);
  const [decisionNote, setDecisionNote] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const [pairs, , loadPairs] = useData(['pairs', tierFilter], () => api.getDuplicatePairs(reviewId, tierFilter === 'all' ? undefined : { tier: tierFilter }));

  const summary = pairs.find(p => p.id === activePairId) || pairs[0];
  const [details] = useData<import('../../types/api').LiteratureRecord[]>(['pair-records', summary?.id], () => summary ? Promise.all([api.getRecord(summary.record_a_id), api.getRecord(summary.record_b_id)]) : Promise.resolve([]));
  const activePair = summary ? { ...summary, record_a: details[0], record_b: details[1] } : undefined;

  const handleDecision = useAction(async (decision: 'confirm' | 'reject') => {
    if (!activePair) return;
    try {
      setSubmitting(true);
      await api.submitPairDecision(reviewId, {
        record_a_id: activePair.record_a_id,
        record_b_id: activePair.record_b_id,
        decision,
        note: decisionNote.trim() || undefined,
        reviewer: getActiveReviewer()
      });
      setDecisionNote('');
      await loadPairs();
    } finally {
      setSubmitting(false);
    }
  });

  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      {/* Top Banner */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 p-5 rounded-xl bg-slate-900/60 border border-slate-800 shadow-xl">
        <div>
          <div className="flex items-center gap-2">
            <span className="px-2 py-0.5 rounded text-[11px] font-bold font-mono uppercase bg-brand-500/20 text-brand-300 border border-brand-500/30">
              Step 4: Deduplication
            </span>
            <span className="text-xs text-slate-400 font-mono">Preserve Every Record ? Hide, Never Delete</span>
          </div>
          <h2 className="text-xl font-bold text-slate-100 mt-1">Duplicate Pair Resolution Queue</h2>
          <p className="text-xs text-slate-400">
            Automated pair scoring groups identical papers. Confirm uncertain pairs or separate distinct reports.
          </p>
        </div>

        {/* Filter Pills */}
        <div className="flex items-center gap-1.5 p-1 bg-slate-950 rounded-lg border border-slate-800 text-xs">
          <button
            onClick={() => setTierFilter('all')}
            className={`px-3 py-1.5 rounded-md font-medium transition ${tierFilter === 'all' ? 'bg-brand-600 text-white shadow' : 'text-slate-400 hover:text-slate-200'
              }`}
          >
            All Pairs ({pairs.length})
          </button>
          <button
            onClick={() => setTierFilter('uncertain')}
            className={`px-3 py-1.5 rounded-md font-medium transition ${tierFilter === 'uncertain' ? 'bg-amber-600 text-white shadow' : 'text-slate-400 hover:text-slate-200'
              }`}
          >
            Uncertain Pairs
          </button>
          <button
            onClick={() => setTierFilter('auto')}
            className={`px-3 py-1.5 rounded-md font-medium transition ${tierFilter === 'auto' ? 'bg-emerald-600 text-white shadow' : 'text-slate-400 hover:text-slate-200'
              }`}
          >
            Auto Strong
          </button>
        </div>
      </div>

      {!activePair ? (
        <div className="p-12 text-center rounded-xl bg-slate-900/40 border border-slate-800 text-slate-400 text-sm">
          No duplicate pairs found matching the current filter.
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Pair List Sidebar */}
          <div className="lg:col-span-4 space-y-2 max-h-[700px] overflow-y-auto pr-1">
            {pairs.map(p => {
              const isSelected = activePair?.id === p.id;
              const hasConferenceGuard = p.conflicting_fields_json.some(f => f.toLowerCase().includes('abstract') || f.toLowerCase().includes('conference'));

              return (
                <button
                  key={p.id}
                  onClick={() => {
                    setActivePairId(p.id);
                    setDecisionNote('');
                  }}
                  className={`w-full text-left p-3.5 rounded-xl border text-xs transition-all space-y-2 ${isSelected
                      ? 'bg-slate-800/80 border-brand-500/60 shadow-lg'
                      : 'bg-slate-900/60 border-slate-800 hover:bg-slate-800/40'
                    }`}
                >
                  <div className="flex items-center justify-between">
                    <DedupTierBadge tier={p.tier} score={p.score} />
                    <span className="text-[10px] text-slate-400 font-mono">Method: {p.method}</span>
                  </div>

                  <div className="font-semibold text-slate-200 line-clamp-2">
                    {p.record_a?.title || `Record #${p.record_a_id}`}
                  </div>

                  <div className="flex items-center justify-between text-[11px] text-slate-400 font-mono">
                    <span>Rec #{p.record_a_id} ? Rec #{p.record_b_id}</span>
                    {hasConferenceGuard && (
                      <span className="text-amber-400 flex items-center gap-1 font-sans text-[10px]">
                        <AlertTriangle className="w-3 h-3" />
                        Conf vs Journal
                      </span>
                    )}
                  </div>
                </button>
              );
            })}
          </div>

          {/* Active Pair Side-by-Side Comparator */}
          <div className="lg:col-span-8 p-6 rounded-xl bg-slate-900/60 border border-slate-800 shadow-lg space-y-5">
            {/* Pair Header & Evidence */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-slate-800">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-brand-500/10 border border-brand-500/20 text-brand-400">
                  <GitMerge className="w-5 h-5" />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <h3 className="text-sm font-bold text-slate-100">Pair #{activePair.id} Comparison</h3>
                    <DedupTierBadge tier={activePair.tier} score={activePair.score} />
                  </div>
                  <p className="text-[11px] text-slate-400 mt-0.5">
                    Algorithm: <span className="font-mono text-slate-300">{activePair.algo_version} ({activePair.method})</span>
                  </p>
                </div>
              </div>
            </div>

            {/* Conference vs Journal Guard Warning Banner */}
            {activePair.conflicting_fields_json.some(f => f.toLowerCase().includes('abstract') || f.toLowerCase().includes('conference')) && (
              <div className="flex items-start gap-3 p-3.5 rounded-lg bg-amber-950/30 border border-amber-800/40 text-amber-200 text-xs">
                <ShieldAlert className="w-4 h-4 text-amber-400 mt-0.5 flex-shrink-0" />
                <div className="space-y-1">
                  <div className="font-bold text-amber-300">Conference vs. Journal Guard Activated</div>
                  <p className="leading-relaxed text-amber-200/90">
                    The algorithm detected matching titles but differing publication types (e.g. Meeting Abstract vs Journal Article). Per systematic review standards, separate reports of the same study are not duplicates.
                  </p>
                </div>
              </div>
            )}

            {/* Matched vs Conflicting Fields */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
              <div className="p-3 rounded-lg bg-slate-950/60 border border-slate-800">
                <span className="text-[10px] font-bold text-emerald-400 uppercase tracking-wider block mb-1">
                  Matched Fields
                </span>
                <div className="flex flex-wrap gap-1.5">
                  {activePair.matched_fields_json.map((f, i) => (
                    <span key={i} className="px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-300 font-mono text-[11px]">
                      ? {f}
                    </span>
                  ))}
                </div>
              </div>

              <div className="p-3 rounded-lg bg-slate-950/60 border border-slate-800">
                <span className="text-[10px] font-bold text-amber-400 uppercase tracking-wider block mb-1">
                  Conflicting Fields
                </span>
                <div className="flex flex-wrap gap-1.5">
                  {activePair.conflicting_fields_json.length > 0 ? (
                    activePair.conflicting_fields_json.map((f, i) => (
                      <span key={i} className="px-2 py-0.5 rounded bg-amber-500/10 text-amber-300 font-mono text-[11px]">
                        ? {f}
                      </span>
                    ))
                  ) : (
                    <span className="text-slate-500 text-[11px] italic">None (Exact match)</span>
                  )}
                </div>
              </div>
            </div>

            {/* Side-by-Side Comparison Cards */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
              {/* Record A */}
              <div className="p-4 rounded-xl bg-slate-950/80 border border-slate-800 space-y-2.5">
                <div className="flex items-center justify-between pb-2 border-b border-slate-800 text-[11px] font-mono">
                  <span className="font-bold text-brand-300">Record A (#{activePair.record_a_id})</span>
                  <span className="text-slate-400">{activePair.record_a?.source}</span>
                </div>
                <div>
                  <span className="text-slate-400 font-semibold block text-[10px] uppercase">Title</span>
                  <p className="font-bold text-slate-100 text-xs mt-0.5 leading-snug">{activePair.record_a?.title}</p>
                </div>
                <div className="text-[11px] text-slate-300 font-mono space-y-1">
                  <div>Authors: {activePair.record_a?.authors_json.join(', ')}</div>
                  <div>Year: {activePair.record_a?.year} | Journal: <span className="italic">{activePair.record_a?.journal}</span></div>
                  {activePair.record_a?.doi_norm && <div>DOI: {activePair.record_a.doi_norm}</div>}
                  {activePair.record_a?.pmid && <div>PMID: {activePair.record_a.pmid}</div>}
                </div>
                {activePair.record_a?.abstract && (
                  <div className="pt-1">
                    <span className="text-slate-400 font-semibold block text-[10px] uppercase">Abstract</span>
                    <p className="text-slate-300 text-[11px] leading-relaxed line-clamp-4 mt-0.5 italic">
                      "{activePair.record_a.abstract}"
                    </p>
                  </div>
                )}
              </div>

              {/* Record B */}
              <div className="p-4 rounded-xl bg-slate-950/80 border border-slate-800 space-y-2.5">
                <div className="flex items-center justify-between pb-2 border-b border-slate-800 text-[11px] font-mono">
                  <span className="font-bold text-brand-300">Record B (#{activePair.record_b_id})</span>
                  <span className="text-slate-400">{activePair.record_b?.source}</span>
                </div>
                <div>
                  <span className="text-slate-400 font-semibold block text-[10px] uppercase">Title</span>
                  <p className="font-bold text-slate-100 text-xs mt-0.5 leading-snug">{activePair.record_b?.title}</p>
                </div>
                <div className="text-[11px] text-slate-300 font-mono space-y-1">
                  <div>Authors: {activePair.record_b?.authors_json.join(', ')}</div>
                  <div>Year: {activePair.record_b?.year} | Journal: <span className="italic">{activePair.record_b?.journal}</span></div>
                  {activePair.record_b?.doi_norm && <div>DOI: {activePair.record_b.doi_norm}</div>}
                  {activePair.record_b?.pmid && <div>PMID: {activePair.record_b.pmid}</div>}
                </div>
                {activePair.record_b?.abstract && (
                  <div className="pt-1">
                    <span className="text-slate-400 font-semibold block text-[10px] uppercase">Abstract</span>
                    <p className="text-slate-300 text-[11px] leading-relaxed line-clamp-4 mt-0.5 italic">
                      "{activePair.record_b.abstract}"
                    </p>
                  </div>
                )}
              </div>
            </div>

            {/* Reviewer Action Bar */}
            <div className="p-4 rounded-xl bg-slate-950/90 border border-slate-800 space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-slate-200">Human Pair Decision:</span>
                <span className="text-[11px] text-slate-400 font-mono">Deciding as: <strong className="text-brand-400">{getActiveReviewer()}</strong></span>
              </div>

              <input
                type="text"
                value={decisionNote}
                onChange={e => setDecisionNote(e.target.value)}
                placeholder="Optional explanation / rationale for audit log..."
                className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-xs text-slate-200 focus:outline-none focus:border-brand-500"
              />

              <div className="flex items-center justify-end gap-3 pt-1">
                <button
                  type="button"
                  disabled={submitting}
                  onClick={() => handleDecision('reject')}
                  className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-rose-300 border border-rose-900/40 text-xs font-semibold transition"
                >
                  <X className="w-4 h-4 text-rose-400" />
                  <span>Reject (Distinct Studies)</span>
                </button>

                <button
                  type="button"
                  disabled={submitting}
                  onClick={() => handleDecision('confirm')}
                  className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold shadow-lg shadow-emerald-950/50 transition"
                >
                  <Check className="w-4 h-4" />
                  <span>Confirm Duplicate (Hide Record B)</span>
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
