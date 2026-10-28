import {
  AlertTriangle,
  FileSearch,
  FileSpreadsheet,
  FileText,
  GitCompare,
  GitMerge,
  History,
  Lightbulb,
  Search,
  Tag
} from 'lucide-react';
import React from 'react';

export type NavTab =
  | 'setup'
  | 'search'
  | 'duplicates'
  | 'screening'
  | 'pico'
  | 'history'
  | 'conflicts'
  | 'audit'
  | 'export'
  | 'intelligence';

interface SidebarProps {
  activeTab: NavTab;
  onSelectTab: (tab: NavTab) => void;
  stats?: {
    uncertain_duplicates?: number;
    unscreened?: number;
    conflicts?: number;
  };
}

export function Sidebar({ activeTab, onSelectTab, stats }: SidebarProps) {
  const navItems: Array<{
    id: NavTab;
    step: string;
    label: string;
    icon: React.ElementType;
    badge?: number;
    badgeColor?: string;
  }> = [
      { id: 'setup', step: 'Step 0', label: 'Protocol & Criteria', icon: FileText },
      { id: 'search', step: 'Step 1-2', label: 'Search & Fetch', icon: Search },
      {
        id: 'duplicates',
        step: 'Step 4',
        label: 'Deduplication',
        icon: GitMerge,
        badge: stats?.uncertain_duplicates,
        badgeColor: 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
      },
      {
        id: 'screening',
        step: 'Step 5',
        label: 'Screening Queue',
        icon: FileSearch,
        badge: stats?.unscreened,
        badgeColor: 'bg-brand-500/20 text-brand-300 border border-brand-500/30'
      },
      { id: 'pico', step: 'Step 6', label: 'PICO Extraction', icon: Tag },
      { id: 'intelligence', step: 'Innovation', label: 'Review Intelligence', icon: Lightbulb },
      { id: 'history', step: 'Level 2', label: 'Query Evolution & Diff', icon: GitCompare },
      {
        id: 'conflicts',
        step: 'Loop Guard',
        label: 'Conflicts Workspace',
        icon: AlertTriangle,
        badge: stats?.conflicts,
        badgeColor: 'bg-rose-500/20 text-rose-300 border border-rose-500/30'
      },
      { id: 'audit', step: 'Audit', label: 'Audit Trail', icon: History },
      { id: 'export', step: 'Step 7', label: 'Review & CSV Export', icon: FileSpreadsheet }
    ];

  return (
    <aside className="w-full md:w-64 border-r border-slate-800 bg-slate-950/60 p-4 flex flex-col justify-between shrink-0">
      <div className="grid grid-cols-2 sm:grid-cols-3 md:block md:space-y-1.5 gap-1">
        <div className="col-span-full px-3 py-2 text-[10px] font-bold uppercase tracking-wider text-slate-500 font-mono">
          Systematic Review Pipeline
        </div>

        {navItems.map(item => {
          const Icon = item.icon;
          const isActive = activeTab === item.id;

          return (
            <button
              key={item.id}
              onClick={() => onSelectTab(item.id)}
              className={`w-full text-left px-3 py-2.5 rounded-xl text-xs font-medium transition flex items-center justify-between group ${isActive
                  ? 'bg-brand-600 text-white font-semibold shadow-lg shadow-brand-950/40'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900/80'
                }`}
            >
              <div className="flex items-center gap-3">
                <Icon className={`w-4 h-4 transition ${isActive ? 'text-white' : 'text-slate-400 group-hover:text-brand-400'}`} />
                <div>
                  <div className="leading-tight">{item.label}</div>
                  <div className={`text-[10px] font-mono mt-0.5 ${isActive ? 'text-brand-200' : 'text-slate-500'}`}>
                    {item.step}
                  </div>
                </div>
              </div>

              {item.badge !== undefined && item.badge > 0 && (
                <span className={`px-1.5 py-0.2 rounded font-mono text-[10px] font-bold ${item.badgeColor || 'bg-slate-800 text-slate-300'}`}>
                  {item.badge}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* Footer Info */}
      <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800 text-[11px] text-slate-400 space-y-1">
        <div className="text-slate-300 font-semibold flex items-center justify-between">
          <span>Mini-Rayyan</span>
          <span className="font-mono text-emerald-400 text-[10px]">L1 + L2</span>
        </div>
        <p className="text-[10px] leading-tight text-slate-400">
          PubMed & Europe PMC APIs ? Idempotent runs ? Preserved decisions
        </p>
      </div>
    </aside>
  );
}
