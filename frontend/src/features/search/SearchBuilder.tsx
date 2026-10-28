import { CheckCircle, ChevronRight, Database, Eye, FileText, Play, Search } from 'lucide-react';
import React, { useState } from 'react';
import { NcbiDisclaimer } from '../../components/ui/NcbiDisclaimer';
import { api } from '../../lib/api';
import { useAction, useData, useWorkspace } from '../../lib/workspace';
import type { EntityId } from '../../types/api';
import { PreviewResponse } from '../../types/api';
import { RunLogDrawer } from './RunLogDrawer';

export function SearchBuilder() {
  const { reviewId } = useWorkspace();
  const [queries, setQueries, loadQueries] = useData(['queries'], () => api.getQueries(reviewId));
  const [selectedId, setSelectedId] = useState<EntityId | null>(null);
  const selectedQuery = queries.find(q => q.id === selectedId) || queries[queries.length - 1];


  // Form state
  const [expression, setExpression] = useState('');
  const [source, setSource] = useState<'europe_pmc' | 'pubmed'>('europe_pmc');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [synonymExpansion, setSynonymExpansion] = useState(false);
  const [titleAbstractOnly, setTitleAbstractOnly] = useState(false);

  // Preview state
  const [previewData, setPreviewData] = useState<PreviewResponse | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);

  // In-flight run state
  const [activeRun, setActiveRun] = useState<{ queryId: EntityId; runId: EntityId; } | null>(() => {
    try { return JSON.parse(localStorage.getItem(`evidenceflow_run_${reviewId}`) || 'null'); } catch { return null; }
  });
  const activeRunId = (activeRun && selectedQuery && activeRun.queryId === selectedQuery.id) ? activeRun.runId : null;
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);

  const handleInsertOperator = (op: string) => {
    setExpression(prev => `${prev} ${op} `);
  };

  const handleCreateQuery = useAction(async (e: React.FormEvent) => {
    e.preventDefault();
    if (!expression.trim()) return;
    if (dateFrom && dateTo && dateFrom > dateTo) throw new Error('Date From must be before Date To.');

    const newQ = await api.createQuery(reviewId, {
      expression: expression.trim(),
      source,
      date_from: dateFrom,
      date_to: dateTo,
      options_json: { synonym: synonymExpansion, title_abstract_only: titleAbstractOnly },
      parent_id: selectedQuery?.id || null
    });

    setQueries(prev => [...prev, newQ]);
    setSelectedId(newQ.id);
    setPreviewData(null);
  });

  const handlePreview = useAction(async () => {
    if (!selectedQuery) return;
    try {
      setPreviewLoading(true);
      const res = await api.previewQuery(selectedQuery.id);
      setPreviewData(res);
      // update local hit count
      setQueries(prev => prev.map(q => q.id === selectedQuery.id ? { ...q, status: 'previewed', hit_count: res.hit_count } : q));
    } finally {
      setPreviewLoading(false);
    }
  });

  const handleApproveImport = useAction(async () => {
    if (!selectedQuery) return;
    const res = await api.importQuery(selectedQuery.id);
    const run = { queryId: selectedQuery.id, runId: res.run_id };
    setActiveRun(run);
    localStorage.setItem(`evidenceflow_run_${reviewId}`, JSON.stringify(run));
    setIsDrawerOpen(true);
    // refresh queries
    await loadQueries();
  });

  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      {/* Top Banner */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 p-5 rounded-xl bg-slate-900/60 border border-slate-800 shadow-xl">
        <div>
          <div className="flex items-center gap-2">
            <span className="px-2 py-0.5 rounded text-[11px] font-bold font-mono uppercase bg-brand-500/20 text-brand-300 border border-brand-500/30">
              Steps 1 & 2: Search & Fetch
            </span>
            <span className="text-xs text-slate-400 font-mono">Immutable Query Versions</span>
          </div>
          <h2 className="text-xl font-bold text-slate-100 mt-1">Literature Database Query Builder</h2>
          <p className="text-xs text-slate-400">
            Formulate Boolean queries against PubMed and Europe PMC APIs. Preview hits before approving import.
          </p>
        </div>

        {/* Existing Query Version Selector Tabs */}
        <div className="flex items-center gap-1 p-1 bg-slate-950 rounded-lg border border-slate-800 max-w-full overflow-x-auto">
          {queries.map(q => (
            <button
              key={q.id}
              onClick={() => {
                setSelectedId(q.id);
                setPreviewData(null);
              }}
              className={`px-3 py-1.5 rounded-md text-xs font-medium font-mono whitespace-nowrap transition ${selectedQuery?.id === q.id
                  ? 'bg-brand-600 text-white shadow'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
                }`}
            >
              v{q.version_no} ({q.hit_count != null ? `${q.hit_count} hits` : q.status})
            </button>
          ))}
        </div>
      </div>

      {/* NCBI Disclaimer if PubMed is selected */}
      {(source === 'pubmed' || selectedQuery?.source === 'pubmed') && (
        <NcbiDisclaimer />
      )}

      {/* Main Grid: Form + Version Details */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Query Builder Form */}
        <div className="lg:col-span-7 p-6 rounded-xl bg-slate-900/60 border border-slate-800 shadow-lg space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-slate-800">
            <h3 className="text-sm font-bold text-slate-100 flex items-center gap-2">
              <Search className="w-4 h-4 text-brand-400" />
              <span>Define New Query Version</span>
            </h3>
            <span className="text-[11px] text-slate-400 font-mono">v{queries.length + 1} Draft</span>
          </div>

          <form onSubmit={handleCreateQuery} className="space-y-4 text-xs">
            {/* Expression */}
            <div className="space-y-1.5">
              <div className="flex items-center justify-between">
                <label className="font-semibold text-slate-300">Boolean Search Expression:</label>
                <div className="flex items-center gap-1">
                  <button
                    type="button"
                    onClick={() => handleInsertOperator('AND')}
                    className="px-2 py-0.5 rounded bg-slate-800 hover:bg-slate-700 text-brand-300 font-mono font-bold text-[10px]"
                  >
                    + AND
                  </button>
                  <button
                    type="button"
                    onClick={() => handleInsertOperator('OR')}
                    className="px-2 py-0.5 rounded bg-slate-800 hover:bg-slate-700 text-brand-300 font-mono font-bold text-[10px]"
                  >
                    + OR
                  </button>
                  <button
                    type="button"
                    onClick={() => handleInsertOperator('NOT')}
                    className="px-2 py-0.5 rounded bg-slate-800 hover:bg-slate-700 text-rose-300 font-mono font-bold text-[10px]"
                  >
                    + NOT
                  </button>
                </div>
              </div>
              <textarea
                value={expression}
                onChange={e => setExpression(e.target.value)}
                required
                className="w-full px-3 py-2.5 bg-slate-950 border border-slate-800 rounded-lg text-slate-100 font-mono text-xs focus:outline-none focus:border-brand-500 min-h-[85px] leading-relaxed"
                aria-label="Boolean Search Expression" placeholder="Enter a literature search expression"
              />
            </div>

            {/* Source & Dates */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <div>
                <label className="font-semibold text-slate-300 block mb-1">Literature Database:</label>
                <select
                  value={source}
                  onChange={e => setSource(e.target.value as 'europe_pmc' | 'pubmed')}
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-slate-200"
                >
                  <option value="europe_pmc">Europe PMC (REST API)</option>
                  <option value="pubmed">PubMed (NCBI EFetch)</option>
                </select>
              </div>
              <div>
                <label className="font-semibold text-slate-300 block mb-1">Date From:</label>
                <input
                  type="date"
                  value={dateFrom}
                  onChange={e => setDateFrom(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-slate-200 font-mono"
                />
              </div>
              <div>
                <label className="font-semibold text-slate-300 block mb-1">Date To:</label>
                <input
                  type="date"
                  value={dateTo}
                  onChange={e => setDateTo(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-slate-200 font-mono"
                />
              </div>
            </div>

            {/* Options */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-1">
              <div className="flex items-center gap-2 p-2.5 rounded-lg bg-slate-950/60 border border-slate-800">
                <input
                  type="checkbox"
                  id="synonymToggle"
                  checked={synonymExpansion}
                  onChange={e => setSynonymExpansion(e.target.checked)}
                  className="rounded border-slate-700 text-brand-600 focus:ring-0 bg-slate-900 w-4 h-4"
                />
                <label htmlFor="synonymToggle" className="cursor-pointer text-slate-300">
                  <span className="font-semibold block">MeSH Synonym Expansion</span>
                  <span className="text-[10px] text-slate-400 block">Use source-supported synonym expansion</span>
                </label>
              </div>

              <label className="p-2.5 rounded-lg bg-slate-950 border border-slate-800 flex gap-2 items-center">
                <input type="checkbox" checked={titleAbstractOnly} onChange={e => setTitleAbstractOnly(e.target.checked)} />
                Titles and abstracts only
              </label>
            </div>

            {/* Submit create version */}
            <div className="flex justify-end pt-2">
              <button
                type="submit"
                className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-brand-600 hover:bg-brand-500 text-white font-semibold shadow transition"
              >
                <span>Save as Version v{queries.length + 1}</span>
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </form>
        </div>

        {/* Right Column: Selected Version Inspector & Execution */}
        <div className="lg:col-span-5 p-6 rounded-xl bg-slate-900/60 border border-slate-800 shadow-lg space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-slate-800">
            <h3 className="text-sm font-bold text-slate-100 flex items-center gap-2">
              <Database className="w-4 h-4 text-emerald-400" />
              <span>Active Query Version Inspector</span>
            </h3>
            {selectedQuery && (
              <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-slate-800 text-slate-300 border border-slate-700">
                v{selectedQuery.version_no} {selectedQuery.status}
              </span>
            )}
          </div>

          {selectedQuery ? (
            <div className="space-y-4 text-xs">
              <div className="p-3 rounded-lg bg-slate-950/70 border border-slate-800/80 space-y-1.5">
                <div className="text-[10px] uppercase font-mono tracking-wider text-slate-400">Expression</div>
                <div className="text-slate-100 font-mono text-xs break-words">{selectedQuery.expression}</div>
                <div className="flex items-center gap-3 pt-1 text-[11px] text-slate-400 font-mono">
                  <span>Source: <strong className="text-brand-300">{selectedQuery.source}</strong></span>
                  <span>Range: {selectedQuery.date_from} to {selectedQuery.date_to}</span>
                </div>
              </div>

              {/* Status and Hits */}
              <div className="grid grid-cols-2 gap-3">
                <div className="p-3 rounded-lg bg-slate-950/70 border border-slate-800/80">
                  <span className="text-[10px] text-slate-400 uppercase tracking-wider block">Estimated Hits</span>
                  <span className="text-lg font-bold text-slate-100 font-mono mt-0.5 block">
                    {selectedQuery.hit_count != null ? selectedQuery.hit_count.toLocaleString() : 'Not previewed'}
                  </span>
                </div>
                <div className="p-3 rounded-lg bg-slate-950/70 border border-slate-800/80">
                  <span className="text-[10px] text-slate-400 uppercase tracking-wider block">Imported Records</span>
                  <span className="text-lg font-bold text-emerald-400 font-mono mt-0.5 block">
                    {selectedQuery.imported_count !== null ? `${selectedQuery.imported_count} stored` : 'Pending approval'}
                  </span>
                </div>
              </div>

              {/* Action Buttons: Preview & Import */}
              <div className="space-y-2 pt-2">
                <button
                  type="button"
                  onClick={handlePreview}
                  disabled={previewLoading}
                  className="w-full flex items-center justify-center gap-2 py-2.5 px-4 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 font-semibold shadow transition"
                >
                  <Eye className="w-4 h-4 text-brand-400" />
                  <span>{previewLoading ? 'Querying API hit count...' : 'Preview Hits & Sample Abstracts'}</span>
                </button>

                <button
                  type="button"
                  onClick={handleApproveImport}
                  disabled={selectedQuery.status === 'draft' || previewLoading}
                  className="w-full flex items-center justify-center gap-2 py-2.5 px-4 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-semibold shadow-lg shadow-emerald-950/50 transition"
                >
                  <Play className="w-4 h-4" />
                  <span>
                    {selectedQuery.status === 'imported'
                      ? 'Re-Run Import Pipeline (Idempotent)'
                      : 'Approve & Import Abstracts (Run Pipeline)'}
                  </span>
                </button>
              </div>

              {/* View Run Drawer button */}
              {activeRunId && (
                <button
                  type="button"
                  onClick={() => setIsDrawerOpen(true)}
                  className="w-full py-1.5 text-center text-brand-400 hover:text-brand-300 text-xs font-mono underline"
                >
                  View Active Run #{activeRunId} Progress & Logs
                </button>
              )}
            </div>
          ) : (
            <div className="text-center py-12 text-slate-500 text-xs">
              No query version selected. Create a draft or pick an existing version.
            </div>
          )}
        </div>
      </div>

      {/* Preview Sample Abstracts Table */}
      {previewData && (
        <div className="p-6 rounded-xl bg-slate-900/60 border border-slate-800 shadow-lg space-y-4 animate-in fade-in duration-150">
          <div className="flex items-center justify-between pb-3 border-b border-slate-800">
            <div>
              <h3 className="text-sm font-bold text-slate-100 flex items-center gap-2">
                <FileText className="w-4 h-4 text-brand-400" />
                <span>Search Preview: Top Sample Abstracts</span>
              </h3>
              <p className="text-xs text-slate-400 mt-0.5">
                Total Hits: <span className="text-emerald-400 font-bold font-mono">{previewData.hit_count.toLocaleString()}</span>. Showing sample preview records before downloading into database.
              </p>
            </div>
            <button
              onClick={handleApproveImport}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-emerald-600 hover:bg-emerald-500 text-white shadow transition"
            >
              <CheckCircle className="w-3.5 h-3.5" />
              <span>Approve & Import</span>
            </button>
          </div>

          {previewData.warnings?.map((warning, i) => <p key={i} className="text-amber-300 text-xs">{warning}</p>)}
          <p className="text-xs text-slate-400">Import size is controlled by the backend configuration. Run logs report truncation and the actual record count.</p>
          <div className="space-y-3">
            {previewData.sample_records.map(r => (
              <div key={`${r.source}:${r.source_record_id}`} className="p-3.5 rounded-lg bg-slate-950/70 border border-slate-800 space-y-1.5">
                <div className="flex items-start justify-between gap-2">
                  <h4 className="text-xs font-bold text-slate-200">{r.title}</h4>
                  <span className="text-[10px] px-2 py-0.5 rounded bg-slate-800 font-mono text-slate-400 flex-shrink-0">
                    {r.source}
                  </span>
                </div>
                <div className="text-[11px] text-slate-400 flex items-center gap-2 font-mono">
                  <span>{(r.authors || []).slice(0, 2).map(a => typeof a === 'string' ? a : a.full_name).join(', ')}{((r.authors || []).length > 2) ? ' et al.' : ''}</span>
                  <span>?</span>
                  <span>{r.year}</span>
                  <span>?</span>
                  <span className="italic">{r.journal}</span>
                  {r.doi && <span>? DOI: {r.doi}</span>}
                </div>
                {r.abstract && (
                  <p className="text-xs text-slate-300/90 leading-relaxed line-clamp-2">
                    {r.abstract}
                  </p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Slide-out Run Log Drawer */}
      <RunLogDrawer
        runId={activeRunId}
        isOpen={isDrawerOpen}
        onClose={() => setIsDrawerOpen(false)}
      />
    </div>
  );
}
