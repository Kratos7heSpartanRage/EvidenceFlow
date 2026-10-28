import { AlertCircle, FileText, GitMerge, Lightbulb, RefreshCw, Sparkles } from 'lucide-react';
import React from 'react';
import { api } from '../../lib/api';
import { useData, useWorkspace } from '../../lib/workspace';

export function ReviewIntelligence() {
  const { reviewId } = useWorkspace();
  const [rechecks] = useData(['recheck-candidates'], () => api.getRecheckCandidates(reviewId));
  const [families] = useData(['study-families'], () => api.getStudyFamilies(reviewId));

  return (
    <div className="space-y-6 max-w-6xl mx-auto py-2">
      {/* Top Banner */}
      <div className="p-5 rounded-2xl bg-white/70 dark:bg-slate-900/60 backdrop-blur-md border border-slate-200/80 dark:border-slate-800/80 shadow-sm space-y-2 hover:-translate-y-0.5 hover:shadow-md transition-all duration-200">
        <div className="flex items-center gap-2">
          <span className="px-2.5 py-0.5 rounded-md text-[11px] font-bold font-mono uppercase bg-amber-500/10 text-amber-700 dark:text-amber-300 border border-amber-500/30 flex items-center gap-1.5">
            <Sparkles className="w-3 h-3" />
            Innovation • AI Review Intelligence
          </span>
          <span className="text-xs text-slate-500 dark:text-slate-400 font-mono">Evidence-Backed Algorithmic Recommendations</span>
        </div>
        <h2 className="text-xl font-bold text-slate-900 dark:text-slate-100">Review Intelligence & Cross-Version Audit</h2>
        <p className="text-xs text-slate-500 dark:text-slate-400 leading-relaxed max-w-3xl">
          Algorithmic heuristics surface prior exclusions impacted by criteria revisions and trace multi-report clinical trial families across registers. Reviewers maintain complete oversight.
        </p>
      </div>

      {/* Grid: 2 Intelligence Columns */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Section 1: Old Exclusions to Reconsider */}
        <div className="p-6 rounded-2xl bg-white/70 dark:bg-slate-900/60 backdrop-blur-md border border-slate-200/80 dark:border-slate-800 shadow-sm space-y-4 hover:-translate-y-0.5 hover:shadow-md transition-all duration-200 flex flex-col justify-between">
          <div className="space-y-3">
            <div className="flex items-center justify-between pb-3 border-b border-slate-200 dark:border-slate-800">
              <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100 flex items-center gap-2">
                <RefreshCw className="w-4 h-4 text-amber-600 dark:text-amber-400" />
                <span>Exclusions to Reconsider</span>
              </h3>
              <span className="px-2 py-0.5 rounded-md text-[11px] font-bold font-mono bg-amber-100 dark:bg-amber-500/20 text-amber-800 dark:text-amber-300 border border-amber-300 dark:border-amber-500/30">
                {rechecks.length} candidate{rechecks.length === 1 ? '' : 's'}
              </span>
            </div>

            <p className="text-xs text-slate-500 dark:text-slate-400">
              Identifies earlier exclusions whose matched criterion was widened or removed in the latest criteria revision.
            </p>

            {!rechecks.length ? (
              <div className="p-8 text-center rounded-xl bg-slate-50/60 dark:bg-slate-950/40 border border-dashed border-slate-200 dark:border-slate-800 space-y-2">
                <AlertCircle className="w-6 h-6 text-slate-400 mx-auto" />
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  No affected exclusions found across current criteria versions.
                </p>
              </div>
            ) : (
              <div className="space-y-3 max-h-[500px] overflow-y-auto pr-1">
                {rechecks.map(item => (
                  <article
                    key={item.record_id}
                    className="rounded-xl border border-amber-200 dark:border-amber-500/30 bg-amber-50/40 dark:bg-amber-950/20 p-4 space-y-2.5 hover:shadow-sm transition"
                  >
                    <h4 className="text-xs font-bold text-slate-900 dark:text-slate-100 leading-snug">{item.title}</h4>
                    <div className="flex flex-wrap items-center gap-2 text-[11px] font-mono">
                      <span className="px-2 py-0.5 rounded bg-amber-100 dark:bg-amber-500/20 text-amber-800 dark:text-amber-300">
                        Excluded by: {item.reviewer}
                      </span>
                      <span className="text-slate-500 dark:text-slate-400">
                        Reason: {item.original_reason}
                      </span>
                    </div>

                    <div className="grid grid-cols-2 gap-2 text-[10px] font-mono p-2 rounded bg-white/60 dark:bg-slate-900/60 border border-amber-200/60 dark:border-amber-500/20">
                      <div>
                        <span className="text-slate-400 block uppercase">Old Criterion</span>
                        <span className="text-slate-700 dark:text-slate-300 font-semibold">{item.old_criterion}</span>
                      </div>
                      <div>
                        <span className="text-amber-600 dark:text-amber-400 block uppercase">Revision Impact</span>
                        <span className="text-amber-700 dark:text-amber-300 font-semibold">{item.new_criterion || 'Removed / Relaxed'}</span>
                      </div>
                    </div>

                    {!!item.matched_new_terms?.length && (
                      <p className="text-[11px] text-teal-700 dark:text-teal-300 font-mono">
                        Matched new terms: <strong>{item.matched_new_terms.join(', ')}</strong>
                      </p>
                    )}

                    <blockquote className="text-[11px] text-slate-600 dark:text-slate-300 border-l-2 border-amber-500 pl-2.5 italic line-clamp-3">
                      {item.evidence_excerpt || 'No abstract available'}
                    </blockquote>
                  </article>
                ))}
              </div>
            )}
          </div>

          <div className="pt-3 border-t border-slate-200 dark:border-slate-800 text-[11px] text-slate-500 dark:text-slate-400 flex items-center gap-2">
            <span className="font-semibold text-amber-700 dark:text-amber-400 font-mono">Note:</span>
            <span>To modify a decision, search its title in the Screening Queue and record a new human verdict.</span>
          </div>
        </div>

        {/* Section 2: Study Families & Multi-Report Trials */}
        <div className="p-6 rounded-2xl bg-white/70 dark:bg-slate-900/60 backdrop-blur-md border border-slate-200/80 dark:border-slate-800 shadow-sm space-y-4 hover:-translate-y-0.5 hover:shadow-md transition-all duration-200 flex flex-col justify-between">
          <div className="space-y-3">
            <div className="flex items-center justify-between pb-3 border-b border-slate-200 dark:border-slate-800">
              <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100 flex items-center gap-2">
                <GitMerge className="w-4 h-4 text-cyan-600 dark:text-cyan-400" />
                <span>Trial Families & Multi-Report Clusters</span>
              </h3>
              <span className="px-2 py-0.5 rounded-md text-[11px] font-bold font-mono bg-cyan-100 dark:bg-cyan-500/20 text-cyan-800 dark:text-cyan-300 border border-cyan-300 dark:border-cyan-500/30">
                {families.length} cluster{families.length === 1 ? '' : 's'}
              </span>
            </div>

            <p className="text-xs text-slate-500 dark:text-slate-400">
              Links publications sharing trial registry IDs (e.g. ClinicalTrials.gov NCT numbers) or identical study populations.
            </p>

            {!families.length ? (
              <div className="p-8 text-center rounded-xl bg-slate-50/60 dark:bg-slate-950/40 border border-dashed border-slate-200 dark:border-slate-800 space-y-2">
                <FileText className="w-6 h-6 text-slate-400 mx-auto" />
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  No linked publication families or trial clusters detected yet.
                </p>
              </div>
            ) : (
              <div className="space-y-3 max-h-[500px] overflow-y-auto pr-1">
                {families.map(family => (
                  <article
                    key={`${family.relationship}-${family.id}`}
                    className="rounded-xl border border-cyan-200 dark:border-cyan-500/30 bg-cyan-50/30 dark:bg-cyan-950/20 p-4 space-y-2.5 hover:shadow-sm transition"
                  >
                    <div className="flex flex-wrap gap-2 items-center justify-between">
                      <strong className="text-xs font-bold text-slate-900 dark:text-slate-100 flex items-center gap-1.5">
                        <GitMerge className="w-3.5 h-3.5 text-cyan-600 dark:text-cyan-400" />
                        {family.relationship === 'duplicate_records' ? 'Duplicate Records Cluster' : 'Multi-Report Trial Family'}
                      </strong>
                      <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-cyan-100 dark:bg-cyan-500/20 text-cyan-800 dark:text-cyan-300 border border-cyan-300 dark:border-cyan-500/30">
                        {family.id}
                      </span>
                    </div>

                    <p className="text-[11px] text-slate-500 dark:text-slate-400 font-mono">
                      Evidence: {family.evidence}
                    </p>

                    <ol className="ml-2 border-l-2 border-cyan-400/50 dark:border-cyan-600/50 space-y-2 pt-1">
                      {family.records.map(record => (
                        <li key={record.id} className="relative pl-4 text-xs text-slate-700 dark:text-slate-300">
                          <span aria-hidden="true" className="absolute -left-[5px] top-1.5 h-2 w-2 rounded-full bg-cyan-500" />
                          <div className="font-semibold">{record.title}</div>
                          <div className="text-[10px] text-slate-500 font-mono">
                            {record.source}{record.pmid ? ` • PMID: ${record.pmid}` : ''}
                          </div>
                        </li>
                      ))}
                    </ol>
                  </article>
                ))}
              </div>
            )}
          </div>

          <div className="pt-3 border-t border-slate-200 dark:border-slate-800 text-[11px] text-slate-500 dark:text-slate-400 flex items-center gap-2">
            <span className="font-semibold text-cyan-700 dark:text-cyan-400 font-mono">Audit:</span>
            <span>Shared registry entries require explicit reviewer confirmation before aggregating outcomes.</span>
          </div>
        </div>
      </div>
    </div>
  );
}
