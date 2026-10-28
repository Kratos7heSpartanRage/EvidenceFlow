import { useState } from 'react';
import {
  AlertTriangle,
  CheckCircle2,
  HelpCircle,
  ShieldAlert,
  Split
} from 'lucide-react';
import { HumanDecisionBadge } from '../../components/ui/Badge';
import { api, getActiveReviewer } from '../../lib/api';
import { useAction, useData, useWorkspace } from '../../lib/workspace';
import type { DecisionType, EntityId } from '../../types/api';

export function ConflictsWorkspace() {
  const { reviewId } = useWorkspace();
  const [selectedId, setSelectedId] = useState<EntityId | null>(null);
  const [decision, setDecision] = useState<DecisionType>('include');
  const [reason, setReason] = useState('');
  const [pending, setPending] = useState(false);
  const [resolutionSuccess, setResolutionSuccess] = useState('');

  const [conflicts] = useData(['conflicts'], () => api.getConflicts(reviewId));
  const active = conflicts.find(c => c.id === selectedId) || conflicts[0];

  const [members] = useData(
    ['conflict-members', active?.id],
    () => (active ? Promise.all((active.records || []).map(r => api.getRecord(r.id))) : Promise.resolve([]))
  );

  // 3 Resolution Actions:
  // (a) Unify cluster under one consensus decision
  const handleUnifyGroup = useAction(async () => {
    if (!active || pending) return;
    if (decision === 'exclude' && !reason.trim()) return;
    try {
      setPending(true);
      await api.resolveConflict(active.id, {
        resolution: 'unify',
        decision,
        reason: reason.trim() || undefined,
        reviewer: getActiveReviewer()
      });
      setResolutionSuccess(`Applied consensus ${decision.toUpperCase()} across all cluster members.`);
      setReason('');
    } finally {
      setPending(false);
    }
  });

  // (b) "These are not duplicates" -> Split cluster & reject bridging pair
  const handleSplitNotDuplicates = useAction(async () => {
    if (!active || pending) return;
    try {
      setPending(true);
      if (members.length >= 2) {
        await api.submitPairDecision(reviewId, {
          record_a_id: members[0].id,
          record_b_id: members[1].id,
          decision: 'reject',
          note: reason.trim() || 'Reviewer determined records are not duplicates during conflict resolution',
          reviewer: getActiveReviewer()
        });
      }
      await api.resolveConflict(active.id, {
        resolution: 'maybe',
        reason: 'Split cluster: studies marked as distinct non-duplicate publications',
        reviewer: getActiveReviewer()
      });
      setResolutionSuccess('Split cluster: studies marked as distinct non-duplicates.');
      setReason('');
    } finally {
      setPending(false);
    }
  });

  // (c) Keep as Maybe with note
  const handleKeepMaybe = useAction(async () => {
    if (!active || pending) return;
    try {
      setPending(true);
      await api.resolveConflict(active.id, {
        resolution: 'maybe',
        decision: 'maybe',
        reason: reason.trim() || 'Maintained as Maybe pending full-text retrieval',
        reviewer: getActiveReviewer()
      });
      setResolutionSuccess('Retained cluster records in Maybe queue with reviewer note.');
      setReason('');
    } finally {
      setPending(false);
    }
  });

  return (
    <div className="max-w-6xl mx-auto space-y-5 py-2">
      {/* Top Banner */}
      <div className="p-5 rounded-2xl bg-white/70 dark:bg-slate-900/60 backdrop-blur-md border border-slate-200/80 dark:border-slate-800/80 shadow-sm space-y-2 hover:-translate-y-0.5 hover:shadow-md transition-all duration-200">
        <div className="flex items-center gap-2">
          <span className="px-2.5 py-0.5 rounded-md text-[11px] font-bold font-mono uppercase bg-violet-500/10 text-violet-700 dark:text-violet-300 border border-violet-500/30">
            Arbitration • Loop Guard
          </span>
          <span className="text-xs text-slate-500 dark:text-slate-400 font-mono">Quarantined from PRISMA CSV until resolved</span>
        </div>
        <h2 className="text-xl font-bold text-slate-900 dark:text-slate-100">Multi-Reviewer Conflict Arbitration</h2>
        <p className="text-xs text-slate-500 dark:text-slate-400 leading-relaxed max-w-3xl">
          When query revisions merge duplicate groups containing opposing human verdicts (e.g. Include vs Exclude), EvidenceFlow flags a conflict rather than silently discarding decisions. Never auto-resolved.
        </p>
      </div>

      {!conflicts.length ? (
        <div className="p-12 text-center rounded-2xl bg-white/70 dark:bg-slate-900/60 border border-slate-200/80 dark:border-slate-800 text-slate-500 dark:text-slate-400 text-sm">
          No conflicts recorded. All duplicate cluster verdicts are currently aligned.
        </div>
      ) : (
        active && (
          <div className="grid lg:grid-cols-12 gap-5">
            {/* Left Column: Conflict Queue */}
            <div className="lg:col-span-4 space-y-2 max-h-[700px] overflow-y-auto">
              {conflicts.map(c => {
                const isSelected = active.id === c.id;
                return (
                  <button
                    key={c.id}
                    onClick={() => {
                      setSelectedId(c.id);
                      setReason('');
                      setResolutionSuccess('');
                    }}
                    className={`w-full text-left p-3.5 rounded-2xl border text-xs transition-all duration-150 space-y-1.5 hover:-translate-y-0.5 hover:shadow-md ${
                      isSelected
                        ? 'border-violet-500/80 bg-white dark:bg-violet-950/20 shadow-md'
                        : 'border-slate-200/80 dark:border-slate-800 bg-white/70 dark:bg-slate-900/60 hover:bg-slate-50 dark:hover:bg-slate-800/60'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-mono font-bold text-[10px] text-violet-700 dark:text-violet-400">
                        CONFLICT #{String(c.id).slice(0, 8)}
                      </span>
                      <span
                        className={`px-2 py-0.5 rounded text-[10px] uppercase font-mono font-bold ${
                          c.status === 'open'
                            ? 'bg-rose-50 dark:bg-rose-500/20 text-rose-700 dark:text-rose-300 border border-rose-200 dark:border-rose-500/30'
                            : 'bg-emerald-50 dark:bg-emerald-500/20 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-500/30'
                        }`}
                      >
                        {c.status}
                      </span>
                    </div>
                    <div className="font-semibold text-slate-900 dark:text-slate-100 capitalize">
                      {c.type.replace(/_/g, ' ')}
                    </div>
                    <p className="text-[11px] text-slate-500 dark:text-slate-400 line-clamp-2">
                      {c.details_json?.explanation || 'Contradictory screening decisions merged in cluster'}
                    </p>
                  </button>
                );
              })}
            </div>

            {/* Right Column: Conflicting Studies Side-by-Side & 3 Resolution Actions */}
            <div className="lg:col-span-8 p-6 rounded-2xl bg-white/70 dark:bg-slate-900/60 backdrop-blur-md border border-slate-200/80 dark:border-slate-800 shadow-sm space-y-5 hover:-translate-y-0.5 hover:shadow-md transition-all duration-200">
              <div className="flex items-center justify-between pb-3 border-b border-slate-200 dark:border-slate-800">
                <div>
                  <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100 flex items-center gap-2">
                    <ShieldAlert className="w-4 h-4 text-violet-600 dark:text-violet-400" />
                    <span>Contradictory Cluster Members</span>
                  </h3>
                  <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                    {active.details_json?.explanation}
                  </p>
                </div>
              </div>

              {/* Side-by-side member cards */}
              <div className="grid sm:grid-cols-2 gap-4">
                {members.map((r, idx) => (
                  <div
                    key={r.id}
                    className="p-4 rounded-xl bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 space-y-2.5 text-xs"
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-mono text-[10px] text-slate-500 dark:text-slate-400">Study #{idx + 1} (ID: {r.id})</span>
                      <span className="text-[10px] uppercase font-mono px-1.5 py-0.5 rounded bg-slate-200 dark:bg-slate-800 text-slate-700 dark:text-slate-300">
                        {r.source}
                      </span>
                    </div>

                    <h4 className="font-semibold text-slate-900 dark:text-slate-100 line-clamp-3 leading-snug">
                      {r.title}
                    </h4>

                    <div className="text-[11px] text-slate-500 dark:text-slate-400 font-mono">
                      {r.authors_json?.[0] || 'Unknown'} ({r.year || 'n.d.'}) — {r.journal || 'Journal'}
                    </div>

                    {/* Decision info */}
                    <div className="pt-2 border-t border-slate-200 dark:border-slate-800 space-y-1.5">
                      <div className="flex items-center justify-between">
                        <span className="text-[10px] text-slate-500 uppercase font-mono">Reviewer Verdict:</span>
                        <HumanDecisionBadge decision={r.current_decision} />
                      </div>
                      {r.current_decision?.reason_text && (
                        <p className="text-[11px] text-amber-800 dark:text-amber-300/90 italic bg-amber-50 dark:bg-amber-950/20 p-2 rounded border border-amber-200 dark:border-amber-900/40">
                          "{r.current_decision.reason_text}"
                        </p>
                      )}
                      <div className="text-[10px] text-slate-500 flex items-center justify-between">
                        <span>Reviewer: {r.current_decision?.reviewer || 'Unknown'}</span>
                        <span>{r.current_decision?.created_at ? new Date(r.current_decision.created_at).toLocaleDateString() : ''}</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>

              {resolutionSuccess && (
                <div className="p-3.5 rounded-xl bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-500/40 text-xs text-emerald-800 dark:text-emerald-300 font-mono">
                  {resolutionSuccess}
                </div>
              )}

              {/* 3 Resolution Actions */}
              {active.status === 'open' ? (
                <div className="pt-3 border-t border-slate-200 dark:border-slate-800 space-y-3.5 text-xs">
                  <h4 className="font-bold text-slate-900 dark:text-slate-100">Arbitration Actions:</h4>

                  {/* Optional/Required Reason Input */}
                  <div>
                    <label className="block text-xs text-slate-700 dark:text-slate-300 mb-1 font-medium">
                      Resolution Note / Rationale {decision === 'exclude' && <span className="text-rose-600 dark:text-rose-400">*required for exclusion</span>}:
                    </label>
                    <textarea
                      value={reason}
                      onChange={e => setReason(e.target.value)}
                      placeholder="Explain the consensus resolution or why studies were separated..."
                      className="w-full p-2.5 bg-white dark:bg-slate-950 border border-slate-300 dark:border-slate-700 rounded-xl text-xs text-slate-900 dark:text-slate-200 focus:outline-none focus:border-violet-500"
                    />
                  </div>

                  <div className="grid sm:grid-cols-3 gap-3">
                    {/* Action (a): Choose Consensus for Whole Group */}
                    <div className="p-3.5 rounded-2xl bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 space-y-2 flex flex-col justify-between">
                      <div>
                        <div className="font-bold text-slate-900 dark:text-slate-100 flex items-center gap-1.5">
                          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400" />
                          <span>(a) Unify Decision</span>
                        </div>
                        <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-1">
                          Apply one consensus verdict to all cluster studies.
                        </p>
                        <select
                          value={decision}
                          onChange={e => setDecision(e.target.value as DecisionType)}
                          className="mt-2 w-full p-1.5 bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg text-xs text-slate-900 dark:text-slate-200"
                        >
                          <option value="include">Unify as INCLUDE</option>
                          <option value="exclude">Unify as EXCLUDE</option>
                          <option value="maybe">Unify as MAYBE</option>
                        </select>
                      </div>
                      <button
                        onClick={handleUnifyGroup}
                        disabled={pending || (decision === 'exclude' && !reason.trim())}
                        className="w-full mt-2 py-2 px-3 rounded-xl bg-teal-600 hover:bg-teal-500 text-white font-semibold text-xs shadow-sm transition disabled:opacity-40"
                      >
                        Apply Unify
                      </button>
                    </div>

                    {/* Action (b): These are not duplicates */}
                    <div className="p-3.5 rounded-2xl bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 space-y-2 flex flex-col justify-between">
                      <div>
                        <div className="font-bold text-slate-900 dark:text-slate-100 flex items-center gap-1.5">
                          <Split className="w-3.5 h-3.5 text-amber-600 dark:text-amber-400" />
                          <span>(b) Split Cluster</span>
                        </div>
                        <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-1">
                          "These are not duplicates." Breaks bridging pair and separates studies.
                        </p>
                      </div>
                      <button
                        onClick={handleSplitNotDuplicates}
                        disabled={pending}
                        className="w-full mt-2 py-2 px-3 rounded-xl bg-amber-600 hover:bg-amber-500 text-white font-bold text-xs shadow-sm transition disabled:opacity-40"
                      >
                        Split & Reject Pair
                      </button>
                    </div>

                    {/* Action (c): Keep as Maybe */}
                    <div className="p-3.5 rounded-2xl bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 space-y-2 flex flex-col justify-between">
                      <div>
                        <div className="font-bold text-slate-900 dark:text-slate-100 flex items-center gap-1.5">
                          <HelpCircle className="w-3.5 h-3.5 text-slate-400" />
                          <span>(c) Defer as Maybe</span>
                        </div>
                        <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-1">
                          Quarantine both as Maybe pending full-text retrieval.
                        </p>
                      </div>
                      <button
                        onClick={handleKeepMaybe}
                        disabled={pending}
                        className="w-full mt-2 py-2 px-3 rounded-xl bg-slate-200 dark:bg-slate-800 hover:bg-slate-300 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300 font-semibold text-xs border border-slate-300 dark:border-slate-700 transition disabled:opacity-40"
                      >
                        Keep as Maybe
                      </button>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="p-3.5 rounded-xl bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 text-xs text-slate-700 dark:text-slate-300 flex items-center justify-between">
                  <span className="text-emerald-700 dark:text-emerald-400 font-semibold">Conflict Resolved</span>
                  <span className="text-[11px] text-slate-500 font-mono">
                    Resolved by {active.reviewer || 'Reviewer'} · {active.resolved_at ? new Date(active.resolved_at).toLocaleString() : ''}
                  </span>
                </div>
              )}
            </div>
          </div>
        )
      )}
    </div>
  );
}
