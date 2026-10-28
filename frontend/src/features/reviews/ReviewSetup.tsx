import {
  ArrowRight,
  Edit2,
  FileText,
  Plus,
  Save,
  ShieldCheck,
  ToggleLeft,
  ToggleRight,
  X
} from 'lucide-react';
import React, { useEffect, useState } from 'react';
import { api } from '../../lib/api';
import { useAction, useData, useWorkspace } from '../../lib/workspace';
import type { EntityId } from '../../types/api';
import { Criterion } from '../../types/api';

interface ReviewSetupProps {
  onProceedToSearch?: () => void;
}

export function ReviewSetup({ onProceedToSearch }: ReviewSetupProps) {
  const { reviewId } = useWorkspace();
  const [review, setReview] = useData(['review'], () => api.getReview(reviewId));
  const [criteriaVer, setCriteriaVer] = useData(['criteria'], () => api.getCriteria(reviewId));
  const [activeTab, setActiveTab] = useState<'pico' | 'criteria'>('pico');

  // Edit protocol modal/form
  const [isEditingPico, setIsEditingPico] = useState(false);
  const [picoForm, setPicoForm] = useState({
    title: review?.title || '',
    question: review?.question || '',
    population: review?.population || '',
    intervention: review?.intervention || '',
    comparator: review?.comparator || '',
    outcome: review?.outcome || ''
  });

  useEffect(() => {
    if (review) {
      setPicoForm({
        title: review.title || '',
        question: review.question || '',
        population: review.population || '',
        intervention: review.intervention || '',
        comparator: review.comparator || '',
        outcome: review.outcome || ''
      });
    }
  }, [review]);

  // Add criterion modal
  const [showAddModal, setShowAddModal] = useState(false);
  const [newCrit, setNewCrit] = useState({
    kind: 'exclude' as 'include' | 'exclude',
    code: '',
    label: '',
    reason: '',
    detector_rule: ''
  });

  const handleSavePico = useAction(async () => {
    if (!review) return;
    const updated = await api.updateReview(review.id, picoForm);
    setReview(updated);
    setIsEditingPico(false);
  });

  const handleToggleCriterion = useAction(async (criterionId: EntityId) => {
    if (!criteriaVer) return;
    const updatedCriteria = criteriaVer.criteria.map(c =>
      c.id === criterionId ? { ...c, is_active: !c.is_active } : c
    );
    const newVer = await api.updateCriteria(criteriaVer.review_id, updatedCriteria);
    setCriteriaVer(newVer);
  });

  const handleAddCriterion = useAction(async (e: React.FormEvent) => {
    e.preventDefault();
    if (!criteriaVer || !newCrit.label || !newCrit.reason) return;

    const addedCriterion: Criterion = {
      id: 0,
      criteria_version_id: criteriaVer.id,
      kind: newCrit.kind,
      code: newCrit.code.trim().toLowerCase().replace(/\s+/g, '_') || 'custom_crit',
      label: newCrit.label,
      reason: newCrit.reason,
      detector: newCrit.detector_rule.trim() ? 'rule' : 'manual_only',
      detector_rule: newCrit.detector_rule.trim() || null,
      params_json: {},
      is_active: true
    };

    const newVer = await api.updateCriteria(criteriaVer.review_id, [...criteriaVer.criteria, addedCriterion]);
    setCriteriaVer(newVer);
    setShowAddModal(false);
    setNewCrit({ kind: 'exclude', code: '', label: '', reason: '', detector_rule: '' });
  });

  const activeCriteriaCount = criteriaVer?.criteria?.filter(c => c.is_active).length || 0;

  return (
    <div className="space-y-6 max-w-5xl mx-auto py-2">
      {/* Clean, Airy Top Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 pb-3 border-b border-slate-200/80 dark:border-slate-800/80">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <span className="px-2.5 py-0.5 rounded-md text-[11px] font-bold font-mono uppercase bg-teal-500/10 text-teal-700 dark:text-teal-300 border border-teal-500/30">
              Protocol Workspace • Gate 1
            </span>
            <span className="text-xs text-slate-500 dark:text-slate-400 font-mono">Criteria Version: v{criteriaVer?.version_no}</span>
          </div>
          <h2 className="text-xl sm:text-2xl font-extrabold text-slate-900 dark:text-slate-100 tracking-tight">{review.title}</h2>
        </div>

        <div className="flex items-center gap-2">
          {!isEditingPico ? (
            <button
              onClick={() => setIsEditingPico(true)}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold bg-white dark:bg-slate-900 hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-700 dark:text-slate-200 border border-slate-200 dark:border-slate-800 shadow-sm transition"
            >
              <Edit2 className="w-3.5 h-3.5 text-teal-600 dark:text-teal-400" />
              <span>Edit Question & PICO</span>
            </button>
          ) : (
            <div className="flex items-center gap-2">
              <button
                onClick={() => setIsEditingPico(false)}
                className="px-3 py-1.5 rounded-lg text-xs font-medium text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200"
              >
                Cancel
              </button>
              <button
                onClick={handleSavePico}
                className="flex items-center gap-1.5 px-4 py-1.5 rounded-xl text-xs font-semibold bg-teal-600 hover:bg-teal-500 text-white shadow-sm transition"
              >
                <Save className="w-3.5 h-3.5" />
                <span>Save</span>
              </button>
            </div>
          )}

          {onProceedToSearch && (
            <button
              onClick={onProceedToSearch}
              className="flex items-center gap-2 px-4 py-1.5 rounded-xl text-xs font-bold bg-teal-600 hover:bg-teal-500 text-white shadow-sm transition hover:shadow-md"
            >
              <span>Search Literature</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </div>

      {/* Summary Stat Pills with Hover Interactions */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 md:gap-4">
        <div className="p-4 rounded-2xl bg-white/70 dark:bg-slate-900/50 backdrop-blur-md border border-slate-200/80 dark:border-slate-800/80 space-y-1 hover:-translate-y-0.5 hover:shadow-md transition-all duration-200">
          <span className="text-[10px] uppercase font-bold text-slate-500 dark:text-slate-400 tracking-wider">Literature Records</span>
          <div className="text-2xl font-bold text-slate-900 dark:text-slate-100 font-mono">{review.stats?.total_records ?? 0}</div>
          <span className="text-[11px] text-slate-500">Fetched via API</span>
        </div>

        <div className="p-4 rounded-2xl bg-white/70 dark:bg-slate-900/50 backdrop-blur-md border border-slate-200/80 dark:border-slate-800/80 space-y-1 hover:-translate-y-0.5 hover:shadow-md transition-all duration-200">
          <span className="text-[10px] uppercase font-bold text-slate-500 dark:text-slate-400 tracking-wider">Deduplicated Groups</span>
          <div className="text-2xl font-bold text-teal-600 dark:text-teal-400 font-mono">{review.stats?.unique_groups ?? 0}</div>
          <span className="text-[11px] text-slate-500">Single representation</span>
        </div>

        <div className="p-4 rounded-2xl bg-white/70 dark:bg-slate-900/50 backdrop-blur-md border border-slate-200/80 dark:border-slate-800/80 space-y-1 hover:-translate-y-0.5 hover:shadow-md transition-all duration-200">
          <span className="text-[10px] uppercase font-bold text-slate-500 dark:text-slate-400 tracking-wider">Protocol Criteria</span>
          <div className="text-2xl font-bold text-emerald-600 dark:text-emerald-400 font-mono">{activeCriteriaCount}</div>
          <span className="text-[11px] text-slate-500">Active rules</span>
        </div>

        <div className="p-4 rounded-2xl bg-white/70 dark:bg-slate-900/50 backdrop-blur-md border border-slate-200/80 dark:border-slate-800/80 space-y-1 hover:-translate-y-0.5 hover:shadow-md transition-all duration-200">
          <span className="text-[10px] uppercase font-bold text-slate-500 dark:text-slate-400 tracking-wider">Screening Progress</span>
          <div className="text-2xl font-bold text-indigo-600 dark:text-indigo-400 font-mono">
            {review.stats?.total_records ? Math.round(((review.stats.included + review.stats.excluded) / review.stats.total_records) * 100) : 0}%
          </div>
          <span className="text-[11px] text-slate-500">{review.stats?.unscreened ?? 0} pending</span>
        </div>
      </div>

      {/* Segmented Tabs */}
      <div className="flex items-center gap-1.5 p-1 rounded-xl bg-slate-200/60 dark:bg-slate-900/70 border border-slate-300/80 dark:border-slate-800 w-fit text-xs">
        <button
          onClick={() => setActiveTab('pico')}
          className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg font-semibold transition ${
            activeTab === 'pico'
              ? 'bg-white dark:bg-teal-600 text-slate-900 dark:text-white shadow-sm'
              : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200'
          }`}
        >
          <FileText className="w-3.5 h-3.5" />
          <span>Research Question & PICO</span>
        </button>

        <button
          onClick={() => setActiveTab('criteria')}
          className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg font-semibold transition ${
            activeTab === 'criteria'
              ? 'bg-white dark:bg-teal-600 text-slate-900 dark:text-white shadow-sm'
              : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200'
          }`}
        >
          <ShieldCheck className="w-3.5 h-3.5" />
          <span>Inclusion & Exclusion Criteria ({criteriaVer?.criteria.length || 0})</span>
        </button>
      </div>

      {/* Tab 1: Clean Question & PICO Layout */}
      {activeTab === 'pico' && (
        <div className="space-y-4 animate-in fade-in duration-150">
          {/* Main Question Card */}
          <div className="p-5 rounded-2xl bg-white/70 dark:bg-slate-900/50 backdrop-blur-md border border-slate-200/80 dark:border-slate-800/90 shadow-sm space-y-2 hover:-translate-y-0.5 hover:shadow-md transition-all duration-200">
            <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 dark:text-slate-500 font-mono block">
              Primary Research Question
            </span>

            {isEditingPico ? (
              <textarea
                value={picoForm.question}
                onChange={e => setPicoForm({ ...picoForm, question: e.target.value })}
                className="w-full px-4 py-2.5 bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-700 rounded-xl text-sm text-slate-900 dark:text-slate-100 focus:outline-none focus:border-teal-500 min-h-[70px]"
              />
            ) : (
              <p className="text-base sm:text-lg font-medium text-slate-800 dark:text-slate-100 leading-relaxed italic">
                "{review.question}"
              </p>
            )}
          </div>

          {/* 4 PICO Pillars */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 md:gap-4">
            {/* Population */}
            <div className="p-4 rounded-2xl bg-blue-50/60 dark:bg-blue-950/20 border border-blue-200/80 dark:border-blue-900/40 space-y-1.5 hover:-translate-y-0.5 hover:shadow-md transition-all duration-200">
              <span className="text-xs font-bold text-blue-700 dark:text-blue-400 uppercase tracking-wider font-mono">
                Population (P)
              </span>
              {isEditingPico ? (
                <input
                  type="text"
                  aria-label="Population"
                  value={picoForm.population}
                  onChange={e => setPicoForm({ ...picoForm, population: e.target.value })}
                  className="w-full px-3 py-1.5 bg-white dark:bg-slate-950 border border-slate-300 dark:border-slate-800 rounded-lg text-xs text-slate-900 dark:text-slate-100"
                />
              ) : (
                <div className="text-xs font-semibold text-slate-800 dark:text-slate-200">{review.population || 'Not defined yet'}</div>
              )}
              <p className="text-[11px] text-slate-500 dark:text-slate-400">Target patient or subject demographic eligible for this review.</p>
            </div>

            {/* Intervention */}
            <div className="p-4 rounded-2xl bg-teal-50/60 dark:bg-teal-950/20 border border-teal-200/80 dark:border-teal-900/40 space-y-1.5 hover:-translate-y-0.5 hover:shadow-md transition-all duration-200">
              <span className="text-xs font-bold text-teal-700 dark:text-teal-400 uppercase tracking-wider font-mono">
                Intervention (I)
              </span>
              {isEditingPico ? (
                <input
                  type="text"
                  aria-label="Intervention"
                  value={picoForm.intervention}
                  onChange={e => setPicoForm({ ...picoForm, intervention: e.target.value })}
                  className="w-full px-3 py-1.5 bg-white dark:bg-slate-950 border border-slate-300 dark:border-slate-800 rounded-lg text-xs text-slate-900 dark:text-slate-100"
                />
              ) : (
                <div className="text-xs font-semibold text-slate-800 dark:text-slate-200">{review.intervention || 'Not defined yet'}</div>
              )}
              <p className="text-[11px] text-slate-500 dark:text-slate-400">Therapeutic agent, diagnostic modality, or experimental intervention.</p>
            </div>

            {/* Comparator */}
            <div className="p-4 rounded-2xl bg-amber-50/60 dark:bg-amber-950/20 border border-amber-200/80 dark:border-amber-900/40 space-y-1.5 hover:-translate-y-0.5 hover:shadow-md transition-all duration-200">
              <span className="text-xs font-bold text-amber-700 dark:text-amber-400 uppercase tracking-wider font-mono">
                Comparator (C)
              </span>
              {isEditingPico ? (
                <input
                  type="text"
                  aria-label="Comparator"
                  value={picoForm.comparator}
                  onChange={e => setPicoForm({ ...picoForm, comparator: e.target.value })}
                  className="w-full px-3 py-1.5 bg-white dark:bg-slate-950 border border-slate-300 dark:border-slate-800 rounded-lg text-xs text-slate-900 dark:text-slate-100"
                />
              ) : (
                <div className="text-xs font-semibold text-slate-800 dark:text-slate-200">{review.comparator || 'Not defined yet'}</div>
              )}
              <p className="text-[11px] text-slate-500 dark:text-slate-400">Standard of care, placebo, or active control comparison.</p>
            </div>

            {/* Outcome */}
            <div className="p-4 rounded-2xl bg-rose-50/60 dark:bg-rose-950/20 border border-rose-200/80 dark:border-rose-900/40 space-y-1.5 hover:-translate-y-0.5 hover:shadow-md transition-all duration-200">
              <span className="text-xs font-bold text-rose-700 dark:text-rose-400 uppercase tracking-wider font-mono">
                Outcome (O)
              </span>
              {isEditingPico ? (
                <input
                  type="text"
                  aria-label="Outcome"
                  value={picoForm.outcome}
                  onChange={e => setPicoForm({ ...picoForm, outcome: e.target.value })}
                  className="w-full px-3 py-1.5 bg-white dark:bg-slate-950 border border-slate-300 dark:border-slate-800 rounded-lg text-xs text-slate-900 dark:text-slate-100"
                />
              ) : (
                <div className="text-xs font-semibold text-slate-800 dark:text-slate-200">{review.outcome || 'Not defined yet'}</div>
              )}
              <p className="text-[11px] text-slate-500 dark:text-slate-400">Primary and secondary clinical endpoints being measured.</p>
            </div>
          </div>
        </div>
      )}

      {/* Tab 2: Clean Criteria Cards View */}
      {activeTab === 'criteria' && (
        <div className="space-y-4 animate-in fade-in duration-150">
          <div className="flex items-center justify-between pb-1">
            <div>
              <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100">Protocol Inclusion & Exclusion Criteria</h3>
              <p className="text-xs text-slate-500 dark:text-slate-400">Every exclusion enforces a documented one-line rationale.</p>
            </div>
            <button
              onClick={() => setShowAddModal(true)}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold bg-teal-600 hover:bg-teal-500 text-white shadow-sm transition"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>Add Criterion</span>
            </button>
          </div>

          <div className="grid gap-2.5">
            {criteriaVer?.criteria.map((c) => (
              <div
                key={c.id}
                className={`p-3.5 rounded-xl border transition-all duration-150 flex items-start justify-between gap-4 ${
                  c.is_active
                    ? 'bg-white/70 dark:bg-slate-900/60 border-slate-200/80 dark:border-slate-800 hover:border-slate-300 dark:hover:border-slate-700 shadow-sm'
                    : 'bg-slate-100/50 dark:bg-slate-950/40 border-slate-200 dark:border-slate-900 opacity-60'
                }`}
              >
                <div className="space-y-1 flex-1">
                  <div className="flex items-center gap-2">
                    <span
                      className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider ${
                        c.kind === 'include'
                          ? 'bg-emerald-50 dark:bg-emerald-500/15 text-emerald-700 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-500/30'
                          : 'bg-rose-50 dark:bg-rose-500/15 text-rose-700 dark:text-rose-400 border border-rose-200 dark:border-rose-500/30'
                      }`}
                    >
                      {c.kind}
                    </span>
                    <span className="font-bold text-slate-900 dark:text-slate-100 text-xs">{c.label}</span>
                    <span className="text-[10px] font-mono text-slate-500">({c.code})</span>
                    <span className="px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 text-[10px] font-mono ml-auto">
                      Engine: {c.detector}
                    </span>
                  </div>

                  <p className="text-xs text-slate-600 dark:text-slate-300 leading-relaxed pl-0.5">
                    "{c.reason}"
                  </p>
                </div>

                <button
                  onClick={() => handleToggleCriterion(c.id)}
                  className="p-1.5 rounded-lg text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition shrink-0"
                  title="Toggle criterion active state"
                >
                  {c.is_active ? (
                    <ToggleRight className="w-6 h-6 text-teal-600 dark:text-teal-400" />
                  ) : (
                    <ToggleLeft className="w-6 h-6 text-slate-400 dark:text-slate-600" />
                  )}
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Add Criterion Modal */}
      {showAddModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/60 dark:bg-black/75 backdrop-blur-sm animate-in fade-in duration-150">
          <div className="w-full max-w-lg bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl shadow-2xl overflow-hidden p-6 space-y-4">
            <div className="flex items-center justify-between pb-2 border-b border-slate-200 dark:border-slate-800">
              <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100">Add Protocol Criterion</h3>
              <button onClick={() => setShowAddModal(false)} className="text-slate-400 hover:text-slate-700 dark:hover:text-slate-200">
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleAddCriterion} className="space-y-3 text-xs">
              <div>
                <label className="font-semibold text-slate-700 dark:text-slate-300 block mb-1">Criterion Kind:</label>
                <select
                  value={newCrit.kind}
                  onChange={e => setNewCrit({ ...newCrit, kind: e.target.value as 'include' | 'exclude' })}
                  className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-800 rounded-lg text-slate-900 dark:text-slate-200"
                >
                  <option value="exclude">Exclude Criterion</option>
                  <option value="include">Include Criterion</option>
                </select>
              </div>

              <div>
                <label className="font-semibold text-slate-700 dark:text-slate-300 block mb-1">Criterion Title / Label:</label>
                <input
                  type="text"
                  required
                  value={newCrit.label}
                  onChange={e => setNewCrit({ ...newCrit, label: e.target.value })}
                  className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-800 rounded-lg text-slate-900 dark:text-slate-200"
                  placeholder="e.g. Non-Human Animal Studies"
                />
              </div>

              <div>
                <label className="font-semibold text-slate-700 dark:text-slate-300 block mb-1">Documented Rationale (One-Line Reason):</label>
                <textarea
                  required
                  value={newCrit.reason}
                  onChange={e => setNewCrit({ ...newCrit, reason: e.target.value })}
                  className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-800 rounded-lg text-slate-900 dark:text-slate-200 min-h-[50px]"
                  placeholder="e.g. The review question strictly investigates adult human clinical trials."
                />
              </div>

              <div>
                <label className="font-semibold text-slate-700 dark:text-slate-300 block mb-1">Automatic Detector Rule (Optional):</label>
                <input
                  value={newCrit.detector_rule}
                  onChange={e => setNewCrit({ ...newCrit, detector_rule: e.target.value })}
                  className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-800 rounded-lg text-slate-900 dark:text-slate-200"
                  placeholder="Named detector (non_human, non_english) or keywords separated by |"
                />
                <span className="text-slate-500 dark:text-slate-400 text-[11px] block mt-1">Leave blank for manual screening assessment.</span>
              </div>

              <div className="flex items-center justify-end gap-2 pt-3 border-t border-slate-200 dark:border-slate-800">
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  className="px-3 py-1.5 rounded-lg text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-1.5 rounded-lg bg-teal-600 hover:bg-teal-500 text-white font-semibold shadow"
                >
                  Add Criterion
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
