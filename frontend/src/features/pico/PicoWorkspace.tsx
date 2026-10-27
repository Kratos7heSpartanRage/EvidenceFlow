import React, { useState, useEffect } from 'react';
import { api, getActiveReviewer } from '../../lib/api';
import { LiteratureRecord, PicoAnnotation, PicoLabel } from '../../types/api';
import { PicoBadge } from '../../components/ui/Badge';
import { Tag, Check, Edit3, Trash2, Plus, Sparkles, BookOpen, AlertCircle, HelpCircle } from 'lucide-react';

export function PicoWorkspace() {
  const [includedRecords, setIncludedRecords] = useState<LiteratureRecord[]>([]);
  const [selectedRecordId, setSelectedRecordId] = useState<number | null>(null);
  const [annotations, setAnnotations] = useState<PicoAnnotation[]>([]);
  const [loading, setLoading] = useState(true);

  // Edit/Add modal state
  const [editingAnn, setEditingAnn] = useState<PicoAnnotation | null>(null);
  const [editLabel, setEditLabel] = useState<PicoLabel>('P');
  const [editText, setEditText] = useState('');
  const [isAddMode, setIsAddMode] = useState(false);

  const loadRecords = async () => {
    try {
      setLoading(true);
      // Fetch representatives that are Included or Maybe
      const res = await api.getRecords(1, { decision: 'include', show_hidden: false });
      const maybeRes = await api.getRecords(1, { decision: 'maybe', show_hidden: false });
      const combined = [...res.items, ...maybeRes.items];
      setIncludedRecords(combined);
      if (combined.length > 0 && (!selectedRecordId || !combined.some(r => r.id === selectedRecordId))) {
        setSelectedRecordId(combined[0].id);
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadRecords();
  }, []);

  const activeRecord = includedRecords.find(r => r.id === selectedRecordId) || includedRecords[0];

  const loadAnnotations = async (recordId: number) => {
    const data = await api.getPicoAnnotations(recordId);
    setAnnotations(data);
  };

  useEffect(() => {
    if (activeRecord) {
      loadAnnotations(activeRecord.id);
    }
  }, [activeRecord?.id]);

  const handleConfirmAnnotation = async (ann: PicoAnnotation) => {
    if (!activeRecord) return;
    await api.updatePico(activeRecord.id, {
      op: 'confirm',
      annotation: ann,
      reviewer: getActiveReviewer()
    });
    loadAnnotations(activeRecord.id);
  };

  const handleRejectAnnotation = async (ann: PicoAnnotation) => {
    if (!activeRecord) return;
    await api.updatePico(activeRecord.id, {
      op: 'reject',
      annotation: ann,
      reviewer: getActiveReviewer()
    });
    loadAnnotations(activeRecord.id);
  };

  const handleSaveEdit = async () => {
    if (!activeRecord || !editText.trim()) return;

    if (isAddMode) {
      await api.updatePico(activeRecord.id, {
        op: 'add',
        annotation: {
          label: editLabel,
          text: editText.trim(),
          start_char: 0,
          end_char: editText.length
        },
        reviewer: getActiveReviewer()
      });
    } else if (editingAnn) {
      await api.updatePico(activeRecord.id, {
        op: 'correct',
        annotation: {
          ...editingAnn,
          label: editLabel,
          text: editText.trim()
        },
        reviewer: getActiveReviewer()
      });
    }

    setEditingAnn(null);
    setIsAddMode(false);
    setEditText('');
    loadAnnotations(activeRecord.id);
  };

  const hasComparator = annotations.some(a => a.label === 'C' && a.status !== 'rejected');

  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      {/* Top Banner */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 p-5 rounded-xl bg-slate-900/60 border border-slate-800 shadow-xl">
        <div>
          <div className="flex items-center gap-2">
            <span className="px-2 py-0.5 rounded text-[11px] font-bold font-mono uppercase bg-brand-500/20 text-brand-300 border border-brand-500/30">
              Step 6: PICO Extraction
            </span>
            <span className="text-xs text-slate-400 font-mono">Population ? Intervention ? Comparator ? Outcome</span>
          </div>
          <h2 className="text-xl font-bold text-slate-100 mt-1">PICO Spans Annotator</h2>
          <p className="text-xs text-slate-400">
            Automated entity detection with human-in-the-loop span verification. All changes supersede machine suggestions.
          </p>
        </div>

        {/* Legend */}
        <div className="flex items-center gap-2 p-1.5 bg-slate-950 rounded-lg border border-slate-800 text-xs">
          <PicoBadge label="P" />
          <PicoBadge label="I" />
          <PicoBadge label="C" />
          <PicoBadge label="O" />
        </div>
      </div>

      {includedRecords.length === 0 ? (
        <div className="p-12 text-center rounded-xl bg-slate-900/40 border border-slate-800 text-slate-400 text-sm">
          No Included studies available. Screen and include studies in Step 5 before tagging PICO.
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Record Selector Sidebar */}
          <div className="lg:col-span-4 space-y-2 max-h-[700px] overflow-y-auto pr-1">
            <div className="text-[11px] font-bold text-slate-400 uppercase tracking-wider px-1">
              Included Studies ({includedRecords.length})
            </div>
            {includedRecords.map(r => {
              const isSelected = activeRecord?.id === r.id;
              return (
                <button
                  key={r.id}
                  onClick={() => setSelectedRecordId(r.id)}
                  className={`w-full text-left p-3.5 rounded-xl border text-xs transition-all space-y-1.5 ${
                    isSelected
                      ? 'bg-slate-800/90 border-brand-500/60 shadow-lg'
                      : 'bg-slate-900/60 border-slate-800 hover:bg-slate-800/40'
                  }`}
                >
                  <div className="flex items-center justify-between text-[10px] font-mono text-slate-400">
                    <span>Rec #{r.id}</span>
                    <span className="text-emerald-400 font-bold uppercase">{r.current_decision?.decision}</span>
                  </div>
                  <h4 className="font-semibold text-slate-200 line-clamp-2 leading-snug">
                    {r.title}
                  </h4>
                  <div className="text-[11px] text-slate-400 font-mono">
                    {r.first_author_norm} ({r.year})
                  </div>
                </button>
              );
            })}
          </div>

          {/* Active Record Abstract & PICO Tags Viewer */}
          <div className="lg:col-span-8 p-6 rounded-xl bg-slate-900/60 border border-slate-800 shadow-lg space-y-5">
            {/* Header */}
            <div className="space-y-2 pb-4 border-b border-slate-800">
              <div className="flex items-center justify-between text-[11px] text-slate-400 font-mono">
                <span>Record #{activeRecord.id} ? {activeRecord.journal} ({activeRecord.year})</span>
                <span className="text-slate-300">Reviewer: <strong className="text-brand-400">{getActiveReviewer()}</strong></span>
              </div>
              <h3 className="text-sm font-bold text-slate-100">{activeRecord.title}</h3>
            </div>

            {/* Comparator Alert if missing */}
            {!hasComparator && (
              <div className="flex items-start gap-3 p-3.5 rounded-lg bg-amber-950/30 border border-amber-800/40 text-amber-200 text-xs">
                <AlertCircle className="w-4 h-4 text-amber-400 mt-0.5 flex-shrink-0" />
                <div className="space-y-0.5">
                  <div className="font-bold text-amber-300">Comparator Span: Unknown / Not Detected</div>
                  <p className="text-amber-200/90 leading-relaxed">
                    No explicit comparator was recognized by automated pattern rules. If this is a single-arm study or unstated control, keep as unknown or manually tag a span below.
                  </p>
                </div>
              </div>
            )}

            {/* Abstract Viewer with Highlights */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">
                  Abstract & Extracted Evidence Spans
                </span>
                <button
                  onClick={() => {
                    setIsAddMode(true);
                    setEditingAnn(null);
                    setEditText('');
                    setEditLabel('P');
                  }}
                  className="flex items-center gap-1 text-xs text-brand-400 hover:text-brand-300 font-semibold"
                >
                  <Plus className="w-3.5 h-3.5" />
                  <span>Add Manual Tag</span>
                </button>
              </div>

              <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 text-slate-200 text-xs leading-loose font-sans select-text">
                {activeRecord.abstract}
              </div>
            </div>

            {/* Extracted Tags Cards List */}
            <div className="space-y-3">
              <span className="text-xs font-bold text-slate-400 uppercase tracking-wider block">
                PICO Tag Annotations ({annotations.length})
              </span>

              <div className="grid gap-2.5">
                {annotations.map(ann => {
                  const isHuman = ann.origin === 'human';
                  return (
                    <div
                      key={ann.id}
                      className="flex items-start justify-between gap-3 p-3.5 rounded-lg bg-slate-950/70 border border-slate-800 text-xs transition hover:border-slate-700"
                    >
                      <div className="space-y-1.5 flex-1">
                        <div className="flex items-center gap-2">
                          <PicoBadge label={ann.label} />
                          <span
                            className={`px-1.5 py-0.2 rounded text-[10px] font-mono uppercase font-semibold ${
                              isHuman ? 'bg-brand-500/20 text-brand-300' : 'bg-slate-800 text-slate-400'
                            }`}
                          >
                            {ann.origin} ({ann.status})
                          </span>
                          {ann.reviewer && (
                            <span className="text-[10px] text-slate-500">by {ann.reviewer}</span>
                          )}
                        </div>

                        <div className="text-slate-100 font-medium italic text-xs leading-relaxed">
                          "{ann.text}"
                        </div>
                      </div>

                      {/* Actions */}
                      <div className="flex items-center gap-1 flex-shrink-0">
                        {ann.status !== 'confirmed' && (
                          <button
                            onClick={() => handleConfirmAnnotation(ann)}
                            className="p-1.5 rounded hover:bg-emerald-950/50 text-slate-400 hover:text-emerald-400 transition"
                            title="Confirm this span"
                          >
                            <Check className="w-4 h-4" />
                          </button>
                        )}
                        <button
                          onClick={() => {
                            setEditingAnn(ann);
                            setEditLabel(ann.label);
                            setEditText(ann.text);
                            setIsAddMode(false);
                          }}
                          className="p-1.5 rounded hover:bg-slate-800 text-slate-400 hover:text-slate-200 transition"
                          title="Edit / Correct span"
                        >
                          <Edit3 className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => handleRejectAnnotation(ann)}
                          className="p-1.5 rounded hover:bg-rose-950/50 text-slate-400 hover:text-rose-400 transition"
                          title="Reject / Remove span"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Modal for Edit / Add Tag */}
            {(editingAnn || isAddMode) && (
              <div className="p-4 rounded-xl bg-slate-950 border border-brand-500/50 space-y-3">
                <div className="flex items-center justify-between text-xs font-bold text-slate-100">
                  <span>{isAddMode ? 'Add PICO Tag' : 'Edit / Correct PICO Annotation'}</span>
                  <button
                    onClick={() => {
                      setEditingAnn(null);
                      setIsAddMode(false);
                    }}
                    className="text-slate-400 hover:text-slate-200"
                  >
                    ?
                  </button>
                </div>

                <div className="grid grid-cols-4 gap-2">
                  {(['P', 'I', 'C', 'O'] as PicoLabel[]).map(lbl => (
                    <button
                      key={lbl}
                      type="button"
                      onClick={() => setEditLabel(lbl)}
                      className={`p-2 rounded-lg font-mono text-xs font-bold border transition ${
                        editLabel === lbl
                          ? 'bg-brand-600 text-white border-brand-500 shadow'
                          : 'bg-slate-900 text-slate-400 border-slate-800 hover:bg-slate-800'
                      }`}
                    >
                      {lbl}
                    </button>
                  ))}
                </div>

                <div>
                  <label className="text-[11px] text-slate-400 block mb-1">Tag Span Text:</label>
                  <textarea
                    value={editText}
                    onChange={e => setEditText(e.target.value)}
                    className="w-full px-3 py-2 bg-slate-900 border border-slate-800 rounded-lg text-xs text-slate-100 focus:outline-none focus:border-brand-500 min-h-[50px]"
                    placeholder="Enter span exact wording..."
                  />
                </div>

                <div className="flex justify-end gap-2">
                  <button
                    type="button"
                    onClick={() => {
                      setEditingAnn(null);
                      setIsAddMode(false);
                    }}
                    className="px-3 py-1.5 rounded-lg text-xs text-slate-400 hover:text-slate-200"
                  >
                    Cancel
                  </button>
                  <button
                    type="button"
                    onClick={handleSaveEdit}
                    className="px-4 py-1.5 rounded-lg bg-brand-600 hover:bg-brand-500 text-white text-xs font-semibold shadow"
                  >
                    Save Annotation
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
