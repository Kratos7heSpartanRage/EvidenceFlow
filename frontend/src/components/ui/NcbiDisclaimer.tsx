import React from 'react';
import { AlertCircle, ExternalLink } from 'lucide-react';

export function NcbiDisclaimer() {
  return (
    <div className="flex items-start gap-3 p-3 rounded-lg bg-blue-950/40 border border-blue-800/40 text-blue-200 text-xs">
      <AlertCircle className="w-4 h-4 text-blue-400 mt-0.5 flex-shrink-0" />
      <div className="space-y-1">
        <div className="font-semibold text-blue-100 flex items-center gap-1.5">
          <span>NCBI / NLM Disclaimer Notice</span>
          <span className="text-[10px] px-1.5 py-0.2 rounded bg-blue-900/80 text-blue-300 font-mono">Official Compliance</span>
        </div>
        <p className="leading-relaxed text-blue-200/90">
          This tool queries the National Library of Medicine (NLM) PubMed E-utilities API. NLM data are in the public domain, but individual abstracts may contain copyrighted material reproduced with permission. Literature searches respect the 3 req/sec unauthenticated rate limit.
        </p>
        <div className="text-[11px] text-blue-300/70 pt-0.5">
          Tool: <span className="font-mono text-blue-200">EvidenceFlow</span> | Contact: <span className="font-mono text-blue-200">evidenceflow-hackathon@team.internal</span>
        </div>
      </div>
    </div>
  );
}
