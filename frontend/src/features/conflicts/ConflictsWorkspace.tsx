import React, { useState, useEffect } from 'react';
import { api, getActiveReviewer } from '../../lib/api';
import { Conflict } from '../../types/api';
import { AlertTriangle, CheckCircle, Split, HelpCircle, User, ShieldAlert, Sparkles, Check, ArrowRight } from 'lucide-react';

export function ConflictsWorkspace() {
  const [conflicts, setConflicts] = useState<Conflict[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedConflictId, setSelectedConflictId] = useState<number | null>(null);

  // Resolution modal state
  const [resolutionType, setResolutionType] = useState<'unify' | 'split' | 'maybe'>('unify');
  const [unifyDecision, setUnifyDecision] = useState<'include' | 'exclude'>('include');
  const [unifyReason, setUnifyReason] = useState('');
  const [resolving, setResolving] = useState(false);

  const loadConflicts = async () => {
    try {
      setLoading(true);
      const data = await api.getConflicts(1);
      setConflicts(data);
      if (data.length > 0 && !selectedConflictId) {
        setSelectedConflictId(data[0].id);
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadConflicts();
  }, []);

  const activeConflict = conflicts.find(c => c.id === selectedConflictId) || conflicts[0];

  const handleResolve = async () => {
    if (!activeConflict) return;
    try {
      setResolving(true);
      await api.resolveConflict(activeConflict.id, {
        resolution: resolutionType,
        decision: resolutionType === 'unify' ? unifyDecision : resolutionType === 'maybe' ? 'maybe' : undefined,
        reason: unifyReason.trim() || undefined,
        reviewer: getActiveReviewer()
      });
      await loadConflicts();
    } catch (err: any) {
      alert(`Resolution failed: ${err.message}`);
    } finally {
      setResolving(false);
    }
  };

  if (loading && conflicts.length === 0) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-brand-500"></div>
      </div>
    );
  }

  const openCount = conflicts.filter(c => c.status === 'open').length;

  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      {/* Top Banner */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 p-5 rounded-xl bg-slate-900/60 border border-slate-800 shadow-xl">
        <div>
          <div className="flex items-center gap-2">
            <span className="px-2 py-0.5 rounded text-[11px] font-bold font-mono uppercase bg-rose-500/20 text-rose-300 border border-rose-500/30">
              Level 2 Loop Governance
            </span>
            <span className="text-xs text-slate-400 font-mono">
              {openCount} Open Conflict{openCount === 1 ? '' : 's'}
            </span>
          </div>
          <h2 className="text-xl font-bold text-slate-100 mt-1">Group Decision Conflicts Resolution</h2>
          <p className="text-xs text-slate-400">
            When queries evolve and separate groups merge, conflicting human decisions are never resolved silently.
          </p>
        </div>

        {openCount > 0 && (
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-rose-950/40 border border-rose-800/40 text-rose-300 text-xs">
            <ShieldAlert className="w-4 h-4 text-rose-400 flex-shrink-0" />
            <span>Export CSV is blocked while conflicts remain open.</span>
          </div>
        )}
      </div>

      {conflicts.length === 0 ? (
        <div className="p-12 text-center rounded-xl bg-slate-900/40 border border-slate-800 text-slate-400 text-sm">
          No conflicts recorded. All duplicate merges have unanimous decisions.
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Conflicts Selector List */}
          <div className="lg:col-span-4 space-y-2 max-h-[700px] overflow-y-auto pr-1">
            {conflicts.map(c => {
              const isSelected = activeConflict?.id === c.id;
              const isOpen = c.status === 'open';

              return (
                <button
                  key={c.id}
                  onClick={() => setSelectedConflictId(c.id)}
                  className={`w-full text-left p-3.5 rounded-xl border text-xs transition-all space-y-2 ${
                    isSelected
                      ? 'bg-slate-800/90 border-rose-500/60 shadow-lg'
                      : 'bg-slate-900/60 border-slate-800 hover:bg-slate-800/40'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span
                      className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase ${
                        isOpen ? 'bg-rose-500/20 text-rose-300 border border-rose-500/30' : 'bg-emerald-500/20 text-emerald-300'
                      }`}
                    >
                      {c.status}
                    </span>
                    <span className="text-[10px] text-slate-500 font-mono">Run #{c.created_run_id}</span>
                  </div>

                  <h4 className="font-bold text-slate-100 text-xs line-clamp-1">
                    Conflict #{c.id}: Group Merge Inconsistency
                  </h4>

                  <p className="text-[11px] text-slate-400 leading-snug">
                    {c.details_json?.merging_reason}
                  </p>
                </button>
              );
            })}
          </div>

          {/* Active Conflict Detailed Resolution View */}
          <div className="lg:col-span-8 p-6 rounded-xl bg-slate-900/60 border border-slate-800 shadow-lg space-y-5">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <div className="flex items-center gap-2">
                <AlertTriangle className="w-5 h-5 text-rose-400" />
                <h3 className="text-sm font-bold text-slate-100">
                  Conflict #{activeConflict.id} Details & Decision Reconciler
                </h3>
              </div>
              <span className="text-[11px] font-mono text-slate-400">
                Fingerprint: {activeConflict.fingerprint.slice(0, 16)}...
              </span>
            </div>

            {/* Explanatory Banner */}
            <div className="p-3.5 rounded-lg bg-slate-950/80 border border-slate-800 text-xs space-y-1">
              <span className="text-slate-400 font-semibold block text-[10px] uppercase">
                Why this conflict was raised:
              </span>
              <p className="text-slate-200 leading-relaxed">
                {activeConflict.details_json?.merging_reason}. Two records were judged differently by reviewers under query version 1 and query version 2, but deduplication merged them into one group.
              </p>
            </div>

            {/* Conflicting Member Records Cards */}
            <div className="space-y-3">
              <span className="text-xs font-bold text-slate-400 uppercase tracking-wider block">
                Conflicting Member Records
              </span>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                {activeConflict.details_json?.records.map((rec: any) => (
                  <div key={rec.record_id} className="p-4 rounded-xl bg-slate-950/90 border border-slate-800 space-y-2">
                    <div className="flex items-center justify-between pb-1.5 border-b border-slate-800 font-mono text-[11px]">
                      <span className="font-bold text-brand-300">Record #{rec.record_id}</span>
                      <span
                        className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                          rec.decision === 'include'
                            ? 'bg-emerald-500/20 text-emerald-400'
                            : 'bg-rose-500/20 text-rose-400'
                        }`}
                      >
                        {rec.decision}
                      </span>
                    </div>

                    <h4 className="font-semibold text-slate-100 text-xs leading-snug line-clamp-2">
                      {rec.title}
                    </h4>

                    <div className="text-[11px] text-slate-400 italic">
                      Reason: "{rec.reason}"
                    </div>

                    <div className="flex items-center justify-between pt-1 text-[10px] text-slate-500 font-mono border-t border-slate-800/60">
                      <span>Reviewer: {rec.reviewer}</span>
                      <span>{new Date(rec.created_at).toLocaleDateString()}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Resolution Options Form */}
            {activeConflict.status === 'open' ? (
              <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-4">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-slate-200">Select Resolution Strategy:</span>
                  <span className="text-[11px] text-slate-400 font-mono">Reviewer: <strong className="text-brand-400">{getActiveReviewer()}</strong></span>
                </div>

                <div className="grid grid-cols-3 gap-2 text-xs">
                  <button
                    type="button"
                    onClick={() => setResolutionType('unify')}
                    className={`p-3 rounded-lg border text-left space-y-1 transition ${
                      resolutionType === 'unify'
                        ? 'bg-brand-600/20 border-brand-500 text-white shadow'
                        : 'bg-slate-900 border-slate-800 text-slate-400 hover:bg-slate-800'
                    }`}
                  >
                    <div className="font-bold flex items-center gap-1.5">
                      <Check className="w-3.5 h-3.5 text-brand-400" />
                      <span>Unify Group Decision</span>
                    </div>
                    <div className="text-[10px] opacity-80">Apply single decision to all members</div>
                  </button>

                  <button
                    type="button"
                    onClick={() => setResolutionType('split')}
                    className={`p-3 rounded-lg border text-left space-y-1 transition ${
                      resolutionType === 'split'
                        ? 'bg-brand-600/20 border-brand-500 text-white shadow'
                        : 'bg-slate-900 border-slate-800 text-slate-400 hover:bg-slate-800'
                    }`}
                  >
                    <div className="font-bold flex items-center gap-1.5">
                      <Split className="w-3.5 h-3.5 text-brand-400" />
                      <span>Not Duplicates (Split)</span>
                    </div>
                    <div className="text-[10px] opacity-80">Reject duplicate pair and separate</div>
                  </button>

                  <button
                    type="button"
                    onClick={() => setResolutionType('maybe')}
                    className={`p-3 rounded-lg border text-left space-y-1 transition ${
                      resolutionType === 'maybe'
                        ? 'bg-brand-600/20 border-brand-500 text-white shadow'
                        : 'bg-slate-900 border-slate-800 text-slate-400 hover:bg-slate-800'
                    }`}
                  >
                    <div className="font-bold flex items-center gap-1.5">
                      <HelpCircle className="w-3.5 h-3.5 text-brand-400" />
                      <span>Keep as Maybe</span>
                    </div>
                    <div className="text-[10px] opacity-80">Mark group Maybe with note</div>
                  </button>
                </div>

                {/* Sub-options for Unify */}
                {resolutionType === 'unify' && (
                  <div className="space-y-3 pt-2 text-xs">
                    <div className="flex items-center gap-4">
                      <label className="font-semibold text-slate-300">Choose Group Decision:</label>
                      <div className="flex items-center gap-3">
                        <label className="flex items-center gap-1.5 cursor-pointer text-slate-200">
                          <input
                            type="radio"
                            name="unifyDecision"
                            value="include"
                            checked={unifyDecision === 'include'}
                            onChange={() => setUnifyDecision('include')}
                            className="text-emerald-500 focus:ring-0"
                          />
                          <span>Include All</span>
                        </label>
                        <label className="flex items-center gap-1.5 cursor-pointer text-slate-200">
                          <input
                            type="radio"
                            name="unifyDecision"
                            value="exclude"
                            checked={unifyDecision === 'exclude'}
                            onChange={() => setUnifyDecision('exclude')}
                            className="text-rose-500 focus:ring-0"
                          />
                          <span>Exclude All</span>
                        </label>
                      </div>
                    </div>

                    <div>
                      <label className="text-[11px] text-slate-400 block mb-1">
                        Resolution Rationale / Reason:
                      </label>
                      <input
                        type="text"
                        value={unifyReason}
                        onChange={e => setUnifyReason(e.target.value)}
                        placeholder="e.g. Reconciled as early T2D population cohort; included after joint review..."
                        className="w-full px-3 py-2 bg-slate-900 border border-slate-800 rounded-lg text-slate-200 focus:outline-none focus:border-brand-500 text-xs"
                      />
                    </div>
                  </div>
                )}

                <div className="flex justify-end pt-2 border-t border-slate-800">
                  <button
                    type="button"
                    disabled={resolving}
                    onClick={handleResolve}
                    className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-brand-600 hover:bg-brand-500 text-white font-semibold text-xs shadow-lg shadow-brand-950/50 transition cursor-pointer"
                  >
                    <span>{resolving ? 'Resolving Conflict...' : 'Apply Conflict Resolution'}</span>
                    <ArrowRight className="w-4 h-4" />
                  </button>
                </div>
              </div>
            ) : (
              <div className="p-4 rounded-xl bg-emerald-950/30 border border-emerald-800/40 text-emerald-300 text-xs flex items-center gap-2">
                <CheckCircle className="w-4 h-4 text-emerald-400 flex-shrink-0" />
                <span>
                  Conflict resolved by <strong>{activeConflict.reviewer}</strong> on {activeConflict.resolved_at ? new Date(activeConflict.resolved_at).toLocaleString() : ''}.
                </span>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
