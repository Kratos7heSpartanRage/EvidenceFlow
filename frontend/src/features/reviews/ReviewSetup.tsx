import React, { useState, useEffect } from 'react';
import { api } from '../../lib/api';
import { Review, CriteriaVersion, Criterion } from '../../types/api';
import { FileText, Plus, ShieldCheck, ToggleLeft, ToggleRight, Sparkles, Check, Edit2, Save, X } from 'lucide-react';

export function ReviewSetup() {
  const [review, setReview] = useState<Review | null>(null);
  const [criteriaVer, setCriteriaVer] = useState<CriteriaVersion | null>(null);
  const [loading, setLoading] = useState(true);
  const [isEditingPico, setIsEditingPico] = useState(false);
  const [picoForm, setPicoForm] = useState({
    title: '',
    question: '',
    population: '',
    intervention: '',
    comparator: '',
    outcome: ''
  });

  // New criterion modal state
  const [showAddModal, setShowAddModal] = useState(false);
  const [newCrit, setNewCrit] = useState({
    kind: 'exclude' as 'include' | 'exclude',
    code: '',
    label: '',
    reason: '',
    detector: 'rule' as 'metadata' | 'rule' | 'metadata_then_rule'
  });

  const loadData = async () => {
    try {
      setLoading(true);
      const rev = await api.getReview(1);
      const crits = await api.getCriteria(1);
      setReview(rev);
      setCriteriaVer(crits);
      setPicoForm({
        title: rev.title,
        question: rev.question,
        population: rev.population,
        intervention: rev.intervention,
        comparator: rev.comparator,
        outcome: rev.outcome
      });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleSavePico = async () => {
    if (!review) return;
    const updated = await api.updateReview(review.id, picoForm);
    setReview(updated);
    setIsEditingPico(false);
  };

  const handleToggleCriterion = async (criterionId: number) => {
    if (!criteriaVer) return;
    const updatedCriteria = criteriaVer.criteria.map(c =>
      c.id === criterionId ? { ...c, is_active: !c.is_active } : c
    );
    const newVer = await api.updateCriteria(criteriaVer.review_id, updatedCriteria);
    setCriteriaVer(newVer);
  };

  const handleAddCriterion = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!criteriaVer || !newCrit.label || !newCrit.reason) return;

    const addedCriterion: Criterion = {
      id: 0,
      criteria_version_id: criteriaVer.id,
      kind: newCrit.kind,
      code: newCrit.code.trim().toLowerCase().replace(/\s+/g, '_') || 'custom_crit',
      label: newCrit.label,
      reason: newCrit.reason,
      detector: newCrit.detector,
      params_json: {},
      is_active: true
    };

    const newVer = await api.updateCriteria(criteriaVer.review_id, [...criteriaVer.criteria, addedCriterion]);
    setCriteriaVer(newVer);
    setShowAddModal(false);
    setNewCrit({ kind: 'exclude', code: '', label: '', reason: '', detector: 'rule' });
  };

  if (loading || !review) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-brand-500"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      {/* Top Banner */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 p-5 rounded-xl bg-gradient-to-r from-brand-950/40 via-slate-900 to-slate-900 border border-brand-900/40 shadow-xl">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <span className="px-2 py-0.5 rounded text-[11px] font-bold font-mono uppercase bg-brand-500/20 text-brand-300 border border-brand-500/30">
              Step 0 Protocol
            </span>
            <span className="text-xs text-slate-400 font-mono">Criteria Version: v{criteriaVer?.version_no}</span>
          </div>
          <h2 className="text-xl font-bold text-slate-100">{review.title}</h2>
          <p className="text-xs text-slate-400">
            Immutable protocol criteria. Editing or toggling criteria automatically logs an audited criteria version.
          </p>
        </div>
        <div className="flex items-center gap-2">
          {!isEditingPico ? (
            <button
              onClick={() => setIsEditingPico(true)}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition"
            >
              <Edit2 className="w-3.5 h-3.5 text-brand-400" />
              <span>Edit Protocol</span>
            </button>
          ) : (
            <div className="flex items-center gap-2">
              <button
                onClick={() => setIsEditingPico(false)}
                className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-medium text-slate-400 hover:text-slate-200"
              >
                <X className="w-3.5 h-3.5" />
                <span>Cancel</span>
              </button>
              <button
                onClick={handleSavePico}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-brand-600 hover:bg-brand-500 text-white shadow-lg shadow-brand-950/50 transition"
              >
                <Save className="w-3.5 h-3.5" />
                <span>Save Protocol</span>
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Review Question & PICO Definition Card */}
      <div className="p-6 rounded-xl bg-slate-900/60 border border-slate-800 shadow-lg space-y-4">
        <div className="flex items-center justify-between pb-3 border-b border-slate-800">
          <div className="flex items-center gap-2 text-slate-200 font-bold text-sm">
            <FileText className="w-4 h-4 text-brand-400" />
            <span>Research Question & PICO Formulation</span>
          </div>
        </div>

        {isEditingPico ? (
          <div className="space-y-4 text-xs">
            <div>
              <label className="font-semibold text-slate-300 block mb-1">Primary Review Question:</label>
              <textarea
                value={picoForm.question}
                onChange={e => setPicoForm({ ...picoForm, question: e.target.value })}
                className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-slate-100 focus:outline-none focus:border-brand-500 min-h-[60px]"
              />
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="font-semibold text-pico-p block mb-1">Population (P):</label>
                <input
                  type="text"
                  value={picoForm.population}
                  onChange={e => setPicoForm({ ...picoForm, population: e.target.value })}
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-slate-100 focus:outline-none focus:border-brand-500"
                />
              </div>
              <div>
                <label className="font-semibold text-pico-i block mb-1">Intervention (I):</label>
                <input
                  type="text"
                  value={picoForm.intervention}
                  onChange={e => setPicoForm({ ...picoForm, intervention: e.target.value })}
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-slate-100 focus:outline-none focus:border-brand-500"
                />
              </div>
              <div>
                <label className="font-semibold text-pico-c block mb-1">Comparator (C):</label>
                <input
                  type="text"
                  value={picoForm.comparator}
                  onChange={e => setPicoForm({ ...picoForm, comparator: e.target.value })}
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-slate-100 focus:outline-none focus:border-brand-500"
                />
              </div>
              <div>
                <label className="font-semibold text-pico-o block mb-1">Outcome (O):</label>
                <input
                  type="text"
                  value={picoForm.outcome}
                  onChange={e => setPicoForm({ ...picoForm, outcome: e.target.value })}
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-slate-100 focus:outline-none focus:border-brand-500"
                />
              </div>
            </div>
          </div>
        ) : (
          <div className="space-y-4">
            <div className="p-3.5 rounded-lg bg-slate-950/70 border border-slate-800/80">
              <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block mb-1">Review Question</span>
              <p className="text-sm font-medium text-slate-100 leading-relaxed italic">
                "{review.question}"
              </p>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
              <div className="p-3 rounded-lg bg-pico-p/10 border border-pico-p/30">
                <span className="text-[10px] font-bold text-pico-p uppercase tracking-wider block">Population (P)</span>
                <span className="text-xs font-semibold text-slate-200 mt-1 block">{review.population}</span>
              </div>
              <div className="p-3 rounded-lg bg-pico-i/10 border border-pico-i/30">
                <span className="text-[10px] font-bold text-pico-i uppercase tracking-wider block">Intervention (I)</span>
                <span className="text-xs font-semibold text-slate-200 mt-1 block">{review.intervention}</span>
              </div>
              <div className="p-3 rounded-lg bg-pico-c/10 border border-pico-c/30">
                <span className="text-[10px] font-bold text-pico-c uppercase tracking-wider block">Comparator (C)</span>
                <span className="text-xs font-semibold text-slate-200 mt-1 block">{review.comparator}</span>
              </div>
              <div className="p-3 rounded-lg bg-pico-o/10 border border-pico-o/30">
                <span className="text-[10px] font-bold text-pico-o uppercase tracking-wider block">Outcome (O)</span>
                <span className="text-xs font-semibold text-slate-200 mt-1 block">{review.outcome}</span>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Protocol Criteria Section */}
      <div className="p-6 rounded-xl bg-slate-900/60 border border-slate-800 shadow-lg space-y-4">
        <div className="flex items-center justify-between pb-3 border-b border-slate-800">
          <div>
            <h3 className="text-sm font-bold text-slate-100 flex items-center gap-2">
              <ShieldCheck className="w-4 h-4 text-emerald-400" />
              <span>Inclusion & Exclusion Criteria with Rationale</span>
            </h3>
            <p className="text-xs text-slate-400 mt-0.5">
              Every exclusion requires a documented one-line reason. Reviewer toggles dictate algorithmic screening suggestions.
            </p>
          </div>
          <button
            onClick={() => setShowAddModal(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-brand-600 hover:bg-brand-500 text-white shadow transition"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>Add Criterion</span>
          </button>
        </div>

        {/* Criteria Table */}
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-slate-300">
            <thead className="bg-slate-950/80 text-[11px] text-slate-400 uppercase tracking-wider border-b border-slate-800">
              <tr>
                <th className="py-2.5 px-3">Status</th>
                <th className="py-2.5 px-3">Type</th>
                <th className="py-2.5 px-3">Criterion Name</th>
                <th className="py-2.5 px-4">Documented Rationale (One-Line Reason)</th>
                <th className="py-2.5 px-3">Detection Method</th>
                <th className="py-2.5 px-3 text-right">Toggle</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-normal">
              {criteriaVer?.criteria.map((c) => (
                <tr key={c.id} className={`hover:bg-slate-800/30 transition ${!c.is_active ? 'opacity-50' : ''}`}>
                  <td className="py-3 px-3">
                    <span
                      className={`inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-mono ${
                        c.is_active ? 'bg-emerald-500/20 text-emerald-300' : 'bg-slate-800 text-slate-500'
                      }`}
                    >
                      {c.is_active ? 'ACTIVE' : 'MUTED'}
                    </span>
                  </td>
                  <td className="py-3 px-3">
                    <span
                      className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider ${
                        c.kind === 'include'
                          ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                          : 'bg-rose-500/20 text-rose-400 border border-rose-500/30'
                      }`}
                    >
                      {c.kind}
                    </span>
                  </td>
                  <td className="py-3 px-3 font-semibold text-slate-200">
                    <div>{c.label}</div>
                    <div className="text-[10px] font-mono text-slate-500">{c.code}</div>
                  </td>
                  <td className="py-3 px-4 text-slate-300 leading-relaxed">
                    {c.reason}
                  </td>
                  <td className="py-3 px-3 font-mono text-[11px]">
                    <span className="px-2 py-0.5 rounded bg-slate-800 border border-slate-700 text-slate-300">
                      {c.detector}
                    </span>
                  </td>
                  <td className="py-3 px-3 text-right">
                    <button
                      onClick={() => handleToggleCriterion(c.id)}
                      className="p-1 rounded text-slate-400 hover:text-slate-200 transition"
                      title={c.is_active ? 'Mute this criterion' : 'Activate this criterion'}
                    >
                      {c.is_active ? (
                        <ToggleRight className="w-5 h-5 text-brand-400" />
                      ) : (
                        <ToggleLeft className="w-5 h-5 text-slate-600" />
                      )}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Add Criterion Modal */}
      {showAddModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm">
          <div className="w-full max-w-lg bg-slate-900 border border-slate-800 rounded-xl shadow-2xl overflow-hidden p-6 space-y-4">
            <div className="flex items-center justify-between pb-2 border-b border-slate-800">
              <h3 className="text-sm font-bold text-slate-100">Add Protocol Criterion</h3>
              <button onClick={() => setShowAddModal(false)} className="text-slate-400 hover:text-slate-200">
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleAddCriterion} className="space-y-3 text-xs">
              <div>
                <label className="font-semibold text-slate-300 block mb-1">Criterion Kind:</label>
                <select
                  value={newCrit.kind}
                  onChange={e => setNewCrit({ ...newCrit, kind: e.target.value as any })}
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-slate-200"
                >
                  <option value="exclude">Exclude Criterion</option>
                  <option value="include">Include Criterion</option>
                </select>
              </div>

              <div>
                <label className="font-semibold text-slate-300 block mb-1">Label (e.g. Non-Human Animal Studies):</label>
                <input
                  type="text"
                  required
                  value={newCrit.label}
                  onChange={e => setNewCrit({ ...newCrit, label: e.target.value })}
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-slate-200"
                  placeholder="e.g. Pediatric Cohorts (<18 yrs)"
                />
              </div>

              <div>
                <label className="font-semibold text-slate-300 block mb-1">One-Line Rationale / Reason:</label>
                <textarea
                  required
                  value={newCrit.reason}
                  onChange={e => setNewCrit({ ...newCrit, reason: e.target.value })}
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-slate-200 min-h-[50px]"
                  placeholder="e.g. Question strictly targets adult manifestation of diabetes"
                />
              </div>

              <div>
                <label className="font-semibold text-slate-300 block mb-1">Detector Engine Strategy:</label>
                <select
                  value={newCrit.detector}
                  onChange={e => setNewCrit({ ...newCrit, detector: e.target.value as any })}
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-slate-200"
                >
                  <option value="metadata_then_rule">Metadata field first, rule fallback</option>
                  <option value="metadata">Metadata field only</option>
                  <option value="rule">Rule / Regex keywords only</option>
                </select>
              </div>

              <div className="flex items-center justify-end gap-2 pt-3 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  className="px-3 py-1.5 rounded-lg text-slate-400 hover:text-slate-200"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-1.5 rounded-lg bg-brand-600 hover:bg-brand-500 text-white font-semibold shadow"
                >
                  Add to Protocol
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
