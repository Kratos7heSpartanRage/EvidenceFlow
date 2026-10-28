import {
  ArrowRight,
  FileSpreadsheet,
  FileText,
  GitCompare,
  GitMerge,
  Search,
  ShieldCheck,
  Tag
} from 'lucide-react';
import React from 'react';
import { AmbientBackground } from '../../components/ui/AmbientBackground';

interface LandingPageProps {
  onEnterWorkspace: () => void;
  isDark?: boolean;
}

export function LandingPage({ onEnterWorkspace, isDark = true }: LandingPageProps) {
  return (
    <div className="min-h-screen bg-slate-50 dark:bg-[#070b13] text-slate-900 dark:text-slate-100 flex flex-col font-sans selection:bg-teal-500 selection:text-white relative transition-colors duration-300">
      <AmbientBackground isDark={isDark} />

      {/* Editorial Top Navbar */}
      <header className="h-16 px-6 sm:px-12 border-b border-slate-200/80 dark:border-slate-800/80 bg-white/70 dark:bg-slate-950/70 backdrop-blur-xl flex items-center justify-between sticky top-0 z-40 transition-colors">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-teal-600 flex items-center justify-center font-bold text-white text-xs tracking-wider shadow-sm">
            EF
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-sm font-bold text-slate-900 dark:text-slate-100 tracking-tight">EvidenceFlow</span>
              <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded bg-teal-50 dark:bg-teal-500/10 text-teal-700 dark:text-teal-300 border border-teal-200 dark:border-teal-500/30 font-semibold">
                Mini-Rayyan 72h
              </span>
            </div>
            <p className="text-[11px] text-slate-500 dark:text-slate-400">Auditable Systematic Review Workspace</p>
          </div>
        </div>

        <div className="flex items-center gap-4">
          <button
            onClick={onEnterWorkspace}
            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-teal-600 hover:bg-teal-500 text-white font-semibold text-xs tracking-wide transition shadow-sm hover:shadow-md cursor-pointer"
          >
            <span>Enter Workspace</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>
      </header>

      {/* Hero Section */}
      <main className="flex-1 max-w-6xl mx-auto px-6 py-12 sm:py-20 space-y-16">
        <div className="text-center space-y-5 max-w-3xl mx-auto">
          {/* Subtle Tag */}
          <div className="inline-flex items-center gap-2 px-3.5 py-1 rounded-full bg-white/80 dark:bg-slate-900/80 border border-slate-200/80 dark:border-slate-800 text-xs font-mono text-slate-600 dark:text-slate-400 shadow-sm">
            <span className="w-2 h-2 rounded-full bg-teal-500 animate-pulse" />
            <span>Mini-Rayyan AI/ML Hackathon Platform</span>
          </div>

          {/* Headline */}
          <h1 className="text-4xl sm:text-5xl font-extrabold tracking-tight text-slate-900 dark:text-slate-100 leading-[1.15]">
            Auditable Systematic Literature Reviews{' '}
            <span className="text-teal-600 dark:text-teal-400">With Zero Decision Loss</span>
          </h1>

          {/* Editorial Hook */}
          <p className="text-sm sm:text-base text-slate-600 dark:text-slate-300 leading-relaxed font-normal">
            A biomedical systematic-review tool with automated PubMed & Europe PMC ingestion, algorithmic deduplication, rule-based screening, and PICO tagging.
          </p>

          {/* Core Pitch Quote */}
          <div className="p-4 rounded-2xl bg-white/70 dark:bg-slate-900/60 backdrop-blur-md border border-slate-200/80 dark:border-slate-800 max-w-2xl mx-auto text-left shadow-sm">
            <p className="text-xs font-mono text-teal-700 dark:text-teal-400 font-semibold mb-1">THE LEVEL 2 GUARANTEE</p>
            <p className="text-sm italic text-slate-800 dark:text-slate-200">
              "Change your search as often as you like. EvidenceFlow shows exactly what changed and never loses a decision you made."
            </p>
          </div>

          {/* CTAs */}
          <div className="pt-2 flex flex-col sm:flex-row items-center justify-center gap-4">
            <button
              onClick={onEnterWorkspace}
              className="w-full sm:w-auto flex items-center justify-center gap-2.5 px-6 py-3 rounded-xl bg-teal-600 hover:bg-teal-500 text-white font-bold text-sm tracking-wide transition shadow-sm hover:shadow-md cursor-pointer"
            >
              <span>Launch EvidenceFlow Workspace</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* 6 Key Architectural Capabilities */}
        <div className="grid md:grid-cols-3 gap-5 pt-4">
          <div className="p-5 rounded-2xl bg-white/70 dark:bg-slate-900/50 backdrop-blur-md border border-slate-200/80 dark:border-slate-800/80 space-y-2.5 shadow-sm hover:-translate-y-0.5 hover:shadow-md transition-all duration-200">
            <div className="w-8 h-8 rounded-xl bg-teal-50 dark:bg-teal-500/10 border border-teal-200 dark:border-teal-500/20 text-teal-700 dark:text-teal-400 flex items-center justify-center">
              <FileText className="w-4 h-4" />
            </div>
            <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100">1. PICO Question & Criteria</h3>
            <p className="text-xs text-slate-600 dark:text-slate-400 leading-relaxed">
              Define protocol questions and criteria with mandatory rationales. Any criteria update generates an explicit version without erasing existing evaluations.
            </p>
          </div>

          <div className="p-5 rounded-2xl bg-white/70 dark:bg-slate-900/50 backdrop-blur-md border border-slate-200/80 dark:border-slate-800/80 space-y-2.5 shadow-sm hover:-translate-y-0.5 hover:shadow-md transition-all duration-200">
            <div className="w-8 h-8 rounded-xl bg-teal-50 dark:bg-teal-500/10 border border-teal-200 dark:border-teal-500/20 text-teal-700 dark:text-teal-400 flex items-center justify-center">
              <Search className="w-4 h-4" />
            </div>
            <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100">2. Boolean Search & Ingestion</h3>
            <p className="text-xs text-slate-600 dark:text-slate-400 leading-relaxed">
              Preview hit counts across PubMed and Europe PMC. Live expressions render in monospace with NCBI copyright and rate-limit compliance.
            </p>
          </div>

          <div className="p-5 rounded-2xl bg-white/70 dark:bg-slate-900/50 backdrop-blur-md border border-slate-200/80 dark:border-slate-800/80 space-y-2.5 shadow-sm hover:-translate-y-0.5 hover:shadow-md transition-all duration-200">
            <div className="w-8 h-8 rounded-xl bg-teal-50 dark:bg-teal-500/10 border border-teal-200 dark:border-teal-500/20 text-teal-700 dark:text-teal-400 flex items-center justify-center">
              <GitMerge className="w-4 h-4" />
            </div>
            <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100">3. Deduplication & Graph Clustering</h3>
            <p className="text-xs text-slate-600 dark:text-slate-400 leading-relaxed">
              Exact DOI/PMID matches paired with title Levenshtein distance. Human reviewers can confirm or reject candidate pairs with automatic canonical election.
            </p>
          </div>

          <div className="p-5 rounded-2xl bg-white/70 dark:bg-slate-900/50 backdrop-blur-md border border-slate-200/80 dark:border-slate-800/80 space-y-2.5 shadow-sm hover:-translate-y-0.5 hover:shadow-md transition-all duration-200">
            <div className="w-8 h-8 rounded-xl bg-teal-50 dark:bg-teal-500/10 border border-teal-200 dark:border-teal-500/20 text-teal-700 dark:text-teal-400 flex items-center justify-center">
              <ShieldCheck className="w-4 h-4" />
            </div>
            <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100">4. Rayyan-Style Screening</h3>
            <p className="text-xs text-slate-600 dark:text-slate-400 leading-relaxed">
              Keyboard-first (I, E, M, N, P). Outlined suggested badges with evidence popovers; solid badges for human decisions. Exclude is strictly blocked without a reason.
            </p>
          </div>

          <div className="p-5 rounded-2xl bg-white/70 dark:bg-slate-900/50 backdrop-blur-md border border-slate-200/80 dark:border-slate-800/80 space-y-2.5 shadow-sm hover:-translate-y-0.5 hover:shadow-md transition-all duration-200">
            <div className="w-8 h-8 rounded-xl bg-teal-50 dark:bg-teal-500/10 border border-teal-200 dark:border-teal-500/20 text-teal-700 dark:text-teal-400 flex items-center justify-center">
              <Tag className="w-4 h-4" />
            </div>
            <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100">5. PICO Entity Extraction</h3>
            <p className="text-xs text-slate-600 dark:text-slate-400 leading-relaxed">
              Sentence-level span highlighting for Population, Intervention, Comparator, and Outcome. Full drag-select add, edit modal, and explicit unknown flagging.
            </p>
          </div>

          <div className="p-5 rounded-2xl bg-white/70 dark:bg-slate-900/50 backdrop-blur-md border border-slate-200/80 dark:border-slate-800/80 space-y-2.5 shadow-sm hover:-translate-y-0.5 hover:shadow-md transition-all duration-200">
            <div className="w-8 h-8 rounded-xl bg-teal-50 dark:bg-teal-500/10 border border-teal-200 dark:border-teal-500/20 text-teal-700 dark:text-teal-400 flex items-center justify-center">
              <GitCompare className="w-4 h-4" />
            </div>
            <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100">6. Query Loop & Exact Diff</h3>
            <p className="text-xs text-slate-600 dark:text-slate-400 leading-relaxed">
              Compare any two query versions: records added, retained, or dropped. Execute exact reverts with zero API calls while keeping human screening work safe.
            </p>
          </div>
        </div>

        {/* Bottom Banner */}
        <div className="p-6 rounded-2xl bg-white/70 dark:bg-slate-900/60 backdrop-blur-md border border-slate-200/80 dark:border-slate-800 flex flex-col sm:flex-row items-center justify-between gap-4 shadow-sm">
          <div className="space-y-1 text-center sm:text-left">
            <h4 className="text-sm font-bold text-slate-900 dark:text-slate-100">Ready to examine the review?</h4>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Explore the Metformin vs Placebo in Type 2 Diabetes benchmark or initialize a new review.
            </p>
          </div>
          <button
            onClick={onEnterWorkspace}
            className="px-5 py-2.5 rounded-xl bg-teal-600 hover:bg-teal-500 text-white font-semibold text-xs transition shadow-sm hover:shadow-md shrink-0 cursor-pointer"
          >
            Launch Review Workspace →
          </button>
        </div>
      </main>

      {/* Minimal Footer */}
      <footer className="border-t border-slate-200/80 dark:border-slate-800/80 py-6 px-6 text-center text-xs text-slate-500 dark:text-slate-400">
        EvidenceFlow · Mini-Rayyan 72h Hackathon · Member D Frontend & Demo Lead
      </footer>
    </div>
  );
}
