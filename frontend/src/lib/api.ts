import type {
  AuditEvent,
  Conflict,
  CriteriaVersion,
  Criterion,
  DecisionType,
  DiffSummary,
  DuplicatePair,
  EntityId,
  LiteratureRecord,
  PicoAnnotation,
  PipelineRun,
  PreviewResponse,
  QueryVersion,
  RecordListResponse,
  Review,
  ScreeningDecision,
} from '../types/api';
import type * as Wire from '../types/backend';

export function getActiveReviewer(): string {
  return localStorage.getItem('evidenceflow_reviewer') || 'Reviewer';
}
export function setActiveReviewer(name: string) {
  localStorage.setItem('evidenceflow_reviewer', name.trim() || 'Reviewer');
  window.dispatchEvent(new Event('reviewer_changed'));
}

export class ApiError extends Error {
  constructor(message: string, public code: string, public details?: unknown) {
    super(message);
    this.name = 'ApiError';
  }
}
const baseUrl = (import.meta.env.VITE_API_BASE_URL || '/api').replace(/\/$/, '');
export async function request<T>(path: string, method = 'GET', body?: unknown): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${baseUrl}${path}`, {
      method, headers: body === undefined ? undefined : { 'Content-Type': 'application/json' },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch {
    throw new ApiError('Cannot reach the backend. Start the backend server, then retry.', 'NETWORK_ERROR');
  }
  if (!response.ok) {
    const payload = await response.json().catch(() => null);
    const issues = payload?.error?.details?.errors || payload?.detail;
    const message = (Array.isArray(issues) ? issues.map((item: { loc?: string[]; msg: string; }) => `${item.loc?.slice(1).join('.') || 'Request'}: ${item.msg}`).join('; ') : null) || payload?.error?.message || (Array.isArray(payload?.detail)
      ? payload.detail.map((item: { loc?: string[]; msg: string; }) => `${item.loc?.slice(1).join('.') || 'Request'}: ${item.msg}`).join('; ')
      : typeof payload?.detail === 'string' ? payload.detail : `Request failed (${response.status})`);
    throw new ApiError(message, payload?.error?.code || `HTTP_${response.status}`, payload);
  }
  if (response.headers.get('content-type')?.includes('text/csv')) return await response.text() as T;
  return response.json() as Promise<T>;
}
const id = (value: EntityId) => encodeURIComponent(String(value));
function toCriterion(c: Wire.Criterion): Criterion {
  return {
    id: c.id, criteria_version_id: c.criteria_version_id, kind: c.type === 'inclusion' ? 'include' : 'exclude',
    code: c.detector_rule || 'manual', label: c.label, reason: c.description,
    detector: c.detector_rule ? 'rule' : 'manual_only', is_active: true,
    detector_rule: c.detector_rule, field_target: c.field_target
  };
}
function fromCriterion(c: Criterion): Wire.CriterionInput {
  return {
    type: c.kind === 'include' ? 'inclusion' : 'exclusion', label: c.label, description: c.reason,
    detector_rule: c.detector_rule?.trim() || null, field_target: c.field_target || null
  };
}
function toCriteria(c: Wire.CriteriaVersion): CriteriaVersion {
  return { ...c, version_no: c.version_number, created_by: '', criteria: c.criteria.map(toCriterion) };
}
function toReview(r: Wire.Review): Review {
  return {
    ...r, population: r.pico?.population || r.pico?.P || '', intervention: r.pico?.intervention || r.pico?.I || '',
    comparator: r.pico?.comparator || r.pico?.C || '', outcome: r.pico?.outcome || r.pico?.O || '',
    active_criteria_version_id: r.active_criteria_version?.id,
    stats: {
      total_records: r.counts.total_records, unique_groups: r.counts.unique_studies,
      included: r.counts.screened_included, excluded: r.counts.screened_excluded,
      maybe: r.counts.screened_maybe, unscreened: r.counts.unscreened,
      conflicts: r.counts.open_conflicts, uncertain_duplicates: 0
    }
  };
}
function toQuery(q: Wire.QueryVersion): QueryVersion {
  return {
    ...q, version_no: q.version_number, date_from: q.date_from || undefined,
    date_to: q.date_to || undefined, status: q.status as QueryVersion['status'],
    import_cap: 0, options_json: { synonym: q.expand_synonyms, title_abstract_only: q.title_abstract_only }
  };
}
function toDecision(d: Wire.ScreeningDecision, reviewId: EntityId): ScreeningDecision {
  return { ...d, review_id: reviewId, reviewer: d.reviewer_name, criteria_version_id: '', origin: d.origin };
}
function toPico(p: Wire.PicoSpan, recordId: EntityId): PicoAnnotation {
  return {
    ...p, record_id: recordId, label: p.element, start_char: p.start_index ?? 0,
    end_char: p.end_index, status: (p.status || (p.is_confirmed ? 'confirmed' : 'suggested')) as PicoAnnotation['status'],
    reviewer: p.reviewer || undefined, created_at: ''
  };
}
function toRecord(r: Wire.RecordItem | Wire.RecordDetail): LiteratureRecord {
  const detail = 'abstract' in r ? r as Wire.RecordDetail : undefined;
  const authors = r.authors.map(a => typeof a === 'string' ? a : a.full_name);
  const suggestion = r.suggestion;
  return {
    id: r.id, review_id: r.review_id, source: r.source as LiteratureRecord['source'],
    source_record_id: r.source_record_id, title: r.title, title_norm: r.title.toLowerCase(),
    abstract: detail?.abstract, authors_json: authors, first_author_norm: authors[0],
    journal: r.journal, year: r.publication_year, doi_norm: r.doi, pmid: r.pmid,
    group_id: r.group_id || undefined, group_members_count: detail ? detail.cluster_members.length + 1 : undefined,
    is_representative: r.is_representative, is_hidden: r.is_hidden,
    language: detail?.language, pub_types_json: detail?.publication_types || [], mesh_json: detail?.mesh_headings || [],
    content_hash: '', created_at: '', updated_at: '',
    current_decision: r.decision ? toDecision({ ...r.decision, record_id: r.id }, r.review_id) : null,
    suggestion: suggestion ? {
      id: suggestion.id, record_id: r.id, criteria_version_id: '', content_hash: '',
      algo_version: suggestion.algorithm_version || '', suggestion: suggestion.suggested_decision,
      criterion_id: suggestion.matched_criterion_id,
      evidence_json: {
        explanation: suggestion.evidence_snippets?.map(e => e.explanation).filter(Boolean).join(' ') || suggestion.matched_criterion_label || 'No evidence details supplied by the backend; human review required.',
          rule_hits: suggestion.evidence_snippets?.flatMap(e => e.matched || []),
          metadata_fields_used: suggestion.evidence_snippets?.filter(e => e.source === 'metadata').flatMap(e => e.field ? [e.field] : []),
        strength: suggestion.confidence >= 1 ? 'strong' : suggestion.confidence > 0 ? 'weak' : 'none'
      }, created_at: ''
    } : null,
    decision_history: detail?.decisions.map(d => toDecision({ ...d, record_id: r.id }, r.review_id)),
    pico_annotations: detail?.pico_spans.map(p => toPico(p, r.id))
  };
}
export interface RecordFilters {
  status?: string; decision?: string; q?: string; version?: EntityId;
  show_hidden?: boolean; page?: number; page_size?: number;
}
async function recordPages(reviewId: EntityId, params: RecordFilters = {}): Promise<RecordListResponse> {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && key !== 'show_hidden') search.set(key, String(value));
  }
  search.set('status', params.status || 'active');
  search.set('representatives_only', String(!params.show_hidden));
  search.set('page_size', String(params.page_size || 500));
  search.set('page', String(params.page || 1));
  const response = await request<{ items: Wire.RecordItem[]; total: number; page: number; page_size: number; }>(`/reviews/${id(reviewId)}/records?${search}`);
  const items = response.items.map(toRecord);
  if (params.page === undefined) {
    for (let page = 2;items.length < response.total;page++) {
      search.set('page', String(page));
      const next = await request<typeof response>(`/reviews/${id(reviewId)}/records?${search}`);
      if (!next.items.length) break;
      items.push(...next.items.map(toRecord));
    }
  }
  return { ...response, items, total_pages: Math.ceil(response.total / response.page_size) };
}
export const api = {
  async getHealth() {
    const health = await request<{ status: string; database: string; }>('/health');
    if (health.database === 'disconnected') throw new ApiError('Backend database is unavailable. Apply migrations and retry.', 'DATABASE_ERROR');
    return health;
  },
  async listReviews(): Promise<Review[]> { return (await request<Wire.Review[]>('/reviews')).map(toReview); },
  async createReview(data: Pick<Review, 'title' | 'question'>): Promise<Review> {
    return toReview(await request<Wire.Review>('/reviews', 'POST', { ...data, pico: {} }));
  },
  async getReview(reviewId: EntityId): Promise<Review> {
    const [review, pairs] = await Promise.all([
      request<Wire.Review>(`/reviews/${id(reviewId)}`),
      request<Wire.DuplicatePair[]>(`/reviews/${id(reviewId)}/duplicate-pairs?tier=tier_3_review_needed&decided=false`),
    ]);
    const result = toReview(review);
    result.stats!.uncertain_duplicates = pairs.length;
    return result;
  },
  async updateReview(reviewId: EntityId, patch: Partial<Review>): Promise<Review> {
    return toReview(await request<Wire.Review>(`/reviews/${id(reviewId)}`, 'PATCH', {
      title: patch.title, question: patch.question, pico: {
        population: patch.population,
        intervention: patch.intervention, comparator: patch.comparator, outcome: patch.outcome
      },
    }));
  },
  async getCriteria(reviewId: EntityId): Promise<CriteriaVersion> {
    const review = await request<Wire.Review>(`/reviews/${id(reviewId)}`);
    return review.active_criteria_version ? toCriteria(review.active_criteria_version)
      : { id: '', review_id: reviewId, version_no: 0, created_at: '', created_by: '', criteria: [] };
  },
  async updateCriteria(reviewId: EntityId, criteria: Criterion[]): Promise<CriteriaVersion> {
    return toCriteria(await request<Wire.CriteriaVersion>(`/reviews/${id(reviewId)}/criteria`, 'POST',
      { criteria: criteria.filter(c => c.is_active).map(fromCriterion) }));
  },
  async getQueries(reviewId: EntityId): Promise<QueryVersion[]> {
    return (await request<Wire.QueryVersion[]>(`/reviews/${id(reviewId)}/queries`)).map(toQuery).sort((a, b) => a.version_no - b.version_no);
  },
  async createQuery(reviewId: EntityId, data: {
    expression: string; source: string; date_from?: string; date_to?: string;
    options_json?: { synonym?: boolean; title_abstract_only?: boolean; }; label?: string; parent_id?: EntityId | null
   }): Promise<QueryVersion> {
    return toQuery(await request<Wire.QueryVersion>(`/reviews/${id(reviewId)}/queries`, 'POST', {
      label: data.label || data.expression.slice(0, 120), parent_id: data.parent_id || null,
      spec: {
        expression: data.expression, source: data.source, date_from: data.date_from || null,
        date_to: data.date_to || null, expand_synonyms: data.options_json?.synonym || false,
        title_abstract_only: data.options_json?.title_abstract_only || false
      },
    }));
  },
  async previewQuery(queryId: EntityId): Promise<PreviewResponse> {
    const result = await request<Wire.QueryPreview>(`/queries/${id(queryId)}/preview`, 'POST');
    return {
      query_version_id: result.query_id, hit_count: result.estimated_hits,
      sample_records: result.sample_records, warnings: result.warnings
    };
  },
  async importQuery(queryId: EntityId) { return request<{ run_id: string; status: string; }>(`/queries/${id(queryId)}/import`, 'POST'); },
  async getRun(runId: EntityId): Promise<PipelineRun> {
    const run = await request<Wire.PipelineRun>(`/runs/${id(runId)}`);
    const stepNames: Record<string, PipelineRun['steps'][number]['step']> = {
      fetch_records: 'fetch', deduplicate: 'dedup', screen_heuristics: 'screen', pico_extract: 'pico',
    };
    return {
      ...run, trigger: run.run_type as PipelineRun['trigger'], active_version_ids_json: [],
      finished_at: run.completed_at, error: run.error_message,
      steps: [...run.steps].sort((a, b) => a.step_order - b.step_order).map(s => ({
        ...s,
        step: stepNames[s.name] || 'store', finished_at: s.completed_at,
        output_summary_json: s.message ? { message: s.message } : undefined,
        error: s.status === 'failed' ? s.message : null
      }))
    };
  },
  getRecords: recordPages,
  async getRecord(recordId: EntityId): Promise<LiteratureRecord> { return toRecord(await request<Wire.RecordDetail>(`/records/${id(recordId)}`)); },
  async getDuplicatePairs(reviewId: EntityId, params?: { tier?: 'auto' | 'uncertain'; }): Promise<DuplicatePair[]> {
    const pairs = await request<Wire.DuplicatePair[]>(`/reviews/${id(reviewId)}/duplicate-pairs`);
    return pairs.filter(p => !params?.tier || (params.tier === 'uncertain' ? p.tier === 'tier_3_review_needed' : p.tier !== 'tier_3_review_needed')).map(p => {
      const verdict = [...p.decisions].sort((a, b) => b.created_at.localeCompare(a.created_at))[0];
      return {
        id: p.id, review_id: p.review_id, record_a_id: p.record_a_id, record_b_id: p.record_b_id,
        method: 'unspecified', score: p.similarity_score, tier: p.tier === 'tier_3_review_needed' ? 'uncertain' : 'auto',
        matched_fields_json: p.match_reasons, conflicting_fields_json: [], algo_version: '', created_run_id: '',
        record_a: p.record_a ? toRecord({ ...p.record_a, is_representative: true, is_hidden: false }) : undefined,
        record_b: p.record_b ? toRecord({ ...p.record_b, is_representative: true, is_hidden: false }) : undefined,
        decision: verdict ? {
          ...verdict, review_id: reviewId, record_a_id: p.record_a_id,
          record_b_id: p.record_b_id, reviewer: verdict.reviewer_name
        } : undefined
      };
    });
  },
  async submitPairDecision(reviewId: EntityId, data: { record_a_id: EntityId; record_b_id: EntityId; decision: 'confirm' | 'reject'; note?: string; reviewer: string; }) {
    const { reviewer, ...rest } = data;
    return request<Wire.PairDecisionResult>(`/reviews/${id(reviewId)}/pair-decisions`, 'POST', { ...rest, reviewer_name: reviewer });
  },
  async submitScreeningDecision(recordId: EntityId, data: { decision: DecisionType; criterion_id?: EntityId | null; reason_text?: string; note?: string; reviewer: string; }) {
    const { reviewer, ...rest } = data;
    return request<Wire.ScreeningDecision>(`/records/${id(recordId)}/screening`, 'POST', { ...rest, reviewer_name: reviewer });
  },
  async getPicoAnnotations(recordId: EntityId): Promise<PicoAnnotation[]> {
    return (await request<Wire.RecordDetail>(`/records/${id(recordId)}`)).pico_spans.map(p => toPico(p, recordId));
  },
  async updatePico(recordId: EntityId, operation: { op: 'confirm' | 'correct' | 'reject'; annotation: Partial<PicoAnnotation>; reviewer: string; }) {
    return request<Wire.PicoPatchResult>(`/records/${id(recordId)}/pico`, 'PATCH', {
      reviewer: operation.reviewer, ops: [{
        op: operation.op, span_id: operation.annotation.id, text: operation.op === 'correct' ? operation.annotation.text : undefined,
      }]
    });
  },
  async getDiff(to: EntityId, from: EntityId): Promise<DiffSummary> {
    const diff = await request<Wire.QueryDiff>(`/queries/${id(to)}/diff?against=${id(from)}`);
    return {
      from_version_id: from, to_version_id: to,
      records_added: diff.new_records_count, records_removed: diff.dropped_records_count,
      already_present: diff.retained_records_count, decisions_preserved: diff.already_screened_retained_count,
      conflicts_opened: diff.potential_conflicts_count, metrics_available: false
    };
  },
  async getConflicts(reviewId: EntityId): Promise<Conflict[]> {
    const conflicts = await request<Wire.Conflict[]>(`/reviews/${id(reviewId)}/conflicts?status=all`);
    if (!conflicts.length) return [];
    const records = await recordPages(reviewId, { show_hidden: true, status: 'all' });
    return conflicts.map(c => {
      const members = records.items.filter(r => r.group_id === c.group_id || r.id === c.group_id);
      return {
        id: c.id, review_id: c.review_id, type: c.reason === 'include_vs_exclude' ? 'group_decision_conflict' : 'pair_override_bypassed',
        fingerprint: c.open_fingerprint || c.id, record_ids_json: members.map(r => r.id),
        details_json: {
          explanation: c.resolution_note || c.reason, conflicting_decisions: members.filter(r => r.current_decision).map(r => ({
            record_id: r.id, decision: r.current_decision!.decision, reason: r.current_decision!.reason_text || '',
            reviewer: r.current_decision!.reviewer, time: r.current_decision!.created_at
          }))
        },
        status: c.status, created_run_id: '', resolved_at: c.resolved_at, reviewer: c.resolved_by, records: members
      };
    });
  },
  async resolveConflict(conflictId: EntityId, data: { resolution: 'unify' | 'maybe'; decision?: DecisionType; reason?: string; reviewer: string; }) {
    return request<Wire.ConflictResolveResult>(`/conflicts/${id(conflictId)}/resolve`, 'POST', {
      decision: data.decision || 'maybe', reviewer: data.reviewer, note: data.reason, reason_text: data.reason,
    });
  },
  async revertQuery(queryId: EntityId) { return request<Wire.QueryRevertResult>(`/queries/${id(queryId)}/revert`, 'POST'); },
  async getAuditEvents(reviewId: EntityId): Promise<AuditEvent[]> {
    const items: Wire.AuditEvent[] = [];
    for (let page = 1;;page++) {
      const response = await request<{ items: Wire.AuditEvent[]; total: number; }>(`/reviews/${id(reviewId)}/audit?page=${page}&page_size=500`);
      items.push(...response.items);
      if (items.length >= response.total || !response.items.length) break;
    }
    return items.map(e => ({
      id: e.id, review_id: e.review_id, actor: e.actor, action: e.event_type,
      entity_type: e.target_type, entity_id: e.target_id, before_json: e.before_state, after_json: e.after_state,
      created_at: e.timestamp
    }));
  },
  async exportCsv(reviewId: EntityId) { return request<string>(`/reviews/${id(reviewId)}/export.csv`); },
};
