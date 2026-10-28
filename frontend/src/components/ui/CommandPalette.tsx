import React, { useEffect, useState } from 'react';
import {
  Activity,
  AlertTriangle,
  ArrowRight,
  Download,
  FileSearch,
  FileText,
  GitCompare,
  GitMerge,
  History,
  Lightbulb,
  Moon,
  Search,
  Sun,
  Tag,
  X
} from 'lucide-react';
import { NavTab } from '../../app/Sidebar';

interface CommandPaletteProps {
  isOpen: boolean;
  onClose: () => void;
  onSelectTab: (tab: NavTab) => void;
  onToggleTheme: () => void;
  isDark: boolean;
  onBackToLanding?: () => void;
}

interface CommandItem {
  id: string;
  category: 'Navigation' | 'Actions';
  label: string;
  detail: string;
  icon: React.ElementType;
  tab?: NavTab;
  action?: () => void;
}

export function CommandPalette({
  isOpen,
  onClose,
  onSelectTab,
  onToggleTheme,
  isDark,
  onBackToLanding
}: CommandPaletteProps) {
  const [query, setQuery] = useState('');
  const [selectedIndex, setSelectedIndex] = useState(0);

  const items: CommandItem[] = [
    {
      id: 'setup',
      category: 'Navigation',
      label: 'Step 0: Protocol & Criteria',
      detail: 'Configure PICO question and review eligibility criteria',
      icon: FileText,
      tab: 'setup'
    },
    {
      id: 'search',
      category: 'Navigation',
      label: 'Step 1-2: Search & Fetch',
      detail: 'Build Boolean queries against PubMed & Europe PMC',
      icon: Search,
      tab: 'search'
    },
    {
      id: 'runs',
      category: 'Navigation',
      label: 'Step 3: Pipeline Runs',
      detail: 'Inspect ingestion, deduplication, and screening run execution logs',
      icon: Activity,
      tab: 'runs'
    },
    {
      id: 'duplicates',
      category: 'Navigation',
      label: 'Step 4: Deduplication Queue',
      detail: 'Review uncertain candidate pairs and override matches',
      icon: GitMerge,
      tab: 'duplicates'
    },
    {
      id: 'screening',
      category: 'Navigation',
      label: 'Step 5: Screening Queue',
      detail: 'Screen title and abstracts with keyboard shortcuts (I, E, M)',
      icon: FileSearch,
      tab: 'screening'
    },
    {
      id: 'pico',
      category: 'Navigation',
      label: 'Step 6: PICO Extraction',
      detail: 'Review and curate Population, Intervention, Comparator, and Outcome spans',
      icon: Tag,
      tab: 'pico'
    },
    {
      id: 'intelligence',
      category: 'Navigation',
      label: 'Innovation: Review Intelligence',
      detail: 'Surface old exclusions affected by criteria changes and multi-report study families',
      icon: Lightbulb,
      tab: 'intelligence'
    },
    {
      id: 'history',
      category: 'Navigation',
      label: 'Level 2: Query Evolution & Diff View',
      detail: 'Compare query iterations and verify zero loss of human decisions',
      icon: GitCompare,
      tab: 'history'
    },
    {
      id: 'conflicts',
      category: 'Navigation',
      label: 'Multi-Reviewer Conflicts',
      detail: 'Arbitrate inter-reviewer disagreements and bridging conflicts',
      icon: AlertTriangle,
      tab: 'conflicts'
    },
    {
      id: 'audit',
      category: 'Navigation',
      label: 'Audit Trail & Event Ledger',
      detail: 'View append-only cryptographic event logs with state diffs',
      icon: History,
      tab: 'audit'
    },
    {
      id: 'export',
      category: 'Navigation',
      label: 'PRISMA & CSV Export',
      detail: 'Download RFC-4180 CSV of included canonical studies',
      icon: Download,
      tab: 'export'
    },
    {
      id: 'toggle-theme',
      category: 'Actions',
      label: isDark ? 'Switch to Light Theme' : 'Switch to Dark Theme',
      detail: 'Toggle between clean editorial light mode and low-glare dark mode',
      icon: isDark ? Sun : Moon,
      action: onToggleTheme
    },
    ...(onBackToLanding
      ? [
          {
            id: 'landing',
            category: 'Actions' as const,
            label: 'Return to Landing Overview',
            detail: 'View the product introduction and architecture overview',
            icon: ArrowRight,
            action: onBackToLanding
          }
        ]
      : [])
  ];

  const filtered = items.filter(
    item =>
      item.label.toLowerCase().includes(query.toLowerCase()) ||
      item.detail.toLowerCase().includes(query.toLowerCase())
  );

  useEffect(() => {
    setSelectedIndex(0);
  }, [query]);

  useEffect(() => {
    if (!isOpen) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        setSelectedIndex(prev => (prev + 1) % (filtered.length || 1));
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        setSelectedIndex(prev => (prev - 1 + (filtered.length || 1)) % (filtered.length || 1));
      } else if (e.key === 'Enter') {
        e.preventDefault();
        const selected = filtered[selectedIndex];
        if (selected) {
          if (selected.tab) {
            onSelectTab(selected.tab);
          } else if (selected.action) {
            selected.action();
          }
          onClose();
        }
      } else if (e.key === 'Escape') {
        e.preventDefault();
        onClose();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, filtered, selectedIndex, onSelectTab, onClose]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-20 px-4 bg-slate-950/60 dark:bg-black/75 backdrop-blur-sm animate-in fade-in duration-150">
      <div
        className="w-full max-w-xl rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-2xl overflow-hidden flex flex-col text-slate-900 dark:text-slate-100 animate-in zoom-in-95 duration-150"
        role="dialog"
        aria-modal="true"
        aria-label="Command Palette"
      >
        {/* Search Input Bar */}
        <div className="flex items-center px-4 py-3.5 border-b border-slate-200 dark:border-slate-800 gap-3 bg-slate-50/80 dark:bg-slate-950/60">
          <Search className="w-4 h-4 text-teal-600 dark:text-teal-400 shrink-0" />
          <input
            type="text"
            placeholder="Type a command or jump to step..."
            className="w-full bg-transparent text-sm text-slate-900 dark:text-slate-100 placeholder-slate-400 focus:outline-none"
            value={query}
            onChange={e => setQuery(e.target.value)}
            autoFocus
          />
          <kbd className="hidden sm:inline-block px-1.5 py-0.5 text-[10px] font-mono text-slate-500 dark:text-slate-400 bg-slate-200 dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded">
            ESC
          </kbd>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 p-1 rounded-md hover:bg-slate-100 dark:hover:bg-slate-800"
            aria-label="Close command palette"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Results List */}
        <div className="max-h-96 overflow-y-auto p-2 divide-y divide-slate-100 dark:divide-slate-800/40">
          {filtered.length === 0 ? (
            <div className="py-8 text-center text-sm text-slate-400">
              No matching commands or sections found.
            </div>
          ) : (
            filtered.map((item, idx) => {
              const Icon = item.icon;
              const isSelected = idx === selectedIndex;
              return (
                <button
                  key={item.id}
                  onClick={() => {
                    if (item.tab) onSelectTab(item.tab);
                    if (item.action) item.action();
                    onClose();
                  }}
                  onMouseEnter={() => setSelectedIndex(idx)}
                  className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-left transition-colors ${
                    isSelected
                      ? 'bg-teal-50 dark:bg-teal-950/40 text-teal-900 dark:text-teal-200 border border-teal-200 dark:border-teal-500/30'
                      : 'text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800/60'
                  }`}
                >
                  <div
                    className={`w-7 h-7 rounded-lg flex items-center justify-center shrink-0 ${
                      isSelected
                        ? 'bg-teal-100 dark:bg-teal-500/20 text-teal-700 dark:text-teal-300'
                        : 'bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400'
                    }`}
                  >
                    <Icon className="w-3.5 h-3.5" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="text-xs font-semibold tracking-tight">{item.label}</div>
                    <div className="text-[11px] text-slate-500 dark:text-slate-400 truncate">{item.detail}</div>
                  </div>
                  {isSelected && (
                    <kbd className="hidden sm:inline-block px-1.5 py-0.5 text-[10px] font-mono text-teal-700 dark:text-teal-300 bg-teal-100 dark:bg-teal-950/60 border border-teal-200 dark:border-teal-500/40 rounded">
                      ↵
                    </kbd>
                  )}
                </button>
              );
            })
          )}
        </div>

        {/* Footer shortcuts */}
        <div className="px-4 py-2 border-t border-slate-200 dark:border-slate-800 bg-slate-50/80 dark:bg-slate-950/60 text-[11px] text-slate-500 dark:text-slate-400 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span>
              <kbd className="font-mono bg-slate-200 dark:bg-slate-800 px-1 py-0.5 rounded text-[10px]">↑</kbd>{' '}
              <kbd className="font-mono bg-slate-200 dark:bg-slate-800 px-1 py-0.5 rounded text-[10px]">↓</kbd> to navigate
            </span>
            <span>
              <kbd className="font-mono bg-slate-200 dark:bg-slate-800 px-1 py-0.5 rounded text-[10px]">↵</kbd> to select
            </span>
          </div>
          <span className="font-mono text-[10px] text-slate-400 dark:text-slate-500">Cmd+K or Ctrl+K</span>
        </div>
      </div>
    </div>
  );
}
