import React from 'react';
import {
  ArrowRight,
  ShieldCheck,
  GitMerge,
  FileSearch,
  Tag,
  GitCompare,
  RotateCcw,
  Sparkles,
  Layers,
  Database,
  CheckCircle2,
  Lock,
  FileSpreadsheet,
  Cpu,
  BookOpen
} from 'lucide-react';

interface LandingPageProps {
  onEnterWorkspace: () => void;
}

export function LandingPage({ onEnterWorkspace }: LandingPageProps) {
  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans selection:bg-brand-500 selection:text-white relative overflow-x-hidden">
      {/* Background glowing gradients */}
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[1000px] h-[450px] bg-gradient-to-b from-brand-600/20 via-cyan-500/10 to-transparent blur-3xl pointer-events-none -z-10" />
      <div className="absolute top-1/3 -left-48 w-96 h-96 bg-purple-600/10 rounded-full blur-3xl pointer-events-none -z-10" />
      <div className="absolute top-2/3 -right-48 w-96 h-96 bg-emerald-600/10 rounded-full blur-3xl pointer-events-none -z-10" />

      {/* Top Navbar */}
      <header className="h-20 px-6 sm:px-12 border-b border-slate-800/80 bg-slate-950/70 backdrop-blur-md flex items-center justify-between sticky top-0 z-40">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-brand-600 via-brand-500 to-cyan-400 flex items-center justify-center shadow-lg shadow-brand-950/80 font-black text-white text-base tracking-wider">
            EF
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-lg font-black text-slate-100 tracking-tight">EvidenceFlow</span>
              <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded-full bg-brand-500/15 text-brand-300 border border-brand-500/30 font-bold">
                Mini-Rayyan 2026
              </span>
            </div>
            <p className="text-[11px] text-slate-400 font-medium">Auditable Systematic Review Workspace</p>
          </div>
        </div>

        <div className="flex items-center gap-4">
          <button
            onClick={onEnterWorkspace}
            className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-gradient-to-r from-brand-600 to-cyan-600 hover:from-brand-500 hover:to-cyan-500 text-white font-bold text-xs shadow-xl shadow-brand-950/60 transition-all hover:scale-105 active:scale-95 cursor-pointer"
          >
            <span>Enter Workspace</span>
            <ArrowRight className="w-4 h-4" />
          </button>
        </div>
      </header>

      {/* Hero Section */}
      <main className="flex-1 max-w-6xl mx-auto px-6 py-16 sm:py-24 space-y-20">
        <div className="text-center space-y-6 max-w-3xl mx-auto">
          {/* Floating Pill Badge */}
          <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-slate-900/90 border border-slate-700/80 shadow-inner text-xs font-medium text-slate-300">
            <Sparkles className="w-3.5 h-3.5 text-brand-400" />
            <span>Mini-Rayyan 72-Hour Hackathon Challenge</span>
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
          </div>

          {/* Headline */}
          <h1 className="text-4xl sm:text-6xl font-extrabold text-slate-100 tracking-tight leading-[1.15]">
            Auditable Systematic Reviews.{' '}
            <span className="bg-gradient-to-r from-brand-400 via-cyan-300 to-emerald-400 bg-clip-text text-transparent">
              Without the Rework.
            </span>
          </h1>

          {/* Subtitle */}
          <p className="text-base sm:text-lg text-slate-300/90 leading-relaxed font-normal">
            Change your literature search as often as you like. EvidenceFlow automatically traces query diffs, merges duplicate groups, and mathematically guarantees that <strong>no reviewer decision is ever lost</strong>.
          </p>

          {/* Main Hero CTA Button */}
          <div className="pt-4 flex flex-col sm:flex-row items-center justify-center gap-4">
            <button
              onClick={onEnterWorkspace}
              className="w-full sm:w-auto flex items-center justify-center gap-3 px-8 py-4 rounded-2xl bg-gradient-to-r from-brand-600 via-brand-500 to-cyan-500 hover:from-brand-500 hover:to-cyan-400 text-white font-extrabold text-sm shadow-2xl shadow-brand-950/80 transition-all hover:scale-105 active:scale-95 cursor-pointer"
            >
              <span>Launch Review Workspace</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>

          {/* Quick Pillars */}
          <div className="pt-6 grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs text-slate-400 font-mono">
            <div className="p-2.5 rounded-xl bg-slate-900/50 border border-slate-800/80 flex items-center justify-center gap-2">
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
              <span>Zero-Loss Query Loop</span>
            </div>
            <div className="p-2.5 rounded-xl bg-slate-900/50 border border-slate-800/80 flex items-center justify-center gap-2">
              <CheckCircle2 className="w-3.5 h-3.5 text-brand-400 shrink-0" />
              <span>Multi-Source Fetch</span>
            </div>
            <div className="p-2.5 rounded-xl bg-slate-900/50 border border-slate-800/80 flex items-center justify-center gap-2">
              <CheckCircle2 className="w-3.5 h-3.5 text-cyan-400 shrink-0" />
              <span>Automated PICO</span>
            </div>
            <div className="p-2.5 rounded-xl bg-slate-900/50 border border-slate-800/80 flex items-center justify-center gap-2">
              <CheckCircle2 className="w-3.5 h-3.5 text-purple-400 shrink-0" />
              <span>100% Audit Provenance</span>
            </div>
          </div>
        </div>

        {/* Feature Cards Grid (3 Columns) */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 pt-6">
          {/* Card 1 */}
          <div className="p-6 rounded-2xl bg-slate-900/40 border border-slate-800 hover:border-slate-700 transition space-y-3">
            <div className="w-10 h-10 rounded-xl bg-brand-500/10 border border-brand-500/20 text-brand-400 flex items-center justify-center">
              <GitCompare className="w-5 h-5" />
            </div>
            <h3 className="text-base font-bold text-slate-100">Level 2 Loop & Diff View</h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              Broaden or narrow your Boolean query. EvidenceFlow computes precise additions, preserves earlier reviewer decisions, and restores exact v1 snapshots without re-fetching APIs.
            </p>
          </div>

          {/* Card 2 */}
          <div className="p-6 rounded-2xl bg-slate-900/40 border border-slate-800 hover:border-slate-700 transition space-y-3">
            <div className="w-10 h-10 rounded-xl bg-cyan-500/10 border border-cyan-500/20 text-cyan-400 flex items-center justify-center">
              <GitMerge className="w-5 h-5" />
            </div>
            <h3 className="text-base font-bold text-slate-100">Cross-Source Deduplication</h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              Deterministic deduplication across PubMed and Europe PMC. Armed with our Conference vs. Journal guard to prevent treating conference abstracts as duplicates of published trials.
            </p>
          </div>

          {/* Card 3 */}
          <div className="p-6 rounded-2xl bg-slate-900/40 border border-slate-800 hover:border-slate-700 transition space-y-3">
            <div className="w-10 h-10 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 flex items-center justify-center">
              <ShieldCheck className="w-5 h-5" />
            </div>
            <h3 className="text-base font-bold text-slate-100">Human-In-The-Loop Governance</h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              Exclusion requires an explicit protocol reason. When queries expand and groups merge with conflicting decisions, conflicts are surfaced for human resolution rather than silently chosen.
            </p>
          </div>
        </div>

        {/* 7-Step Pipeline Stepper Preview */}
        <div className="p-8 rounded-2xl bg-slate-900/50 border border-slate-800 space-y-6">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-800 pb-4">
            <div>
              <h2 className="text-lg font-bold text-slate-100">The EvidenceFlow Pipeline Architecture</h2>
              <p className="text-xs text-slate-400">Steps 0 through 7 designed for the Mini-Rayyan evaluation rubric</p>
            </div>
            <span className="text-[11px] font-mono text-brand-400 font-bold px-2.5 py-1 rounded-lg bg-brand-950/80 border border-brand-800/40">
              End-to-End Ready
            </span>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-3 text-xs">
            <div className="p-3.5 rounded-xl bg-slate-950 border border-slate-800/80 space-y-1">
              <span className="text-[10px] font-mono text-brand-400 font-bold block">STEP 0</span>
              <div className="font-semibold text-slate-200">Protocol & Criteria</div>
              <p className="text-[11px] text-slate-500">PICO definition</p>
            </div>
            <div className="p-3.5 rounded-xl bg-slate-950 border border-slate-800/80 space-y-1">
              <span className="text-[10px] font-mono text-cyan-400 font-bold block">STEP 1-2</span>
              <div className="font-semibold text-slate-200">Search & Fetch</div>
              <p className="text-[11px] text-slate-500">PubMed & Europe PMC</p>
            </div>
            <div className="p-3.5 rounded-xl bg-slate-950 border border-slate-800/80 space-y-1">
              <span className="text-[10px] font-mono text-amber-400 font-bold block">STEP 4</span>
              <div className="font-semibold text-slate-200">Deduplication</div>
              <p className="text-[11px] text-slate-500">Hide, never delete</p>
            </div>
            <div className="p-3.5 rounded-xl bg-slate-950 border border-slate-800/80 space-y-1">
              <span className="text-[10px] font-mono text-rose-400 font-bold block">STEP 5</span>
              <div className="font-semibold text-slate-200">Screening</div>
              <p className="text-[11px] text-slate-500">I / E / M + reason</p>
            </div>
            <div className="p-3.5 rounded-xl bg-slate-950 border border-slate-800/80 space-y-1">
              <span className="text-[10px] font-mono text-purple-400 font-bold block">STEP 6</span>
              <div className="font-semibold text-slate-200">PICO Spans</div>
              <p className="text-[11px] text-slate-500">Entity tagging</p>
            </div>
            <div className="p-3.5 rounded-xl bg-slate-950 border border-brand-500/40 space-y-1 shadow-md shadow-brand-950/40">
              <span className="text-[10px] font-mono text-brand-300 font-bold block">LOOP</span>
              <div className="font-semibold text-brand-200">Query Evolution</div>
              <p className="text-[11px] text-brand-400/80">Diff & exact revert</p>
            </div>
            <div className="p-3.5 rounded-xl bg-slate-950 border border-slate-800/80 space-y-1">
              <span className="text-[10px] font-mono text-emerald-400 font-bold block">STEP 7</span>
              <div className="font-semibold text-slate-200">CSV Export</div>
              <p className="text-[11px] text-slate-500">Synthesis output</p>
            </div>
          </div>
        </div>

        {/* Bottom Call to Action */}
        <div className="text-center p-8 rounded-2xl bg-gradient-to-r from-brand-950/60 via-slate-900 to-slate-950 border border-brand-800/40 space-y-4">
          <h2 className="text-xl font-bold text-slate-100">Ready to test the Mini-Rayyan workflow?</h2>
          <p className="text-xs text-slate-400 max-w-lg mx-auto">
            Explore the prepared Metformin vs. Placebo systematic review protocol, review duplicate pairs, screen abstracts, and test the Level 2 Query Evolution loop.
          </p>
          <button
            onClick={onEnterWorkspace}
            className="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-brand-600 hover:bg-brand-500 text-white font-bold text-xs shadow-lg shadow-brand-950/60 transition cursor-pointer"
          >
            <span>Launch EvidenceFlow Workspace</span>
            <ArrowRight className="w-4 h-4" />
          </button>
        </div>
      </main>

      {/* Footer */}
      <footer className="py-6 border-t border-slate-800/80 bg-slate-950 text-center text-xs text-slate-500 font-mono">
        EvidenceFlow ? Mini-Rayyan 72h Hackathon ? Member D Frontend & Demo Lead
      </footer>
    </div>
  );
}
