import {
  Activity,
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
  | 'runs'
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
    included?: number;
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
    { id: 'setup', step: '00', label: 'Protocol & Criteria', icon: FileText },
    { id: 'search', step: '01', label: 'Search & Fetch', icon: Search },
    { id: 'runs', step: '02', label: 'Pipeline Runs', icon: Activity },
    {
      id: 'duplicates',
      step: '03',
      label: 'Deduplication',
      icon: GitMerge,
      badge: stats?.uncertain_duplicates,
      badgeColor: 'bg-amber-100 dark:bg-amber-500/20 text-amber-700 dark:text-amber-300 border border-amber-300 dark:border-amber-500/30'
    },
    {
      id: 'screening',
      step: '04',
      label: 'Screening Queue',
      icon: FileSearch,
      badge: stats?.unscreened,
      badgeColor: 'bg-teal-100 dark:bg-teal-500/20 text-teal-700 dark:text-teal-300 border border-teal-300 dark:border-teal-500/30'
    },
    { id: 'pico', step: '05', label: 'PICO Extraction', icon: Tag },
    { id: 'intelligence', step: 'AI', label: 'Review Intelligence', icon: Lightbulb },
    { id: 'history', step: 'L2', label: 'Evolution & Diff', icon: GitCompare },
    {
      id: 'conflicts',
      step: 'LG',
      label: 'Conflicts Workspace',
      icon: AlertTriangle,
      badge: stats?.conflicts,
      badgeColor: 'bg-rose-100 dark:bg-rose-500/20 text-rose-700 dark:text-rose-300 border border-rose-300 dark:border-rose-500/30'
    },
    { id: 'audit', step: 'AD', label: 'Audit Trail', icon: History },
    { id: 'export', step: '06', label: 'Review & CSV Export', icon: FileSpreadsheet }
  ];

  return (
    <aside className="w-full md:w-64 border-r border-slate-200/80 dark:border-slate-800/80 bg-white/50 dark:bg-slate-950/50 backdrop-blur-md p-3 md:p-4 flex flex-col justify-between shrink-0 transition-colors duration-300">
      <div className="space-y-1">
        <div className="px-3 py-1.5 text-[10px] font-bold uppercase tracking-wider text-slate-400 dark:text-slate-500 font-mono flex items-center justify-between">
          <span>Review Pipeline</span>
          <span className="text-[9px] text-teal-600 dark:text-teal-400 font-semibold">GATES 1–5</span>
        </div>

        <nav className="space-y-1" aria-label="Pipeline navigation">
          {navItems.map(item => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;

            return (
              <button
                key={item.id}
                onClick={() => onSelectTab(item.id)}
                className={`w-full text-left px-3 py-2 rounded-xl text-xs font-medium transition-all duration-150 flex items-center justify-between group ${
                  isActive
                    ? 'bg-teal-600 text-white font-semibold shadow-md shadow-teal-900/20 translate-x-0.5'
                    : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200 hover:bg-slate-100/80 dark:hover:bg-slate-900/80'
                }`}
              >
                <div className="flex items-center gap-2.5">
                  <span
                    className={`text-[10px] font-mono px-1.5 py-0.5 rounded transition ${
                      isActive
                        ? 'bg-teal-700 text-teal-100 font-bold'
                        : 'bg-slate-200/70 dark:bg-slate-800 text-slate-500 dark:text-slate-400 group-hover:bg-slate-300 dark:group-hover:bg-slate-700'
                    }`}
                  >
                    {item.step}
                  </span>
                  <div className="flex items-center gap-2">
                    <Icon
                      className={`w-4 h-4 transition ${
                        isActive
                          ? 'text-white'
                          : 'text-slate-400 group-hover:text-teal-600 dark:group-hover:text-teal-400'
                      }`}
                    />
                    <span className="leading-tight">{item.label}</span>
                  </div>
                </div>

                {item.badge !== undefined && item.badge > 0 && (
                  <span
                    className={`px-1.5 py-0.5 rounded font-mono text-[10px] font-bold ${
                      isActive ? 'bg-white text-teal-700' : item.badgeColor || 'bg-slate-200 dark:bg-slate-800 text-slate-700 dark:text-slate-300'
                    }`}
                  >
                    {item.badge}
                  </span>
                )}
              </button>
            );
          })}
        </nav>
      </div>

      {/* Footer Info Pill */}
      <div className="mt-4 p-3 rounded-xl bg-slate-100/70 dark:bg-slate-900/60 border border-slate-200/80 dark:border-slate-800/80 text-[11px] text-slate-600 dark:text-slate-400 space-y-1 transition-colors">
        <div className="text-slate-800 dark:text-slate-200 font-semibold flex items-center justify-between text-xs">
          <span>EvidenceFlow</span>
          <span className="font-mono text-teal-600 dark:text-teal-400 text-[10px] font-bold px-1.5 py-0.5 rounded bg-teal-50 dark:bg-teal-950/80 border border-teal-200 dark:border-teal-800">
            Hackathon
          </span>
        </div>
        <p className="text-[10px] leading-tight text-slate-500 dark:text-slate-400">
          Auditable Boolean loop with guaranteed decision preservation.
        </p>
      </div>
    </aside>
  );
}
