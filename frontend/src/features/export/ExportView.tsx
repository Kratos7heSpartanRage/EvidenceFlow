import React, { useState, useEffect } from 'react';
import { api } from '../../lib/api';
import { LiteratureRecord, PicoAnnotation, Conflict } from '../../types/api';
import { Download, FileSpreadsheet, ShieldAlert, CheckCircle, ExternalLink, Sparkles } from 'lucide-react';

export function ExportView() {
  const [records, setRecords] = useState<LiteratureRecord[]>([]);
  const [annotations, setAnnotations] = useState<PicoAnnotation[]>([]);
  const [conflicts, setConflicts] = useState<Conflict[]>([]);
  const [loading, setLoading] = useState(true);

  const loadData = async () => {
    try {
      setLoading(true);
      const res = await api.getRecords(1, { decision: 'include', show_hidden: false });
      setRecords(res.items);
      const confs = await api.getConflicts(1);
      setConflicts(confs);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleDownloadCsv = async () => {
    const csvContent = await api.exportCsv(1);
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.setAttribute('href', url);
    link.setAttribute('download', `evidenceflow_included_studies_${new Date().toISOString().slice(0, 10)}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const openConflictsCount = conflicts.filter(c => c.status === 'open').length;

  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      {/* Top Banner */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 p-5 rounded-xl bg-slate-900/60 border border-slate-800 shadow-xl">
        <div>
          <div className="flex items-center gap-2">
            <span className="px-2 py-0.5 rounded text-[11px] font-bold font-mono uppercase bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
              Step 7: Final Synthesis
            </span>
            <span className="text-xs text-slate-400 font-mono">Included Studies with PICO Evidence</span>
          </div>
          <h2 className="text-xl font-bold text-slate-100 mt-1">Systematic Review CSV Export</h2>
          <p className="text-xs text-slate-400">
            Export verified included representative studies, extracted PICO tags, and complete decision provenance.
          </p>
        </div>

        {/* Download CSV button */}
        <button
          onClick={handleDownloadCsv}
          className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs shadow-lg shadow-emerald-950/50 transition cursor-pointer active:scale-95"
        >
          <Download className="w-4 h-4" />
          <span>Download CSV Export</span>
        </button>
      </div>

      {/* Warning banner if open conflicts exist */}
      {openConflictsCount > 0 && (
        <div className="flex items-start gap-3 p-4 rounded-xl bg-rose-950/40 border border-rose-800/50 text-rose-200 text-xs shadow">
          <ShieldAlert className="w-5 h-5 text-rose-400 flex-shrink-0 mt-0.5" />
          <div className="space-y-1">
            <div className="font-bold text-rose-300">
              Warning: {openConflictsCount} Unresolved Group Conflict{openConflictsCount === 1 ? '' : 's'} Present
            </div>
            <p className="leading-relaxed text-rose-200/90">
              Groups with conflicting reviewer decisions are temporarily excluded from this synthesis export until resolved in the Conflicts Workspace.
            </p>
          </div>
        </div>
      )}

      {/* Synthesis Preview Table */}
      <div className="p-6 rounded-xl bg-slate-900/60 border border-slate-800 shadow-lg space-y-4">
        <div className="flex items-center justify-between pb-3 border-b border-slate-800 text-xs">
          <div className="flex items-center gap-2 text-slate-200 font-bold">
            <FileSpreadsheet className="w-4 h-4 text-emerald-400" />
            <span>Export Table Preview ({records.length} Included Representative Studies)</span>
          </div>
          <span className="text-slate-400 font-mono text-[11px]">Format: Comma-Separated Values (RFC 4180)</span>
        </div>

        {records.length === 0 ? (
          <div className="text-center py-12 text-slate-500 text-xs">
            No included studies ready for synthesis. Review and mark studies as Include in Step 5.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-slate-300">
              <thead className="bg-slate-950/80 text-[11px] text-slate-400 uppercase tracking-wider border-b border-slate-800 font-mono">
                <tr>
                  <th className="py-2.5 px-3">ID</th>
                  <th className="py-2.5 px-4 min-w-[200px]">Title & Journal</th>
                  <th className="py-2.5 px-3">First Author</th>
                  <th className="py-2.5 px-3">Year</th>
                  <th className="py-2.5 px-3">Identifiers</th>
                  <th className="py-2.5 px-3">Decision</th>
                  <th className="py-2.5 px-4 min-w-[140px]">Reviewer Rationale</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {records.map(r => (
                  <tr key={r.id} className="hover:bg-slate-800/30 transition">
                    <td className="py-3 px-3 font-mono text-slate-400">#{r.id}</td>
                    <td className="py-3 px-4">
                      <div className="font-semibold text-slate-100">{r.title}</div>
                      <div className="text-[11px] text-slate-400 italic mt-0.5">{r.journal}</div>
                    </td>
                    <td className="py-3 px-3 text-slate-300">{r.first_author_norm || r.authors_json[0]}</td>
                    <td className="py-3 px-3 font-mono text-slate-300">{r.year}</td>
                    <td className="py-3 px-3 font-mono text-[10px] space-y-0.5 text-slate-400">
                      {r.doi_norm && <div>DOI: {r.doi_norm}</div>}
                      {r.pmid && <div>PMID: {r.pmid}</div>}
                    </td>
                    <td className="py-3 px-3">
                      <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
                        {r.current_decision?.decision || 'Include'}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-slate-300 text-[11px] leading-relaxed italic">
                      "{r.current_decision?.reason_text || 'Standard protocol inclusion'}"
                      <div className="text-[10px] text-slate-500 font-mono not-italic mt-0.5">
                        by {r.current_decision?.reviewer || 'Reviewer'}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
