import { useState } from 'react';
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
  const [conflicts] = useData(['conflicts'], () => api.getConflicts(reviewId));
  const active = conflicts.find(c => c.id === selectedId) || conflicts[0];
  const [members] = useData(['conflict-members', active?.id], () => active ? Promise.all((active.records || []).map(r => api.getRecord(r.id))) : Promise.resolve([]));
  const resolve = useAction(async () => {
    if (!active || pending) return;
    try {
      setPending(true);
      await api.resolveConflict(active.id, { resolution: 'unify', decision, reason: reason.trim() || undefined, reviewer: getActiveReviewer() });
      setReason('');
    } finally { setPending(false); }
  });
  return <div className="max-w-6xl mx-auto space-y-6">
    <div className="p-5 bg-slate-900 border border-slate-800 rounded-xl space-y-2">
      <h2 className="text-xl font-bold">Group Decision Conflicts Resolution</h2>
      <p className="text-sm text-slate-400">{conflicts.filter(c => c.status === 'open').length} open conflicts. Affected groups stay quarantined from CSV until resolved by a reviewer.</p>
    </div>
    {!conflicts.length && <p className="p-6 text-slate-400">No conflicts recorded. Continue reviewing duplicate pairs and screening studies.</p>}
    {active && <div className="grid lg:grid-cols-3 gap-6">
      <div className="space-y-2">{conflicts.map(c => <button key={c.id} className={`w-full text-left p-3 rounded-xl border ${active.id === c.id ? 'border-brand-500 bg-slate-800' : 'border-slate-800 bg-slate-900'}`}
        onClick={() => { setSelectedId(c.id); setReason(''); }}><span className="block text-xs text-slate-400">{c.status}</span>{c.type.replace(/_/g, ' ')}</button>)}</div>
      <div className="lg:col-span-2 p-5 bg-slate-900 border border-slate-800 rounded-xl space-y-5">
        <p className="text-sm">{active.details_json?.explanation}</p>
        {(members || []).map(r => <div key={r.id} className="space-y-3 p-4 border border-slate-800 rounded-lg">
          <h3 className="font-bold">{r.title}</h3>
          {(r.decision_history || []).filter(d => !d.superseded_by_id).map(d => <div key={d.id}><HumanDecisionBadge decision={d} /><p className="mt-2 text-xs text-slate-400">{d.reason_text || d.note}</p></div>)}
        </div>)}
        {active.status === 'open' && (active.type === 'pair_override_bypassed' ? <p className="text-amber-300 text-sm">This conflict involves duplicate grouping. Review and change the relevant pair decision in Duplicates before applying screening consensus.</p> : <form className="space-y-3" onSubmit={e => { e.preventDefault(); void resolve(); }}>
          <label className="block text-sm">Consensus decision<select className="block mt-1 p-2 bg-slate-950 rounded border border-slate-700" value={decision} onChange={e => setDecision(e.target.value as DecisionType)}>
            <option value="include">Include</option><option value="exclude">Exclude</option><option value="maybe">Maybe</option>
          </select></label>
          <label className="block text-sm">{decision === 'exclude' ? 'Exclusion reason (required)' : 'Consensus notes'}<textarea required={decision === 'exclude'} value={reason} onChange={e => setReason(e.target.value)} className="block mt-1 w-full p-2 bg-slate-950 rounded border border-slate-700" /></label>
          <button disabled={pending || (decision === 'exclude' && !reason.trim())} className="px-4 py-2 bg-brand-600 rounded disabled:opacity-40">{pending ? 'Resolving…' : 'Apply consensus'}</button>
        </form>)}
        {active.status === 'resolved' && <p className="text-sm text-emerald-300">Resolved by {active.reviewer} · {active.resolved_at && new Date(active.resolved_at).toLocaleString()}</p>}
      </div>
    </div>}
  </div>;
}
