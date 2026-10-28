import { useState } from 'react';
import { PicoBadge } from '../../components/ui/Badge';
import { NcbiDisclaimer } from '../../components/ui/NcbiDisclaimer';
import { api, getActiveReviewer } from '../../lib/api';
import { useAction, useData, useWorkspace } from '../../lib/workspace';
import type { EntityId, PicoAnnotation } from '../../types/api';

export function PicoWorkspace() {
  const { reviewId } = useWorkspace();
  const [selectedId, setSelectedId] = useState<EntityId | null>(null);
  const [editing, setEditing] = useState<PicoAnnotation | null>(null);
  const [text, setText] = useState('');
  const [pending, setPending] = useState(false);
  const [records] = useData(['pico-records'], async () => {
    const [included, maybe] = await Promise.all([api.getRecords(reviewId, { decision: 'include' }), api.getRecords(reviewId, { decision: 'maybe' })]);
    return [...new Map([...included.items, ...maybe.items].map(r => [r.id, r])).values()];
  });
  const summary = records.find(r => r.id === selectedId) || records[0];
  const [record, setRecord] = useData(['record', summary?.id], () => summary ? api.getRecord(summary.id) : Promise.resolve(null));
  const annotations = record?.pico_annotations || [];
  const update = useAction(async (op: 'confirm' | 'correct' | 'reject', annotation: PicoAnnotation) => {
    if (!record || pending) return;
    if (op === 'correct' && !record.abstract?.includes(text.trim())) throw new Error('Copy the corrected wording exactly from the abstract.');
    try {
      setPending(true);
      await api.updatePico(record.id, { op, annotation: op === 'correct' ? { ...annotation, text: text.trim() } : annotation, reviewer: getActiveReviewer() });
      setRecord(await api.getRecord(record.id)); setEditing(null);
    } finally { setPending(false); }
  });
  return <div className="max-w-6xl mx-auto space-y-6">
    <div className="p-5 bg-slate-900 border border-slate-800 rounded-xl space-y-2">
      <h2 className="text-xl font-bold">PICO Spans Annotator</h2>
      <p className="text-sm text-slate-400">Confirm, correct or reject extracted spans. Human edits preserve the original machine evidence.</p>
    </div>
    {!records.length && <p className="p-6 text-slate-400">No included or Maybe studies yet. Screen records first to review their PICO evidence.</p>}
    {record && <div className="grid lg:grid-cols-3 gap-6">
      <div className="space-y-2">{records.map(r => <button key={r.id} className={`w-full text-left p-3 rounded-xl border ${record.id === r.id ? 'border-brand-500 bg-slate-800' : 'border-slate-800 bg-slate-900'}`}
        onClick={() => { setSelectedId(r.id); setEditing(null); }}>{r.title}<span className="block text-xs text-slate-400 mt-1">{r.current_decision?.decision}</span></button>)}</div>
      <div className="lg:col-span-2 p-5 bg-slate-900 border border-slate-800 rounded-xl space-y-5">
        <h3 className="font-bold">{record.title}</h3>
        {record.source === 'pubmed' && <NcbiDisclaimer />}
        <p className="text-sm text-slate-300 whitespace-pre-wrap leading-relaxed">{record.abstract || 'No abstract supplied by the source.'}</p>
        {!annotations.length && <p className="text-sm text-slate-400">No PICO spans were detected in this abstract.</p>}
        {annotations.map(ann => <div key={ann.id} className="p-4 border border-slate-800 rounded-lg space-y-3">
          <div className="flex flex-wrap gap-2 items-center"><PicoBadge label={ann.label} /><span className="text-xs text-slate-400">{ann.origin} · {ann.status}{ann.reviewer ? ` · ${ann.reviewer}` : ''}</span></div>
          <p className="text-sm">“{ann.text}”</p>
          <div className="flex gap-3 text-xs">
            <button disabled={pending || ann.status === 'confirmed'} className="text-emerald-400 disabled:opacity-40" onClick={() => update('confirm', ann)}>Confirm</button>
            <button disabled={pending} className="text-brand-300" onClick={() => { setEditing(ann); setText(ann.text); }}>Correct text</button>
            <button disabled={pending} className="text-rose-300" onClick={() => update('reject', ann)}>Reject</button>
          </div>
          {editing?.id === ann.id && <form className="space-y-2" onSubmit={e => { e.preventDefault(); void update('correct', ann); }}>
            <label className="text-xs block">Exact wording from abstract<textarea required value={text} onChange={e => setText(e.target.value)} className="block mt-1 p-2 w-full bg-slate-950 border border-slate-700 rounded" /></label>
            <button disabled={pending || !text.trim()} className="px-3 py-2 rounded bg-brand-600 text-xs disabled:opacity-40">Save correction</button>
            <button type="button" className="px-3 text-xs" onClick={() => setEditing(null)}>Cancel</button>
          </form>}
        </div>)}
      </div>
    </div>}
  </div>;
}
