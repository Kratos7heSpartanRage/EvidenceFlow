import React, { useState, useEffect } from 'react';
import { getActiveReviewer, setActiveReviewer, api, mockStore } from '../lib/api';
import { User, Activity, RotateCcw, ShieldCheck, ChevronDown, Check, Home, ArrowLeft } from 'lucide-react';

interface HeaderProps {
  onRefresh: () => void;
  onBackToLanding?: () => void;
}

export function Header({ onRefresh, onBackToLanding }: HeaderProps) {
  const [reviewer, setReviewer] = useState(getActiveReviewer());
  const [healthMode, setHealthMode] = useState<'live' | 'mock'>('mock');
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);

  useEffect(() => {
    api.getHealth().then(h => setHealthMode(h.mode));

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

  const handleResetDemoState = () => {
    if (confirm('Reset in-memory demo state back to pristine baseline?')) {
      mockStore.reset();
      onRefresh();
    }
  };

  return (
    <header className="h-16 px-6 border-b border-slate-800 bg-slate-950/80 backdrop-blur-md flex items-center justify-between sticky top-0 z-40">
      {/* Brand & Subtitle & Back to Landing */}
      <div className="flex items-center gap-4">
        {onBackToLanding && (
          <button
            onClick={onBackToLanding}
            className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-semibold text-slate-400 hover:text-slate-100 hover:bg-slate-800 transition"
            title="Return to Landing Page"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">Overview</span>
          </button>
        )}

        <div
          onClick={onBackToLanding}
          className="flex items-center gap-3 cursor-pointer group"
          title="Click to go to Overview"
        >
          <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-brand-600 to-cyan-500 flex items-center justify-center shadow-lg shadow-brand-950/60 font-bold text-white text-sm group-hover:scale-105 transition">
            EF
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-base font-extrabold text-slate-100 tracking-tight group-hover:text-brand-300 transition">
                EvidenceFlow
              </h1>
              <span className="text-[10px] uppercase font-mono px-1.5 py-0.2 rounded bg-slate-800 text-slate-400 border border-slate-700">
                Workspace
              </span>
            </div>
            <p className="text-[11px] text-slate-400">Mini-Rayyan Systematic Review</p>
          </div>
        </div>
      </div>

      {/* Center/Right Controls */}
      <div className="flex items-center gap-3">
        {/* Backend status badge */}
        <div
          className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-mono font-medium border ${
            healthMode === 'live'
              ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400'
              : 'bg-brand-500/10 border-brand-500/30 text-brand-300'
          }`}
          title={healthMode === 'live' ? 'Connected to live FastAPI backend' : 'Running in local verified mock state for instant demo'}
        >
          <span className="w-2 h-2 rounded-full bg-current animate-pulse" />
          <span className="hidden sm:inline">{healthMode === 'live' ? 'Backend Live' : 'Demo Mode (Full State)'}</span>
        </div>

        {/* Reset Mock State Button */}
        <button
          onClick={handleResetDemoState}
          className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-medium text-slate-400 hover:text-slate-200 hover:bg-slate-800/80 transition"
          title="Reset sample data back to baseline"
        >
          <RotateCcw className="w-3.5 h-3.5" />
          <span className="hidden md:inline">Reset Demo</span>
        </button>

        {/* Active Reviewer Selector Dropdown */}
        <div className="relative">
          <button
            onClick={() => setIsDropdownOpen(!isDropdownOpen)}
            className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800 hover:border-slate-700 text-xs font-medium text-slate-200 transition shadow-sm"
          >
            <User className="w-3.5 h-3.5 text-brand-400" />
            <span>{reviewer}</span>
            <ChevronDown className="w-3.5 h-3.5 text-slate-400" />
          </button>

          {isDropdownOpen && (
            <div className="absolute right-0 mt-1.5 w-48 rounded-xl bg-slate-900 border border-slate-800 shadow-2xl p-1.5 z-50 text-xs animate-in fade-in duration-100">
              <div className="px-2.5 py-1 text-[10px] font-bold uppercase tracking-wider text-slate-500">
                Switch Active Reviewer
              </div>
              {reviewers.map(r => (
                <button
                  key={r}
                  onClick={() => handleSelectReviewer(r)}
                  className={`w-full text-left px-2.5 py-1.5 rounded-lg flex items-center justify-between text-xs transition ${
                    reviewer === r ? 'bg-brand-600 text-white font-semibold' : 'text-slate-300 hover:bg-slate-800'
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
