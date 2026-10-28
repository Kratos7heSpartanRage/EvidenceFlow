import { AlertTriangle, Bot, CheckCircle, HelpCircle, Info, User, XCircle } from 'lucide-react';
import { PicoLabel, ScreeningDecision, ScreeningSuggestion } from '../../types/api';

export function MachineSuggestionBadge({ suggestion }: { suggestion?: ScreeningSuggestion | null; }) {
  if (!suggestion) return null;

  const config = {
    include: {
      border: 'border-emerald-500/40 text-emerald-400 bg-emerald-500/10',
      icon: CheckCircle,
      label: 'Suggested: Include'
    },
    exclude: {
      border: 'border-rose-500/40 text-rose-400 bg-rose-500/10',
      icon: XCircle,
      label: 'Suggested: Exclude'
    },
    maybe: {
      border: 'border-amber-500/40 text-amber-400 bg-amber-500/10',
      icon: HelpCircle,
      label: 'Suggested: Maybe'
    }
  }[suggestion.suggestion];

  const strength = suggestion.evidence_json?.strength || 'rule';
  const explanation = suggestion.evidence_json?.explanation || 'Algorithmic suggestion';

  return (
    <div className="relative group inline-block">
      <span
        className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-medium border ${config.border} cursor-help transition-all shadow-sm`}
        title={explanation}
      >
        <Bot className="w-3.5 h-3.5 opacity-80" />
        <span>{config.label}</span>
        <span className="text-[10px] uppercase tracking-wider px-1 py-0.5 rounded bg-slate-800/80 text-slate-300 font-mono">
          {strength}
        </span>
      </span>

      {/* Tooltip on hover */}
      <div className="absolute z-50 bottom-full left-0 mb-1.5 hidden group-hover:block w-72 p-2.5 bg-slate-900 border border-slate-700 rounded-lg shadow-xl text-xs text-slate-300 pointer-events-none transition-all">
        <div className="flex items-center gap-1 text-slate-200 font-semibold mb-1">
          <Info className="w-3.5 h-3.5 text-brand-400" />
          <span>Machine Evidence ({suggestion.algo_version})</span>
        </div>
        <p className="text-slate-300 mb-1.5 leading-relaxed">{explanation}</p>
        {suggestion.evidence_json?.metadata_fields_used && (
          <div className="text-[11px] text-slate-400">
            Metadata: <span className="text-slate-200 font-mono">{suggestion.evidence_json.metadata_fields_used.join(', ')}</span>
          </div>
        )}
        {suggestion.evidence_json?.rule_hits && (
          <div className="text-[11px] text-slate-400 mt-0.5">
            Rule Hits: <span className="text-amber-300 font-mono">{suggestion.evidence_json.rule_hits.join(', ')}</span>
          </div>
        )}
      </div>
    </div>
  );
}

export function HumanDecisionBadge({ decision }: { decision?: ScreeningDecision | null; }) {
  if (!decision) {
    return (
      <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md text-xs font-medium bg-slate-800 border border-slate-700 text-slate-400">
        <HelpCircle className="w-3.5 h-3.5" />
        <span>Unscreened</span>
      </span>
    );
  }

  const config = {
    include: {
      bg: 'bg-emerald-600 text-white border-emerald-500 shadow-emerald-950/40',
      icon: CheckCircle,
      label: 'Included'
    },
    exclude: {
      bg: 'bg-rose-600 text-white border-rose-500 shadow-rose-950/40',
      icon: XCircle,
      label: 'Excluded'
    },
    maybe: {
      bg: 'bg-amber-600 text-white border-amber-500 shadow-amber-950/40',
      icon: HelpCircle,
      label: 'Maybe'
    }
  }[decision.decision];

  const originLabel = decision.origin !== 'direct' ? `(${decision.origin})` : '';

  return (
    <div className="relative group inline-block">
      <span
        className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-semibold shadow border ${config.bg} cursor-help transition-transform active:scale-95`}
      >
        <User className="w-3.5 h-3.5" />
        <span>{config.label}</span>
        {originLabel && (
          <span className="text-[10px] opacity-80 uppercase tracking-tight font-mono">{originLabel}</span>
        )}
      </span>

      {/* Tooltip on hover */}
      <div className="absolute z-50 bottom-full left-0 mb-1.5 hidden group-hover:block w-64 p-2 bg-slate-900 border border-slate-700 rounded-lg shadow-xl text-xs text-slate-300 pointer-events-none">
        <div className="flex items-center justify-between text-slate-200 font-semibold mb-1">
          <span>Decided by {decision.reviewer}</span>
          <span className="text-[10px] text-slate-400 font-mono">{new Date(decision.created_at).toLocaleDateString()}</span>
        </div>
        {decision.reason_text && (
          <p className="text-amber-200 text-xs italic mb-1">"{decision.reason_text}"</p>
        )}
        <div className="text-[10px] text-slate-400">
          Origin: <span className="text-brand-300 font-mono">{decision.origin}</span>
        </div>
      </div>
    </div>
  );
}

export function DedupTierBadge({ tier, score }: { tier: 'auto' | 'uncertain'; score: number; }) {
  if (tier === 'auto') {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-emerald-500/10 border border-emerald-500/30 text-emerald-400">
        <CheckCircle className="w-3 h-3" />
        <span>Auto-Duplicate ({Math.round(score * 100)}%)</span>
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-amber-500/10 border border-amber-500/30 text-amber-400">
      <AlertTriangle className="w-3 h-3" />
      <span>Uncertain Pair ({Math.round(score * 100)}%)</span>
    </span>
  );
}

export function PicoBadge({ label }: { label: PicoLabel; }) {
  const styles: Record<PicoLabel, { bg: string; text: string; border: string; name: string; }> = {
    P: { bg: 'bg-pico-p/15', text: 'text-pico-p', border: 'border-pico-p/40', name: 'Population' },
    I: { bg: 'bg-pico-i/15', text: 'text-pico-i', border: 'border-pico-i/40', name: 'Intervention' },
    C: { bg: 'bg-pico-c/15', text: 'text-pico-c', border: 'border-pico-c/40', name: 'Comparator' },
    O: { bg: 'bg-pico-o/15', text: 'text-pico-o', border: 'border-pico-o/40', name: 'Outcome' }
  };
  const s = styles[label];

  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded font-mono text-xs font-bold border ${s.bg} ${s.text} ${s.border}`}>
      <span>{label}</span>
      <span className="text-[10px] font-sans font-normal opacity-80">({s.name})</span>
    </span>
  );
}
