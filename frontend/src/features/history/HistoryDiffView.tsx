import { useState } from 'react';
import { Modal } from '../../components/ui/Modal';
import { api } from '../../lib/api';
import { useAction, useData, useWorkspace } from '../../lib/workspace';
import type { EntityId } from '../../types/api';

export function HistoryDiffView({ onNavigateToConflicts }: { onNavigateToConflicts?: () => void; }) {
  const { reviewId } = useWorkspace();
  const [queries] = useData(['queries'], () => api.getQueries(reviewId));
  const [fromId, setFromId] = useState<EntityId>('');
  const [toId, setToId] = useState<EntityId>('');
  const [restoreId, setRestoreId] = useState<EntityId>('');
  const effectiveFromId = fromId || queries[0]?.id || '';
  const effectiveToId = toId || queries[queries.length - 1]?.id || '';
  const effectiveRestoreId = restoreId || queries[0]?.id || '';
  const [confirm, setConfirm] = useState(false);
  const [pending, setPending] = useState(false);
  const [message, setMessage] = useState('');
  const [diff] = useData(['diff', effectiveFromId, effectiveToId], () => effectiveFromId && effectiveToId && effectiveFromId !== effectiveToId ? api.getDiff(effectiveToId, effectiveFromId) : Promise.resolve(null));
  const restore = queries.find(q => q.id === effectiveRestoreId);
  const revert = useAction(async () => {
    if (!restore || pending) return;
    try {
      setPending(true);
      const result = await api.revertQuery(restore.id);
      setMessage(`Restored v${restore.version_no}: ${result.restored_records_count ?? 0} records visible, ${result.hidden_records_count ?? 0} hidden. No source requests were made.`);
      setConfirm(false);
    } finally { setPending(false); }
  });
  const options = queries.map(q => <option key={q.id} value={q.id}>v{q.version_no} — {q.label}</option>);
  return <div className="max-w-6xl mx-auto space-y-6">
    <div className="p-5 bg-slate-900 border border-slate-800 rounded-xl space-y-2">
      <h2 className="text-xl font-bold">Query Evolution & Decision Preservation</h2>
      <p className="text-sm text-slate-400">Compare stored query result sets and restore a query's saved grouping. Records and human decision history are preserved.</p>
    </div>
    {!queries.length ? <p className="p-6 text-slate-400">Create and import a query in Search before comparing or restoring versions.</p> : <>
      <div className="flex flex-wrap gap-4">
        <label>From version<select className="block p-2 mt-2 bg-slate-900 rounded border border-slate-700" value={effectiveFromId} onChange={e => setFromId(e.target.value)}>{options}</select></label>
        <label>To version<select className="block p-2 mt-2 bg-slate-900 rounded border border-slate-700" value={effectiveToId} onChange={e => setToId(e.target.value)}>{options}</select></label>
      </div>
      {diff ? <div className="grid sm:grid-cols-3 gap-4">{[
        ['New records', diff.records_added], ['Retained records', diff.already_present],
        ['Dropped records', diff.records_removed], ['Screened records retained', diff.decisions_preserved],
        ['Potential conflicts', diff.conflicts_opened],
      ].map(([label, count]) => <div key={label} className="p-4 bg-slate-900 border border-slate-800 rounded-xl"><p className="text-xs text-slate-400">{label}</p><p className="text-2xl font-bold mt-2">{count}</p></div>)}
        <button className="p-4 rounded-xl border border-slate-700 text-brand-300" onClick={onNavigateToConflicts}>Review conflicts</button>
      </div> : <p className="text-slate-400">Select two different versions to compare their stored results.</p>}
      <div className="p-5 bg-slate-900 border border-slate-800 rounded-xl space-y-3">
        <label className="block">Restore saved version<select className="block p-2 mt-2 bg-slate-950 rounded border border-slate-700" value={effectiveRestoreId} onChange={e => setRestoreId(e.target.value)}>{options}</select></label>
        <p className="text-sm text-slate-400">Restore a version after its import completes. Records outside its snapshot become hidden.</p>
        <button disabled={!restore || restore.imported_count == null} className="px-4 py-2 rounded bg-brand-600 disabled:opacity-40" onClick={() => setConfirm(true)}>Restore v{restore?.version_no}</button>
      </div>
    </>}
    {message && <p role="status" className="text-emerald-300">{message}</p>}
    <Modal isOpen={confirm} onClose={() => setConfirm(false)} title={`Restore v${restore?.version_no}?`} description="Zero external API requests will be performed. This changes which stored records are visible.">
      <button disabled={pending} className="p-3 bg-brand-600 rounded disabled:opacity-40" onClick={revert}>{pending ? 'Restoring…' : 'Execute restore'}</button>
    </Modal>
  </div>;
}
