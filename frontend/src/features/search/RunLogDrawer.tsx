import { useQuery, useQueryClient } from '@tanstack/react-query';
import { CheckCircle, Clock, Database, FileSearch, GitMerge, Layers, Loader2, RefreshCw, Tag, X } from 'lucide-react';
import React, { useEffect } from 'react';
import { api } from '../../lib/api';
import type { EntityId } from '../../types/api';

interface RunLogDrawerProps {
  runId: EntityId | null;
  isOpen: boolean;
  onClose: () => void;
  onComplete?: () => void;
}

const STEP_ICONS: Record<string, React.ElementType> = {
  fetch: RefreshCw,
  store: Database,
  dedup: GitMerge,
  reconcile: Layers,
  screen: FileSearch,
  pico: Tag,
  diff: Clock
};

export function RunLogDrawer({ runId, isOpen, onClose, onComplete }: RunLogDrawerProps) {
  const client = useQueryClient();
  const { data: run, error, refetch } = useQuery({
    queryKey: ['run', runId], queryFn: () => api.getRun(runId!), enabled: !!runId && isOpen,
    refetchInterval: query => ['queued', 'running'].includes(query.state.data?.status || 'queued') ? 1500 : false,
  });
  useEffect(() => {
    if (run?.status === 'completed' || run?.status === 'failed') {
      void client.invalidateQueries({ queryKey: ['workspace'] });
      onComplete?.();
    }
  }, [run?.status, client, onComplete]);

  if (!isOpen || !runId) return null;

  return (
    <div className="fixed inset-y-0 right-0 z-50 w-full max-w-md bg-slate-900 border-l border-slate-800 shadow-2xl flex flex-col animate-in slide-in-from-right duration-200">
      {/* Drawer Header */}
      <div className="flex items-center justify-between p-4 border-b border-slate-800 bg-slate-950/60">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-xs font-mono font-bold text-brand-400">PIPELINE RUN #{run?.id || runId}</span>
            <span
              className={`px-2 py-0.5 rounded text-[10px] font-mono uppercase font-bold ${run?.status === 'completed'
                  ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                  : run?.status === 'running'
                    ? 'bg-brand-500/20 text-brand-400 border border-brand-500/30'
                    : 'bg-rose-500/20 text-rose-400 border border-rose-500/30'
                }`}
            >
              {run?.status || 'loading'}
            </span>
          </div>
          <p className="text-[11px] text-slate-400 mt-0.5">
            Trigger: <span className="text-slate-200 font-medium">{run?.trigger}</span> | Started: {run?.started_at ? new Date(run.started_at).toLocaleTimeString() : '...'}
          </p>
        </div>
        <button
          aria-label="Close run log"
          onClick={onClose}
          className="p-1 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition"
        >
          <X className="w-5 h-5" />
        </button>
      </div>

      {error && <div role="alert" className="p-4 text-rose-300">{error.message}<button className="ml-3 underline" onClick={() => refetch()}>Retry</button></div>}
      {run?.error && <p role="alert" className="p-4 text-rose-300">{run.error}</p>}
      {/* Steps List */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3 text-xs">
        {run?.steps.map((step, idx) => {
          const Icon = STEP_ICONS[step.step] || Clock;
          const isDone = step.status === 'completed';
          const isRunning = step.status === 'running';

          return (
            <div
              key={step.id || idx}
              className={`p-3 rounded-lg border transition ${isRunning
                  ? 'bg-brand-950/30 border-brand-500/50 shadow-md shadow-brand-950/40'
                  : isDone
                    ? 'bg-slate-950/40 border-slate-800/80'
                    : 'bg-slate-950/20 border-slate-900 opacity-60'
                }`}
            >
              <div className="flex items-center justify-between mb-1.5">
                <div className="flex items-center gap-2">
                  <span className="p-1 rounded bg-slate-800 text-slate-300">
                    <Icon className="w-3.5 h-3.5" />
                  </span>
                  <span className="font-bold text-slate-100 uppercase tracking-wider text-[11px]">
                    Step {idx + 1}: {step.step}
                  </span>
                </div>
                <div>
                  {isRunning && (
                    <span className="flex items-center gap-1 text-[11px] text-brand-400 font-mono">
                      <Loader2 className="w-3 h-3 animate-spin" />
                      <span>running</span>
                    </span>
                  )}
                  {isDone && (
                    <span className="flex items-center gap-1 text-[11px] text-emerald-400 font-mono">
                      <CheckCircle className="w-3 h-3" />
                      <span>done</span>
                    </span>
                  )}
                  {['pending', 'queued'].includes(step.status) && (
                    <span className="text-[10px] text-slate-500 font-mono">pending</span>
                  )}
                </div>
              </div>

              {/* Input / Output summaries */}
              {step.output_summary_json && (
                <div className="mt-2 p-2 rounded bg-slate-900/80 border border-slate-800 font-mono text-[10px] text-slate-300 space-y-0.5">
                  {Object.entries(step.output_summary_json).map(([k, v]) => (
                    <div key={k} className="flex justify-between">
                      <span className="text-slate-400">{k}:</span>
                      <span className="text-brand-300 font-bold">{String(v)}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Drawer Footer */}
      <div className="p-4 border-t border-slate-800 bg-slate-950/60 text-center">
        <button
          onClick={onClose}
          className="w-full py-2 px-4 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold transition"
        >
          Close Log
        </button>
      </div>
    </div>
  );
}
