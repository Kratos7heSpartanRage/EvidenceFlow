import { useQuery } from '@tanstack/react-query';
import {
  Activity,
  AlertTriangle,
  CheckCircle,
  Clock,
  Database,
  FileSearch,
  GitMerge,
  Layers,
  Loader2,
  Play,
  RefreshCw,
  RotateCcw,
  Tag,
  XCircle
} from 'lucide-react';
import React, { useEffect, useState } from 'react';
import { api } from '../../lib/api';
import { useAction, useData, useWorkspace } from '../../lib/workspace';
import type { EntityId } from '../../types/api';

const STEP_ICONS: Record<string, React.ElementType> = {
  fetch: RefreshCw,
  store: Database,
  dedup: GitMerge,
  reconcile: Layers,
  screen: FileSearch,
  pico: Tag,
  diff: Clock
};

export function RunsView() {
  const { reviewId } = useWorkspace();
  const [queries, , loadQueries] = useData(['queries'], () => api.getQueries(reviewId));
  const [selectedRunId, setSelectedRunId] = useState<EntityId | null>(null);

  // Auto-select latest run from localStorage if available
  useEffect(() => {
    try {
      const saved = localStorage.getItem(`evidenceflow_run_${reviewId}`);
      if (saved) {
        const parsed = JSON.parse(saved);
        if (parsed?.runId && !selectedRunId) {
          setSelectedRunId(parsed.runId);
        }
      }
    } catch {}
  }, [reviewId, selectedRunId]);

  // Poll active run if running
  const activeRun = useQuery({
    queryKey: ['run', selectedRunId],
    queryFn: () => (selectedRunId ? api.getRun(selectedRunId) : Promise.resolve(null)),
    enabled: !!selectedRunId,
    refetchInterval: query =>
      ['queued', 'running'].includes(query.state.data?.status || '') ? 1500 : false
  });

  const run = activeRun.data;

  const handleTriggerRun = useAction(async (queryId: EntityId) => {
    const res = await api.importQuery(queryId);
    setSelectedRunId(res.run_id);
    localStorage.setItem(
      `evidenceflow_run_${reviewId}`,
      JSON.stringify({ queryId, runId: res.run_id })
    );
    await loadQueries();
  });

  return (
    <div className="space-y-6 max-w-6xl mx-auto py-2">
      {/* Header */}
      <div className="p-5 rounded-2xl bg-white/70 dark:bg-slate-900/60 backdrop-blur-md border border-slate-200/80 dark:border-slate-800/80 shadow-sm space-y-1 hover:-translate-y-0.5 hover:shadow-md transition-all duration-200">
        <div className="flex items-center gap-2">
          <span className="px-2.5 py-0.5 rounded-md text-[11px] font-bold font-mono uppercase bg-teal-500/10 text-teal-700 dark:text-teal-300 border border-teal-500/30">
            Pipeline Execution • Gate 3
          </span>
          <span className="text-xs text-slate-500 dark:text-slate-400 font-mono">Fetch → Store → Dedup → Reconcile → Screen → PICO → Diff</span>
        </div>
        <h2 className="text-xl font-bold text-slate-900 dark:text-slate-100">Automated Pipeline Runs & Orchestration Log</h2>
        <p className="text-xs text-slate-500 dark:text-slate-400">
          Trace automated background batch execution with step-level input/output summaries and idempotent retry. Polled every 1.5s while running.
        </p>
      </div>

      {/* Query Version selector to trigger or view runs */}
      <div className="grid md:grid-cols-12 gap-5">
        <div className="md:col-span-4 space-y-4">
          <div className="p-4 rounded-2xl bg-white/70 dark:bg-slate-900/60 backdrop-blur-md border border-slate-200/80 dark:border-slate-800/80 shadow-sm space-y-3">
            <h3 className="text-xs font-mono uppercase font-bold text-slate-500 dark:text-slate-400">Query Versions & Triggers</h3>
            {!queries.length ? (
              <p className="text-xs text-slate-500">No queries created yet. Go to Search & Fetch to define one.</p>
            ) : (
              <div className="space-y-2">
                {queries.map(q => (
                  <div
                    key={q.id}
                    className="p-3.5 rounded-xl bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800/90 space-y-2 text-xs hover:-translate-y-0.5 hover:shadow-sm transition-all duration-150"
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-mono font-bold text-teal-700 dark:text-teal-400">v{q.version_no}</span>
                      <span
                        className={`px-2 py-0.5 rounded text-[10px] uppercase font-mono ${
                          q.status === 'imported'
                            ? 'bg-emerald-50 dark:bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-500/30'
                            : 'bg-amber-50 dark:bg-amber-500/10 text-amber-700 dark:text-amber-400 border border-amber-200 dark:border-amber-500/30'
                        }`}
                      >
                        {q.status}
                      </span>
                    </div>
                    <p className="text-[11px] text-slate-700 dark:text-slate-300 truncate font-mono" title={q.expression}>
                      {q.expression}
                    </p>
                    <div className="flex items-center justify-between text-[11px] text-slate-500 dark:text-slate-400 pt-1 border-t border-slate-200 dark:border-slate-900">
                      <span>Hits: {q.hit_count?.toLocaleString() ?? '—'}</span>
                      <span>Imported: {q.imported_count?.toLocaleString() ?? '—'}</span>
                    </div>

                    <div className="flex items-center gap-2 pt-1">
                      <button
                        onClick={() => handleTriggerRun(q.id)}
                        className="flex-1 flex items-center justify-center gap-1.5 py-1.5 px-2.5 rounded-lg bg-teal-600 hover:bg-teal-500 text-white font-semibold text-xs shadow-sm transition"
                      >
                        <Play className="w-3 h-3" />
                        <span>Run Pipeline</span>
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Live Run Detail & Step Timeline */}
        <div className="md:col-span-8">
          {!run ? (
            <div className="p-12 rounded-2xl bg-white/70 dark:bg-slate-900/60 backdrop-blur-md border border-slate-200/80 dark:border-slate-800/80 text-center space-y-3">
              <Activity className="w-8 h-8 text-teal-600 dark:text-teal-400 mx-auto animate-pulse" />
              <h3 className="text-sm font-semibold text-slate-800 dark:text-slate-200">No Active Pipeline Execution Selected</h3>
              <p className="text-xs text-slate-500 dark:text-slate-400 max-w-sm mx-auto">
                Trigger a pipeline run from the query list on the left, or approve an imported query in Search & Fetch to monitor live step execution.
              </p>
            </div>
          ) : (
            <div className="p-6 rounded-2xl bg-white/70 dark:bg-slate-900/60 backdrop-blur-md border border-slate-200/80 dark:border-slate-800/80 shadow-sm space-y-5">
              <div className="flex items-center justify-between border-b border-slate-200 dark:border-slate-800 pb-4">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-mono font-bold text-sm text-teal-700 dark:text-teal-400">PIPELINE RUN #{run.id}</span>
                    <span
                      className={`px-2 py-0.5 rounded text-xs font-mono uppercase font-bold ${
                        run.status === 'completed'
                          ? 'bg-emerald-50 dark:bg-emerald-500/20 text-emerald-700 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-500/30'
                          : run.status === 'running'
                          ? 'bg-teal-50 dark:bg-teal-500/20 text-teal-700 dark:text-teal-300 border border-teal-200 dark:border-teal-500/30 animate-pulse'
                          : 'bg-rose-50 dark:bg-rose-500/20 text-rose-700 dark:text-rose-400 border border-rose-200 dark:border-rose-500/30'
                      }`}
                    >
                      {run.status}
                    </span>
                  </div>
                  <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                    Trigger: <span className="text-slate-800 dark:text-slate-200 font-medium">{run.trigger}</span> | Started:{' '}
                    {new Date(run.started_at).toLocaleTimeString()}
                  </p>
                </div>
              </div>

              {/* Progress Steps Timeline */}
              <div className="space-y-3">
                <h4 className="text-xs font-mono uppercase font-bold text-slate-500 dark:text-slate-400">7-Step Execution Pipeline</h4>
                <div className="space-y-2">
                  {run.steps.map((s, idx) => {
                    const Icon = STEP_ICONS[s.step] || Activity;
                    return (
                      <div
                        key={s.id || idx}
                        className={`p-3.5 rounded-xl border text-xs flex items-center justify-between transition-all duration-150 ${
                          s.status === 'completed'
                            ? 'bg-emerald-50/70 dark:bg-emerald-950/20 border-emerald-200 dark:border-emerald-500/30 text-emerald-900 dark:text-emerald-300'
                            : s.status === 'running'
                            ? 'bg-teal-50/70 dark:bg-teal-950/30 border-teal-300 dark:border-teal-500/40 text-teal-900 dark:text-teal-200'
                            : s.status === 'failed'
                            ? 'bg-rose-50/70 dark:bg-rose-950/20 border-rose-200 dark:border-rose-500/30 text-rose-900 dark:text-rose-300'
                            : 'bg-slate-50 dark:bg-slate-950 border-slate-200 dark:border-slate-800 text-slate-500 dark:text-slate-400'
                        }`}
                      >
                        <div className="flex items-center gap-3">
                          <Icon className="w-4 h-4 shrink-0" />
                          <div>
                            <span className="font-bold uppercase tracking-wider">{s.step}</span>
                            {s.output_summary_json && (
                              <p className="text-[11px] opacity-80 mt-0.5">
                                {typeof s.output_summary_json === 'object'
                                  ? (s.output_summary_json as any).message || JSON.stringify(s.output_summary_json)
                                  : String(s.output_summary_json)}
                              </p>
                            )}
                          </div>
                        </div>

                        <div className="flex items-center gap-2 font-mono text-[11px]">
                          {s.status === 'completed' && <CheckCircle className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />}
                          {s.status === 'running' && <Loader2 className="w-4 h-4 text-teal-600 dark:text-teal-400 animate-spin" />}
                          {s.status === 'failed' && <XCircle className="w-4 h-4 text-rose-600 dark:text-rose-400" />}
                          <span className="uppercase font-semibold">{s.status}</span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Failed Error Recovery */}
              {run.status === 'failed' && (
                <div className="p-4 rounded-xl bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-500/30 text-xs text-rose-900 dark:text-rose-200 flex items-start gap-3">
                  <AlertTriangle className="w-4 h-4 text-rose-600 dark:text-rose-400 shrink-0 mt-0.5" />
                  <div className="flex-1">
                    <p className="font-bold">Step Execution Failed</p>
                    <p className="text-[11px] text-rose-700 dark:text-rose-300 mt-0.5">{run.error || 'An error occurred during step execution.'}</p>
                    <button
                      onClick={() => activeRun.refetch()}
                      className="mt-2.5 px-3 py-1.5 rounded-lg bg-rose-600 hover:bg-rose-500 text-white font-semibold text-xs flex items-center gap-1.5 transition"
                    >
                      <RotateCcw className="w-3.5 h-3.5" />
                      <span>Retry Pipeline Step</span>
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
