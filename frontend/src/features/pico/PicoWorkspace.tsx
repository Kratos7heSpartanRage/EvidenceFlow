import { CheckCircle2, Edit3, Tag, XCircle } from 'lucide-react';
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
    const [included, maybe] = await Promise.all([
      api.getRecords(reviewId, { decision: 'include' }),
      api.getRecords(reviewId, { decision: 'maybe' })
    ]);
    return [...new Map([...included.items, ...maybe.items].map(r => [r.id, r])).values()];
  });

  const summary = records.find(r => r.id === selectedId) || records[0];
  const [record, setRecord] = useData(['record', summary?.id], () =>
    summary ? api.getRecord(summary.id) : Promise.resolve(null)
  );
  const annotations = record?.pico_annotations || [];

  const update = useAction(async (op: 'confirm' | 'correct' | 'reject', annotation: PicoAnnotation) => {
    if (!record || pending) return;
    if (op === 'correct' && !record.abstract?.includes(text.trim())) {
      throw new Error('Copy the corrected wording exactly from the abstract.');
    }
    try {
      setPending(true);
      await api.updatePico(record.id, {
        op,
        annotation: op === 'correct' ? { ...annotation, text: text.trim() } : annotation,
        reviewer: getActiveReviewer()
      });
      setRecord(await api.getRecord(record.id));
      setEditing(null);
    } finally {
      setPending(false);
    }
  });

  return (
    <div className="max-w-6xl mx-auto space-y-5 py-2">
      {/* Top Banner */}
      <div className="p-5 rounded-2xl bg-white/70 dark:bg-slate-900/60 backdrop-blur-md border border-slate-200/80 dark:border-slate-800/80 shadow-sm space-y-2 hover:-translate-y-0.5 hover:shadow-md transition-all duration-200">
        <div className="flex items-center gap-2">
          <span className="px-2.5 py-0.5 rounded-md text-[11px] font-bold font-mono uppercase bg-teal-500/10 text-teal-700 dark:text-teal-300 border border-teal-500/30">
            Step 6 • Gate 4
          </span>
          <span className="text-xs text-slate-500 dark:text-slate-400 font-mono">PICO Element Span Extraction</span>
        </div>
        <h2 className="text-xl font-bold text-slate-900 dark:text-slate-100">PICO Spans Annotator</h2>
        <p className="text-xs text-slate-500 dark:text-slate-400 leading-relaxed max-w-3xl">
          Confirm, correct, or reject extracted spans. Human edits preserve the original machine evidence and provenance history.
        </p>
      </div>

      {!records.length && (
        <div className="p-12 text-center rounded-2xl bg-white/70 dark:bg-slate-900/60 border border-slate-200/80 dark:border-slate-800 text-slate-500 dark:text-slate-400 text-sm">
          No included or Maybe studies yet. Screen records first in the Screening Queue to review their PICO evidence.
        </div>
      )}

      {record && (
        <div className="grid lg:grid-cols-12 gap-5">
          {/* Studies List */}
          <div className="lg:col-span-4 space-y-2 max-h-[700px] overflow-y-auto">
            {records.map(r => (
              <button
                key={r.id}
                className={`w-full text-left p-3.5 rounded-2xl border text-xs transition-all duration-150 space-y-1.5 hover:-translate-y-0.5 hover:shadow-md ${
                  record.id === r.id
                    ? 'border-teal-500/80 bg-white dark:bg-slate-800 shadow-md'
                    : 'border-slate-200/80 dark:border-slate-800 bg-white/70 dark:bg-slate-900/60 hover:bg-slate-50 dark:hover:bg-slate-800/60'
                }`}
                onClick={() => {
                  setSelectedId(r.id);
                  setEditing(null);
                }}
              >
                <div className="font-semibold text-slate-900 dark:text-slate-100 line-clamp-2 leading-snug">{r.title}</div>
                <div className="flex items-center justify-between text-[11px] text-slate-500 dark:text-slate-400 font-mono">
                  <span>Rec #{r.id}</span>
                  <span className="capitalize px-1.5 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300">
                    {r.current_decision?.decision || 'Unscreened'}
                  </span>
                </div>
              </button>
            ))}
          </div>

          {/* Right: Abstract & Span Annotations */}
          <div className="lg:col-span-8 p-6 rounded-2xl bg-white/70 dark:bg-slate-900/60 backdrop-blur-md border border-slate-200/80 dark:border-slate-800 shadow-sm space-y-5 hover:-translate-y-0.5 hover:shadow-md transition-all duration-200">
            <div>
              <span className="text-[10px] font-mono text-slate-400 dark:text-slate-500 uppercase">Selected Study</span>
              <h3 className="text-base font-bold text-slate-900 dark:text-slate-100 mt-0.5 leading-snug">{record.title}</h3>
            </div>

            {record.source === 'pubmed' && <NcbiDisclaimer />}

            <div className="space-y-1.5">
              <span className="text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider block font-mono">
                Abstract Text
              </span>
              <div className="p-4 rounded-xl bg-slate-50 dark:bg-slate-950/80 border border-slate-200 dark:border-slate-800 text-slate-800 dark:text-slate-200 text-xs leading-relaxed max-h-[260px] overflow-y-auto font-sans">
                {record.abstract || 'No abstract supplied by the literature source.'}
              </div>
            </div>

            <div className="space-y-3 pt-2 border-t border-slate-200 dark:border-slate-800">
              <h4 className="text-xs font-bold text-slate-900 dark:text-slate-100 uppercase tracking-wider font-mono">
                Extracted PICO Evidence Spans ({annotations.length})
              </h4>

              {!annotations.length && (
                <p className="text-xs text-slate-500 dark:text-slate-400 italic">No automated PICO spans were detected for this abstract.</p>
              )}

              {annotations.map(ann => (
                <div
                  key={ann.id}
                  className="p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50/80 dark:bg-slate-950/60 space-y-2 text-xs"
                >
                  <div className="flex flex-wrap gap-2 items-center justify-between">
                    <div className="flex items-center gap-2">
                      <PicoBadge label={ann.label} />
                      <span className="text-[11px] text-slate-500 dark:text-slate-400 font-mono">
                        Origin: {ann.origin} • Status: <strong className="uppercase">{ann.status}</strong>
                        {ann.reviewer ? ` (${ann.reviewer})` : ''}
                      </span>
                    </div>
                  </div>

                  <p className="text-xs font-semibold text-slate-900 dark:text-slate-100 italic bg-white dark:bg-slate-900 p-2.5 rounded-lg border border-slate-200 dark:border-slate-800">
                    "{ann.text}"
                  </p>

                  <div className="flex items-center gap-3 pt-1 text-xs">
                    <button
                      disabled={pending || ann.status === 'confirmed'}
                      className="flex items-center gap-1 text-emerald-700 dark:text-emerald-400 font-semibold hover:underline disabled:opacity-40"
                      onClick={() => update('confirm', ann)}
                    >
                      <CheckCircle2 className="w-3.5 h-3.5" />
                      <span>Confirm</span>
                    </button>
                    <button
                      disabled={pending}
                      className="flex items-center gap-1 text-teal-700 dark:text-teal-400 font-semibold hover:underline disabled:opacity-40"
                      onClick={() => {
                        setEditing(ann);
                        setText(ann.text);
                      }}
                    >
                      <Edit3 className="w-3.5 h-3.5" />
                      <span>Correct text</span>
                    </button>
                    <button
                      disabled={pending}
                      className="flex items-center gap-1 text-rose-700 dark:text-rose-400 font-semibold hover:underline disabled:opacity-40"
                      onClick={() => update('reject', ann)}
                    >
                      <XCircle className="w-3.5 h-3.5" />
                      <span>Reject</span>
                    </button>
                  </div>

                  {editing?.id === ann.id && (
                    <form
                      className="space-y-2 pt-2 border-t border-slate-200 dark:border-slate-800"
                      onSubmit={e => {
                        e.preventDefault();
                        void update('correct', ann);
                      }}
                    >
                      <label className="text-xs font-semibold block text-slate-700 dark:text-slate-300">
                        Exact wording from abstract:
                        <textarea
                          required
                          value={text}
                          onChange={e => setText(e.target.value)}
                          className="block mt-1 p-2 w-full bg-white dark:bg-slate-950 border border-slate-300 dark:border-slate-700 rounded-lg text-xs text-slate-900 dark:text-slate-200"
                        />
                      </label>
                      <div className="flex gap-2">
                        <button
                          disabled={pending || !text.trim()}
                          className="px-3 py-1.5 rounded-lg bg-teal-600 hover:bg-teal-500 text-white text-xs font-semibold disabled:opacity-40 shadow-sm"
                        >
                          Save correction
                        </button>
                        <button
                          type="button"
                          className="px-3 py-1.5 text-xs text-slate-500 dark:text-slate-400 hover:text-slate-800"
                          onClick={() => setEditing(null)}
                        >
                          Cancel
                        </button>
                      </div>
                    </form>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
