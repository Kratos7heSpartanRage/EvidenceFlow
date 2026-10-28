import { api } from '../../lib/api';
import { useData, useWorkspace } from '../../lib/workspace';

export function ReviewIntelligence() {
  const { reviewId } = useWorkspace();
  const [rechecks] = useData(['recheck-candidates'], () => api.getRecheckCandidates(reviewId));
  const [families] = useData(['study-families'], () => api.getStudyFamilies(reviewId));

  return <div className="space-y-8 max-w-5xl mx-auto text-slate-100">
    <div>
      <h2 className="text-2xl font-bold">Review intelligence</h2>
      <p className="text-sm text-slate-400">Evidence-backed suggestions. Reviewers keep control of every screening and duplicate decision.</p>
    </div>
    <section className="space-y-3">
      <h3 className="text-lg font-semibold">Old exclusions to reconsider ({rechecks.length})</h3>
      <p className="text-sm text-slate-400">After you change the exclusion criteria, this compares the two latest versions and checks earlier criterion-linked exclusions against newly added terms.</p>
      <p className="text-xs text-amber-300">To reconsider a candidate, find its title in Screening Queue and record a new human decision there.</p>
      {!rechecks.length && <p className="text-sm text-slate-400">No affected exclusions found. Create a second criteria version to compare, or check that exclusions were linked to criteria.</p>}
      {rechecks.map(item => <article key={item.record_id} className="rounded-xl border border-amber-700/40 bg-slate-900 p-4 space-y-2">
        <h4 className="font-semibold">{item.title}</h4>
        <p className="text-xs text-slate-300">Previous exclusion by {item.reviewer}: {item.original_reason}</p>
        <p className="text-xs text-slate-400">Old criterion: {item.old_criterion}</p>
        <p className="text-xs text-amber-300">New criterion: {item.new_criterion || 'Removed'}</p>
        {!!item.matched_new_terms.length && <p className="text-xs">Matched new terms: {item.matched_new_terms.join(', ')}</p>}
        <blockquote className="text-xs text-slate-300 border-l-2 border-amber-600 pl-3">{item.evidence_excerpt || 'No abstract available'}</blockquote>
      </article>)}
    </section>
    <section className="space-y-3">
      <h3 className="text-lg font-semibold">Study families ({families.length})</h3>
      <p className="text-sm text-slate-400">Exact duplicate groups and possible reports from the same registered trial are shown separately. A shared registration needs human confirmation.</p>
      {!families.length && <p className="text-sm text-slate-400">No linked publications found in this review yet.</p>}
      {families.map(family => <article key={`${family.relationship}-${family.id}`} className="rounded-xl border border-cyan-700/40 bg-slate-900 p-4 space-y-2">
        <div className="flex flex-wrap gap-2 items-center"><strong className="text-sm">{family.relationship === 'duplicate_records' ? 'Duplicate records' : 'Possible reports of one trial'}</strong><span className="text-xs text-cyan-300">{family.id}</span></div>
        <p className="text-xs text-slate-400">{family.evidence}</p>
        <ol className="ml-2 border-l-2 border-cyan-700 space-y-3">{family.records.map(record => <li key={record.id} className="relative pl-5 text-xs text-slate-200">
          <span aria-hidden="true" className="absolute -left-[7px] top-1 h-3 w-3 rounded-full border-2 border-cyan-400 bg-slate-900" />
          {record.title} <span className="text-slate-400">({record.source}{record.pmid ? `, PMID ${record.pmid}` : ''})</span>
        </li>)}</ol>
      </article>)}
    </section>
  </div>;
}
