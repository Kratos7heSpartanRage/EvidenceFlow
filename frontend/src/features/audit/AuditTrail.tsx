import React, { useState, useEffect } from 'react';
import { api } from '../../lib/api';
import { AuditEvent } from '../../types/api';
import { ShieldCheck, History, User, Bot, ChevronDown, ChevronRight, FileText, Search, Clock } from 'lucide-react';

export function AuditTrail() {
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [actorFilter, setActorFilter] = useState<'all' | 'reviewer' | 'system'>('all');
  const [search, setSearch] = useState('');

  const loadAudit = async () => {
    try {
      setLoading(true);
      const data = await api.getAuditEvents(1);
      setEvents(data);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAudit();
  }, []);

  const filteredEvents = events.filter(e => {
    if (actorFilter === 'system' && !e.actor.startsWith('system')) return false;
    if (actorFilter === 'reviewer' && !e.actor.startsWith('reviewer:')) return false;
    if (search.trim()) {
      const q = search.toLowerCase();
      return e.action.toLowerCase().includes(q) || e.actor.toLowerCase().includes(q) || e.entity_type.toLowerCase().includes(q);
    }
    return true;
  });

  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      {/* Top Banner */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 p-5 rounded-xl bg-slate-900/60 border border-slate-800 shadow-xl">
        <div>
          <div className="flex items-center gap-2">
            <span className="px-2 py-0.5 rounded text-[11px] font-bold font-mono uppercase bg-brand-500/20 text-brand-300 border border-brand-500/30">
              Auditability & Governance
            </span>
            <span className="text-xs text-slate-400 font-mono">Append-Only Immutability</span>
          </div>
          <h2 className="text-xl font-bold text-slate-100 mt-1">Audit Trail & Provenance Log</h2>
          <p className="text-xs text-slate-400">
            Cryptographically verifiable audit log. Every human override, exclusion rationale, and pipeline run step is preserved.
          </p>
        </div>

        {/* Filter Tabs */}
        <div className="flex items-center gap-1.5 p-1 bg-slate-950 rounded-lg border border-slate-800 text-xs">
          <button
            onClick={() => setActorFilter('all')}
            className={`px-3 py-1.5 rounded-md font-medium transition ${
              actorFilter === 'all' ? 'bg-brand-600 text-white shadow' : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            All Events ({events.length})
          </button>
          <button
            onClick={() => setActorFilter('reviewer')}
            className={`px-3 py-1.5 rounded-md font-medium transition ${
              actorFilter === 'reviewer' ? 'bg-brand-600 text-white shadow' : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            Human Reviewers
          </button>
          <button
            onClick={() => setActorFilter('system')}
            className={`px-3 py-1.5 rounded-md font-medium transition ${
              actorFilter === 'system' ? 'bg-brand-600 text-white shadow' : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            System Runs
          </button>
        </div>
      </div>

      {/* Main Audit Log Table */}
      <div className="p-6 rounded-xl bg-slate-900/60 border border-slate-800 shadow-lg space-y-4">
        <div className="flex items-center justify-between pb-3 border-b border-slate-800 text-xs">
          <div className="flex items-center gap-2 text-slate-200 font-bold">
            <History className="w-4 h-4 text-brand-400" />
            <span>Event History ({filteredEvents.length} events logged)</span>
          </div>
          <div className="relative w-64">
            <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Search actions or actors..."
              value={search}
              onChange={e => setSearch(e.target.value)}
              className="w-full pl-8 pr-3 py-1.5 bg-slate-950 border border-slate-800 rounded-lg text-slate-200 text-xs focus:outline-none focus:border-brand-500"
            />
          </div>
        </div>

        {filteredEvents.length === 0 ? (
          <div className="text-center py-12 text-slate-500 text-xs">
            No audit events found matching the search filter.
          </div>
        ) : (
          <div className="space-y-2">
            {filteredEvents.map(evt => {
              const isExpanded = expandedId === evt.id;
              const isSystem = evt.actor.startsWith('system');

              return (
                <div
                  key={evt.id}
                  className="rounded-xl border border-slate-800/80 bg-slate-950/60 overflow-hidden text-xs transition hover:border-slate-700"
                >
                  <div
                    onClick={() => setExpandedId(isExpanded ? null : evt.id)}
                    className="p-3.5 flex items-center justify-between gap-3 cursor-pointer select-none"
                  >
                    <div className="flex items-center gap-3">
                      <div
                        className={`p-1.5 rounded-lg border ${
                          isSystem
                            ? 'bg-slate-800 border-slate-700 text-slate-400'
                            : 'bg-brand-500/10 border-brand-500/20 text-brand-400'
                        }`}
                      >
                        {isSystem ? <Bot className="w-4 h-4" /> : <User className="w-4 h-4" />}
                      </div>

                      <div>
                        <div className="flex items-center gap-2 font-mono">
                          <span className="font-bold text-slate-100">{evt.action}</span>
                          <span className="text-[10px] px-1.5 py-0.2 rounded bg-slate-800 text-slate-400">
                            {evt.entity_type} #{evt.entity_id}
                          </span>
                        </div>
                        <div className="text-[11px] text-slate-400 font-sans mt-0.5">
                          Actor: <strong className="text-slate-300 font-mono">{evt.actor}</strong>
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center gap-3 font-mono text-[11px] text-slate-400">
                      <span>{new Date(evt.created_at).toLocaleString()}</span>
                      {isExpanded ? <ChevronDown className="w-4 h-4 text-slate-400" /> : <ChevronRight className="w-4 h-4 text-slate-600" />}
                    </div>
                  </div>

                  {/* Expanded JSON before / after view */}
                  {isExpanded && (
                    <div className="p-4 border-t border-slate-800/80 bg-slate-950 space-y-3 font-mono text-[11px]">
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div className="space-y-1">
                          <span className="text-[10px] uppercase font-bold text-slate-400 block font-sans">
                            State Before Mutation
                          </span>
                          <pre className="p-3 rounded-lg bg-slate-900 border border-slate-800 text-slate-400 overflow-x-auto max-h-48 leading-relaxed">
                            {evt.before_json ? JSON.stringify(evt.before_json, null, 2) : 'null (Created)'}
                          </pre>
                        </div>

                        <div className="space-y-1">
                          <span className="text-[10px] uppercase font-bold text-emerald-400 block font-sans">
                            State After Mutation
                          </span>
                          <pre className="p-3 rounded-lg bg-slate-900 border border-slate-800 text-emerald-300 overflow-x-auto max-h-48 leading-relaxed">
                            {evt.after_json ? JSON.stringify(evt.after_json, null, 2) : 'null'}
                          </pre>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
