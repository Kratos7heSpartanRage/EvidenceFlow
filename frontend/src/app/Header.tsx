import { useQuery } from '@tanstack/react-query';
import {
  ArrowLeft,
  Check,
  ChevronDown,
  Command,
  FilePlus,
  HelpCircle,
  Moon,
  RotateCcw,
  Search,
  Sparkles,
  Sun,
  User
} from 'lucide-react';
import React, { useEffect, useState } from 'react';
import { api, getActiveReviewer, setActiveReviewer } from '../lib/api';
import type { EntityId, Review } from '../types/api';

interface HeaderProps {
  onRefresh: () => void;
  onBackToLanding?: () => void;
  onOpenCommandPalette?: () => void;
  onToggleTheme?: () => void;
  onOpenShortcuts?: () => void;
  isDark?: boolean;
  activeQueryVersion?: string | number | null;
  reviews?: Review[];
  activeReviewId?: EntityId;
  onSelectReview?: (id: EntityId) => void;
  onOpenCreateReview?: () => void;
}

export function Header({
  onRefresh,
  onBackToLanding,
  onOpenCommandPalette,
  onToggleTheme,
  onOpenShortcuts,
  isDark = true,
  activeQueryVersion,
  reviews = [],
  activeReviewId,
  onSelectReview,
  onOpenCreateReview
}: HeaderProps) {
  const [reviewer, setReviewer] = useState(getActiveReviewer());
  const health = useQuery({ queryKey: ['health'], queryFn: api.getHealth, refetchInterval: 15000 });
  const healthMode = health.isSuccess ? 'live' : health.isPending ? 'connecting' : 'offline';
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);

  useEffect(() => {
    const handleReviewerChange = () => {
      setReviewer(getActiveReviewer());
    };
    window.addEventListener('reviewer_changed', handleReviewerChange);
    return () => window.removeEventListener('reviewer_changed', handleReviewerChange);
  }, []);

  const reviewers = ['Member D (Lead)', 'Member A', 'Member B', 'Member C', 'Auditor'];

  const handleSelectReviewer = (name: string) => {
    setActiveReviewer(name);
    setReviewer(name);
    setIsDropdownOpen(false);
    onRefresh();
  };

  const activeReview = reviews.find(r => r.id === activeReviewId);

  return (
    <header className="h-14 px-4 md:px-6 border-b border-slate-200/80 dark:border-slate-800/80 bg-white/70 dark:bg-slate-950/70 backdrop-blur-xl flex items-center justify-between sticky top-0 z-40 transition-colors duration-300">
      {/* Left: Brand + Review Workspace Switcher */}
      <div className="flex items-center gap-3 md:gap-4 min-w-0">
        {onBackToLanding && (
          <button
            onClick={onBackToLanding}
            className="flex items-center gap-1.5 px-2 py-1 rounded-lg text-xs font-medium text-slate-500 hover:text-slate-800 dark:text-slate-400 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition"
            title="Return to Landing Page"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">Overview</span>
          </button>
        )}

        {/* Brand Icon & Name */}
        <div
          onClick={onBackToLanding}
          className="flex items-center gap-2 cursor-pointer group shrink-0"
          title="EvidenceFlow — Mini-Rayyan Systematic Review"
        >
          <div className="w-7 h-7 rounded-lg bg-teal-600 hover:bg-teal-500 flex items-center justify-center font-bold text-white text-xs shadow-sm shadow-teal-500/20 group-hover:scale-105 transition-transform">
            EF
          </div>
          <span className="text-sm font-extrabold tracking-tight text-slate-900 dark:text-slate-100 group-hover:text-teal-600 dark:group-hover:text-teal-400 transition-colors hidden sm:inline">
            EvidenceFlow
          </span>
        </div>

        {/* Vertical Divider */}
        <div className="h-4 w-px bg-slate-300 dark:bg-slate-800 shrink-0 hidden sm:block" />

        {/* Review Workspace Selector */}
        {reviews.length > 0 && onSelectReview && (
          <div className="flex items-center gap-2 min-w-0">
            <div className="relative flex items-center">
              <select
                id="active-review"
                aria-label="Active Review"
                className="appearance-none bg-slate-100 dark:bg-slate-900 border border-slate-300 dark:border-slate-800 hover:border-slate-400 dark:hover:border-slate-700 text-slate-900 dark:text-slate-100 text-xs font-semibold rounded-lg pl-2.5 pr-7 py-1.5 truncate max-w-[180px] sm:max-w-xs cursor-pointer focus:outline-none focus:ring-1 focus:ring-teal-500 transition"
                value={activeReviewId || ''}
                onChange={e => onSelectReview(e.target.value)}
              >
                {reviews.map(r => (
                  <option key={r.id} value={r.id} className="bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100">
                    {r.title}
                  </option>
                ))}
              </select>
              <ChevronDown className="w-3.5 h-3.5 text-slate-400 pointer-events-none absolute right-2" />
            </div>

            {onOpenCreateReview && (
              <button
                onClick={onOpenCreateReview}
                className="flex items-center gap-1 px-2 py-1.5 rounded-lg text-xs font-semibold bg-teal-50 hover:bg-teal-100 dark:bg-teal-950/60 dark:hover:bg-teal-900/60 text-teal-700 dark:text-teal-300 border border-teal-200 dark:border-teal-800/60 hover:border-teal-300 dark:hover:border-teal-700 transition"
                title="Create New Systematic Review"
              >
                <FilePlus className="w-3.5 h-3.5" />
                <span className="hidden md:inline">New</span>
              </button>
            )}
          </div>
        )}
      </div>

      {/* Center: Command Palette Trigger */}
      {onOpenCommandPalette && (
        <button
          onClick={onOpenCommandPalette}
          className="hidden lg:flex items-center gap-2 px-3 py-1.5 rounded-xl bg-slate-100/80 dark:bg-slate-900/70 border border-slate-200/80 dark:border-slate-800/80 hover:border-slate-300 dark:hover:border-slate-700 text-xs text-slate-500 hover:text-slate-800 dark:text-slate-400 dark:hover:text-slate-200 transition-all shadow-sm"
          title="Open Command Palette (⌘K / Ctrl+K)"
        >
          <Search className="w-3.5 h-3.5 text-teal-600 dark:text-teal-400" />
          <span>Quick search or jump to...</span>
          <kbd className="px-1.5 py-0.5 text-[10px] font-mono text-slate-600 dark:text-slate-400 bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded shadow-sm">
            ⌘K
          </kbd>
        </button>
      )}

      {/* Right: Controls & Status Pills */}
      <div className="flex items-center gap-2 md:gap-2.5">
        {/* Backend status indicator */}
        <div
          className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-mono font-medium border transition-colors ${
            healthMode === 'live'
              ? 'bg-emerald-50 dark:bg-emerald-950/40 border-emerald-200 dark:border-emerald-500/30 text-emerald-700 dark:text-emerald-400'
              : 'bg-amber-50 dark:bg-amber-950/40 border-amber-200 dark:border-amber-500/30 text-amber-700 dark:text-amber-300'
          }`}
          title={healthMode === 'live' ? 'Connected to live FastAPI backend' : 'Backend offline; mock mode active'}
        >
          <span className="w-1.5 h-1.5 rounded-full bg-current animate-pulse" />
          <span className="hidden sm:inline">
            {healthMode === 'live' ? 'Backend Live' : healthMode === 'connecting' ? 'Connecting…' : 'Mock Mode'}
          </span>
        </div>

        {/* Keyboard Shortcuts Trigger */}
        {onOpenShortcuts && (
          <button
            onClick={onOpenShortcuts}
            className="p-1.5 rounded-lg text-slate-500 hover:text-slate-800 dark:text-slate-400 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition"
            title="Screening Keyboard Shortcuts (I/E/M/N/P)"
            aria-label="View shortcuts"
          >
            <HelpCircle className="w-4 h-4" />
          </button>
        )}

        {/* Day-Night Toggle Pill */}
        {onToggleTheme && (
          <button
            onClick={onToggleTheme}
            className="flex items-center gap-1.5 px-2.5 py-1 rounded-xl bg-slate-100 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 hover:border-slate-300 dark:hover:border-slate-700 text-xs font-semibold text-slate-700 dark:text-slate-300 transition shadow-sm"
            title={isDark ? 'Switch to Editorial Light Mode' : 'Switch to Obsidian Dark Mode'}
            aria-label="Toggle light/dark theme"
          >
            {isDark ? (
              <>
                <Sun className="w-3.5 h-3.5 text-amber-400" />
                <span className="hidden sm:inline font-mono text-[11px]">Dark</span>
              </>
            ) : (
              <>
                <Moon className="w-3.5 h-3.5 text-indigo-600" />
                <span className="hidden sm:inline font-mono text-[11px]">Light</span>
              </>
            )}
          </button>
        )}

        {/* Refresh Button */}
        <button
          onClick={onRefresh}
          className="p-1.5 rounded-lg text-slate-500 hover:text-slate-800 dark:text-slate-400 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition"
          title="Refresh Workspace Data"
          aria-label="Refresh data"
        >
          <RotateCcw className="w-4 h-4" />
        </button>

        {/* Reviewer Profile Dropdown */}
        <div className="relative">
          <button
            onClick={() => setIsDropdownOpen(!isDropdownOpen)}
            className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-slate-100 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 hover:border-slate-300 dark:hover:border-slate-700 text-xs font-semibold text-slate-800 dark:text-slate-200 transition shadow-sm"
          >
            <User className="w-3.5 h-3.5 text-teal-600 dark:text-teal-400" />
            <span className="hidden sm:inline max-w-[100px] truncate">{reviewer}</span>
            <ChevronDown className="w-3 h-3 text-slate-400" />
          </button>

          {isDropdownOpen && (
            <div className="absolute right-0 mt-2 w-48 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-2xl p-1.5 z-50 text-xs animate-in fade-in duration-100">
              <div className="px-2.5 py-1 text-[10px] font-bold uppercase tracking-wider text-slate-400 font-mono">
                Active Reviewer
              </div>
              {reviewers.map(r => (
                <button
                  key={r}
                  onClick={() => handleSelectReviewer(r)}
                  className={`w-full text-left px-2.5 py-1.5 rounded-lg flex items-center justify-between text-xs transition ${
                    reviewer === r
                      ? 'bg-teal-600 text-white font-semibold'
                      : 'text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800'
                  }`}
                >
                  <span>{r}</span>
                  {reviewer === r && <Check className="w-3.5 h-3.5 text-white" />}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
