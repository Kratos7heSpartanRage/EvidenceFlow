// Centralized API Client for EvidenceFlow
// Implements all contracts in docs/API_CONTRACTS.md
// Seamlessly delegates to live backend (/api) with automatic mock state fallback for offline dev/demo

import {
  Review,
  CriteriaVersion,
  Criterion,
  QueryVersion,
  LiteratureRecord,
  DuplicatePair,
  PairDecision,
  ScreeningDecision,
  PicoAnnotation,
  Conflict,
  PipelineRun,
  DiffSummary,
  AuditEvent,
  PreviewResponse,
  RecordListResponse
} from '../types/api';

import {
  mockReview,
  mockCriteriaVersion,
  mockQueryVersions,
  mockRecords,
  mockDuplicatePairs,
  mockPairDecisions,
  mockPicoAnnotations,
  mockConflicts,
  mockRuns,
  mockDiffSummary,
  mockAuditEvents
} from '../mocks/mockData';

// Track active reviewer in memory and localStorage
export function getActiveReviewer(): string {
  if (typeof window !== 'undefined') {
    return localStorage.getItem('evidenceflow_reviewer') || 'Member D';
  }
  return 'Member D';
}

export function setActiveReviewer(name: string): void {
  if (typeof window !== 'undefined') {
    localStorage.setItem('evidenceflow_reviewer', name);
    window.dispatchEvent(new Event('reviewer_changed'));
  }
}

// In-Memory Reactive State for Mock Fallback
class MockStateStore {
  review: Review = JSON.parse(JSON.stringify(mockReview));
  criteriaVersion: CriteriaVersion = JSON.parse(JSON.stringify(mockCriteriaVersion));
  queryVersions: QueryVersion[] = JSON.parse(JSON.stringify(mockQueryVersions));
  records: LiteratureRecord[] = JSON.parse(JSON.stringify(mockRecords));
  duplicatePairs: DuplicatePair[] = JSON.parse(JSON.stringify(mockDuplicatePairs));
  pairDecisions: PairDecision[] = JSON.parse(JSON.stringify(mockPairDecisions));
  picoAnnotations: PicoAnnotation[] = JSON.parse(JSON.stringify(mockPicoAnnotations));
  conflicts: Conflict[] = JSON.parse(JSON.stringify(mockConflicts));
  runs: PipelineRun[] = JSON.parse(JSON.stringify(mockRuns));
  diffSummary: DiffSummary = JSON.parse(JSON.stringify(mockDiffSummary));
  auditEvents: AuditEvent[] = JSON.parse(JSON.stringify(mockAuditEvents));

  reset() {
    this.review = JSON.parse(JSON.stringify(mockReview));
    this.criteriaVersion = JSON.parse(JSON.stringify(mockCriteriaVersion));
    this.queryVersions = JSON.parse(JSON.stringify(mockQueryVersions));
    this.records = JSON.parse(JSON.stringify(mockRecords));
    this.duplicatePairs = JSON.parse(JSON.stringify(mockDuplicatePairs));
    this.pairDecisions = JSON.parse(JSON.stringify(mockPairDecisions));
    this.picoAnnotations = JSON.parse(JSON.stringify(mockPicoAnnotations));
    this.conflicts = JSON.parse(JSON.stringify(mockConflicts));
    this.runs = JSON.parse(JSON.stringify(mockRuns));
    this.diffSummary = JSON.parse(JSON.stringify(mockDiffSummary));
    this.auditEvents = JSON.parse(JSON.stringify(mockAuditEvents));
  }
}

export const mockStore = new MockStateStore();

let isBackendAvailable: boolean | null = null;

async function checkBackend(): Promise<boolean> {
  if (isBackendAvailable !== null) return isBackendAvailable;
  if (typeof process !== 'undefined' && process.env?.NODE_ENV === 'test') {
    isBackendAvailable = false;
    return false;
  }
  try {
    const res = await fetch('/api/health', { signal: AbortSignal.timeout(800) });
    isBackendAvailable = res.ok;
  } catch {
    isBackendAvailable = false;
  }
  return isBackendAvailable;
}

export class ApiError extends Error {
  code: string;
  details?: Record<string, any>;
  constructor(message: string, code: string, credentials?: Record<string, any>) {
    super(message);
    this.name = 'ApiError';
    this.code = code;
    this.details = credentials;
  }
}

export const api = {
  // Check backend health
  async getHealth(): Promise<{ status: string; db: string; mode: 'live' | 'mock' }> {
    const live = await checkBackend();
    if (live) {
      const res = await fetch('/api/health');
      const data = await res.json();
      return { ...data, mode: 'live' };
    }
    return { status: 'healthy', db: 'sqlite_in_memory', mode: 'mock' };
  },

  // Review & Criteria (Step 0)
  async getReview(id: number): Promise<Review> {
    const live = await checkBackend();
    if (live) {
      const res = await fetch(`/api/reviews/${id}`);
      if (!res.ok) throw new ApiError('Failed to fetch review', 'FETCH_FAILED');
      return res.json();
    }
    // Update dynamic stats
    const records = mockStore.records;
    const included = records.filter(r => r.current_decision?.decision === 'include').length;
    const excluded = records.filter(r => r.current_decision?.decision === 'exclude').length;
    const maybe = records.filter(r => r.current_decision?.decision === 'maybe').length;
    const unscreened = records.filter(r => !r.current_decision).length;
    const conflicts = mockStore.conflicts.filter(c => c.status === 'open').length;
    const uncertainPairs = mockStore.duplicatePairs.filter(p => p.tier === 'uncertain').length;

    mockStore.review.stats = {
      total_records: records.length,
      unique_groups: new Set(records.map(r => r.group_id)).size,
      included,
      excluded,
      maybe,
      unscreened,
      conflicts,
      uncertain_duplicates: uncertainPairs
    };
    return mockStore.review;
  },

  async updateReview(id: number, patch: Partial<Review>): Promise<Review> {
    const live = await checkBackend();
    if (live) {
      const res = await fetch(`/api/reviews/${id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(patch)
      });
      return res.json();
    }
    Object.assign(mockStore.review, patch);
    mockStore.auditEvents.unshift({
      id: Date.now(),
      review_id: id,
      actor: `reviewer:${getActiveReviewer()}`,
      action: 'update_review',
      entity_type: 'review',
      entity_id: id,
      before_json: null,
      after_json: patch,
      run_id: null,
      created_at: new Date().toISOString()
    });
    return mockStore.review;
  },

  async getCriteria(reviewId: number): Promise<CriteriaVersion> {
    const live = await checkBackend();
    if (live) {
      const res = await fetch(`/api/reviews/${reviewId}/criteria`);
      return res.json();
    }
    return mockStore.criteriaVersion;
  },

  async updateCriteria(reviewId: number, criteria: Criterion[]): Promise<CriteriaVersion> {
    const live = await checkBackend();
    if (live) {
      const res = await fetch(`/api/reviews/${reviewId}/criteria`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ criteria })
      });
      return res.json();
    }
    const newVerNo = mockStore.criteriaVersion.version_no + 1;
    const newCriteriaVersion: CriteriaVersion = {
      id: Date.now(),
      review_id: reviewId,
      version_no: newVerNo,
      created_at: new Date().toISOString(),
      created_by: getActiveReviewer(),
      criteria: criteria.map((c, i) => ({ ...c, id: c.id || Date.now() + i, criteria_version_id: Date.now() }))
    };
    mockStore.criteriaVersion = newCriteriaVersion;
    mockStore.review.active_criteria_version_id = newCriteriaVersion.id;

    mockStore.auditEvents.unshift({
      id: Date.now(),
      review_id: reviewId,
      actor: `reviewer:${getActiveReviewer()}`,
      action: 'update_criteria_version',
      entity_type: 'criteria_version',
      entity_id: newCriteriaVersion.id,
      before_json: { version: newVerNo - 1 },
      after_json: { version: newVerNo, criteria_count: criteria.length },
      run_id: null,
      created_at: new Date().toISOString()
    });

    return newCriteriaVersion;
  },

  // Queries & Search (Steps 1 & 2)
  async getQueries(reviewId: number): Promise<QueryVersion[]> {
    const live = await checkBackend();
    if (live) {
      const res = await fetch(`/api/reviews/${reviewId}/queries`);
      return res.json();
    }
    return mockStore.queryVersions;
  },

  async createQuery(reviewId: number, data: {
    expression: string;
    date_from?: string;
    date_to?: string;
    source: 'europe_pmc' | 'pubmed';
    options_json?: Record<string, any>;
    import_cap?: number;
    label?: string;
    parent_id?: number | null;
  }): Promise<QueryVersion> {
    const live = await checkBackend();
    if (live) {
      const res = await fetch(`/api/reviews/${reviewId}/queries`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
      });
      return res.json();
    }
    const versionNo = mockStore.queryVersions.length + 1;
    const newQuery: QueryVersion = {
      id: Date.now(),
      review_id: reviewId,
      lineage_root_id: 1,
      parent_id: data.parent_id || null,
      version_no: versionNo,
      label: data.label || `Query Version ${versionNo}`,
      source: data.source,
      expression: data.expression,
      date_from: data.date_from || '2015-01-01',
      date_to: data.date_to || '2025-12-31',
      options_json: data.options_json || { synonym: false },
      import_cap: data.import_cap || 500,
      status: 'draft',
      hit_count: null,
      imported_count: null,
      created_at: new Date().toISOString(),
      executed_at: null,
      request_fingerprint: `fp-v${versionNo}-${Date.now()}`
    };
    mockStore.queryVersions.push(newQuery);

    mockStore.auditEvents.unshift({
      id: Date.now(),
      review_id: reviewId,
      actor: `reviewer:${getActiveReviewer()}`,
      action: 'create_query_version',
      entity_type: 'query_version',
      entity_id: newQuery.id,
      before_json: null,
      after_json: { version_no: versionNo, expression: data.expression, source: data.source },
      run_id: null,
      created_at: new Date().toISOString()
    });

    return newQuery;
  },

  async previewQuery(queryId: number): Promise<PreviewResponse> {
    const live = await checkBackend();
    if (live) {
      const res = await fetch(`/api/queries/${queryId}/preview`, { method: 'POST' });
      return res.json();
    }
    const q = mockStore.queryVersions.find(item => item.id === queryId);
    if (!q) throw new ApiError('Query version not found', 'NOT_FOUND');

    q.status = 'previewed';
    q.hit_count = q.source === 'europe_pmc' ? 2450 : 1980;

    return {
      query_version_id: queryId,
      hit_count: q.hit_count,
      sample_records: mockStore.records.slice(0, 10).map(r => ({
        id: r.id,
        title: r.title,
        authors: r.authors_json,
        year: r.year,
        journal: r.journal,
        source: r.source,
        doi: r.doi_norm,
        pmid: r.pmid,
        abstract: r.abstract
      }))
    };
  },

  async importQuery(queryId: number): Promise<{ run_id: number }> {
    const live = await checkBackend();
    if (live) {
      const res = await fetch(`/api/queries/${queryId}/import`, { method: 'POST' });
      return res.json();
    }
    const q = mockStore.queryVersions.find(item => item.id === queryId);
    if (!q) throw new ApiError('Query version not found', 'NOT_FOUND');

    q.status = 'importing';
    const runId = Date.now();
    const newRun: PipelineRun = {
      id: runId,
      review_id: q.review_id,
      query_version_id: queryId,
      trigger: 'import',
      active_version_ids_json: [queryId],
      status: 'running',
      started_at: new Date().toISOString(),
      finished_at: null,
      error: null,
      steps: [
        { id: 101, run_id: runId, step: 'fetch', status: 'running', started_at: new Date().toISOString(), finished_at: null },
        { id: 102, run_id: runId, step: 'store', status: 'pending', started_at: null, finished_at: null },
        { id: 103, run_id: runId, step: 'dedup', status: 'pending', started_at: null, finished_at: null },
        { id: 104, run_id: runId, step: 'reconcile', status: 'pending', started_at: null, finished_at: null },
        { id: 105, run_id: runId, step: 'screen', status: 'pending', started_at: null, finished_at: null },
        { id: 106, run_id: runId, step: 'pico', status: 'pending', started_at: null, finished_at: null },
        { id: 107, run_id: runId, step: 'diff', status: 'pending', started_at: null, finished_at: null }
      ]
    };
    mockStore.runs.unshift(newRun);

    // Simulate progress in steps for demo
    setTimeout(() => {
      newRun.steps[0].status = 'completed';
      newRun.steps[0].finished_at = new Date().toISOString();
      newRun.steps[0].output_summary_json = { fetched: 500, hits: q.hit_count };
      newRun.steps[1].status = 'completed';
      newRun.steps[1].finished_at = new Date().toISOString();
      newRun.steps[2].status = 'completed';
      newRun.steps[2].finished_at = new Date().toISOString();
      newRun.steps[3].status = 'completed';
      newRun.steps[3].finished_at = new Date().toISOString();
      newRun.steps[4].status = 'completed';
      newRun.steps[4].finished_at = new Date().toISOString();
      newRun.steps[5].status = 'completed';
      newRun.steps[5].finished_at = new Date().toISOString();
      newRun.steps[6].status = 'completed';
      newRun.steps[6].finished_at = new Date().toISOString();
      newRun.status = 'completed';
      newRun.finished_at = new Date().toISOString();
      q.status = 'imported';
      q.imported_count = 500;
      q.executed_at = new Date().toISOString();
    }, 2000);

    return { run_id: runId };
  },

  async getRun(runId: number): Promise<PipelineRun> {
    const live = await checkBackend();
    if (live) {
      const res = await fetch(`/api/runs/${runId}`);
      return res.json();
    }
    const run = mockStore.runs.find(r => r.id === runId);
    if (!run) throw new ApiError('Run not found', 'NOT_FOUND');
    return run;
  },

  async getReviewRuns(reviewId: number): Promise<PipelineRun[]> {
    const live = await checkBackend();
    if (live) {
      const res = await fetch(`/api/reviews/${reviewId}/runs`);
      return res.json();
    }
    return mockStore.runs.filter(r => r.review_id === reviewId);
  },

  // Records & Queues
  async getRecords(reviewId: number, params?: {
    status?: string;
    decision?: string;
    q?: string;
    version?: number;
    show_hidden?: boolean;
    page?: number;
    page_size?: number;
  }): Promise<RecordListResponse> {
    const live = await checkBackend();
    if (live) {
      const url = new URL(`/api/reviews/${reviewId}/records`, window.location.origin);
      if (params) {
        Object.entries(params).forEach(([k, v]) => {
          if (v !== undefined) url.searchParams.set(k, String(v));
        });
      }
      const res = await fetch(url.toString());
      return res.json();
    }

    let items = [...mockStore.records];
    if (!params?.show_hidden) {
      items = items.filter(r => r.is_representative);
    }
    if (params?.decision) {
      if (params.decision === 'unscreened') {
        items = items.filter(r => !r.current_decision);
      } else {
        items = items.filter(r => r.current_decision?.decision === params.decision);
      }
    }
    if (params?.q) {
      const query = params.q.toLowerCase();
      items = items.filter(r =>
        r.title.toLowerCase().includes(query) ||
        r.authors_json.some(a => a.toLowerCase().includes(query)) ||
        r.journal?.toLowerCase().includes(query) ||
        r.abstract?.toLowerCase().includes(query)
      );
    }
    if (params?.version) {
      items = items.filter(r => r.query_versions?.includes(params.version!));
    }

    return {
      items,
      total: items.length,
      page: params?.page || 1,
      page_size: params?.page_size || 50,
      total_pages: 1
    };
  },

  async getRecordDetail(recordId: number): Promise<LiteratureRecord> {
    const live = await checkBackend();
    if (live) {
      const res = await fetch(`/api/records/${recordId}`);
      return res.json();
    }
    const rec = mockStore.records.find(r => r.id === recordId);
    if (!rec) throw new ApiError('Record not found', 'NOT_FOUND');
    return rec;
  },

  // Duplicates Queue (Step 4)
  async getDuplicatePairs(reviewId: number, params?: { tier?: string; decided?: boolean }): Promise<DuplicatePair[]> {
    const live = await checkBackend();
    if (live) {
      const url = new URL(`/api/reviews/${reviewId}/duplicate-pairs`, window.location.origin);
      if (params?.tier) url.searchParams.set('tier', params.tier);
      if (params?.decided !== undefined) url.searchParams.set('decided', String(params.decided));
      const res = await fetch(url.toString());
      return res.json();
    }
    let pairs = [...mockStore.duplicatePairs];
    if (params?.tier) {
      pairs = pairs.filter(p => p.tier === params.tier);
    }
    // populate record_a and record_b
    return pairs.map(p => ({
      ...p,
      record_a: mockStore.records.find(r => r.id === p.record_a_id) || p.record_a,
      record_b: mockStore.records.find(r => r.id === p.record_b_id) || p.record_b
    }));
  },

  async submitPairDecision(reviewId: number, data: {
    record_a_id: number;
    record_b_id: number;
    decision: 'confirm' | 'reject';
    note?: string;
    reviewer: string;
  }): Promise<PairDecision> {
    const live = await checkBackend();
    if (live) {
      const res = await fetch(`/api/reviews/${reviewId}/pair-decisions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
      });
      return res.json();
    }

    const decision: PairDecision = {
      id: Date.now(),
      review_id: reviewId,
      record_a_id: data.record_a_id,
      record_b_id: data.record_b_id,
      decision: data.decision,
      note: data.note || null,
      reviewer: data.reviewer,
      created_at: new Date().toISOString(),
      superseded_by_id: null
    };
    mockStore.pairDecisions.push(decision);

    // If confirmed: record_b becomes hidden, joins record_a group
    if (data.decision === 'confirm') {
      const recB = mockStore.records.find(r => r.id === data.record_b_id);
      const recA = mockStore.records.find(r => r.id === data.record_a_id);
      if (recB && recA) {
        recB.is_representative = false;
        recB.group_id = recA.group_id;
        // propagate decision if recA decided
        if (recA.current_decision) {
          recB.current_decision = {
            id: Date.now() + 1,
            review_id: reviewId,
            record_id: recB.id,
            decision: recA.current_decision.decision,
            reason_text: `Inherited from representative #${recA.id}`,
            reviewer: data.reviewer,
            origin: 'inherited',
            criteria_version_id: mockStore.criteriaVersion.id,
            created_at: new Date().toISOString()
          };
        }
      }
    }

    mockStore.auditEvents.unshift({
      id: Date.now(),
      review_id: reviewId,
      actor: `reviewer:${data.reviewer}`,
      action: data.decision === 'confirm' ? 'confirm_duplicate_pair' : 'reject_duplicate_pair',
      entity_type: 'pair_decision',
      entity_id: decision.id,
      before_json: null,
      after_json: data,
      run_id: null,
      created_at: new Date().toISOString()
    });

    return decision;
  },

  // Screening Queue (Step 5)
  async submitScreeningDecision(recordId: number, data: {
    decision: 'include' | 'exclude' | 'maybe';
    criterion_id?: number | null;
    reason_text?: string;
    note?: string;
    reviewer: string;
  }): Promise<ScreeningDecision> {
    // ENFORCE CRITICAL REQUIREMENT: Exclude MUST have a reason
    if (data.decision === 'exclude' && !data.criterion_id && !data.reason_text?.trim()) {
      throw new ApiError(
        'An exclusion reason or criterion is required to exclude a study.',
        'EXCLUSION_REASON_REQUIRED',
        { record_id: recordId }
      );
    }

    const live = await checkBackend();
    if (live) {
      const res = await fetch(`/api/records/${recordId}/screening`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
      });
      if (!res.ok) {
        const err = await res.json();
        throw new ApiError(err?.error?.message || 'Screening error', err?.error?.code || 'SCREENING_FAILED');
      }
      return res.json();
    }

    const rec = mockStore.records.find(r => r.id === recordId);
    if (!rec) throw new ApiError('Record not found', 'NOT_FOUND');

    const decision: ScreeningDecision = {
      id: Date.now(),
      review_id: rec.review_id,
      record_id: recordId,
      decision: data.decision,
      criterion_id: data.criterion_id || null,
      reason_text: data.reason_text || (data.criterion_id ? mockStore.criteriaVersion.criteria.find(c => c.id === data.criterion_id)?.label : null),
      note: data.note || null,
      reviewer: data.reviewer,
      origin: 'direct',
      criteria_version_id: mockStore.criteriaVersion.id,
      created_at: new Date().toISOString()
    };

    // Apply to group
    const groupMembers = mockStore.records.filter(r => r.group_id === rec.group_id);
    groupMembers.forEach(member => {
      member.current_decision = {
        ...decision,
        id: member.id === recordId ? decision.id : Date.now() + member.id,
        record_id: member.id,
        origin: member.id === recordId ? 'direct' : 'group_applied'
      };
    });

    mockStore.auditEvents.unshift({
      id: Date.now(),
      review_id: rec.review_id,
      actor: `reviewer:${data.reviewer}`,
      action: 'screening_decision',
      entity_type: 'screening_decision',
      entity_id: decision.id,
      before_json: rec.current_decision ? { decision: rec.current_decision.decision } : null,
      after_json: { decision: data.decision, reason: decision.reason_text, group_id: rec.group_id },
      run_id: null,
      created_at: new Date().toISOString()
    });

    return decision;
  },

  // PICO Workspace (Step 6)
  async getPicoAnnotations(recordId: number): Promise<PicoAnnotation[]> {
    const live = await checkBackend();
    if (live) {
      const res = await fetch(`/api/records/${recordId}/pico`);
      return res.json();
    }
    return mockStore.picoAnnotations.filter(p => p.record_id === recordId);
  },

  async updatePico(recordId: number, op: {
    op: 'confirm' | 'correct' | 'reject' | 'add' | 'mark_unknown';
    annotation: Partial<PicoAnnotation>;
    reviewer: string;
  }): Promise<PicoAnnotation> {
    const live = await checkBackend();
    if (live) {
      const res = await fetch(`/api/records/${recordId}/pico`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(op)
      });
      return res.json();
    }

    const ann: PicoAnnotation = {
      id: Date.now(),
      record_id: recordId,
      label: op.annotation.label || 'P',
      text: op.annotation.text || '',
      start_char: op.annotation.start_char ?? 0,
      end_char: op.annotation.end_char ?? 0,
      origin: 'human',
      status: op.op === 'confirm' ? 'confirmed' : op.op === 'correct' ? 'corrected' : op.op === 'add' ? 'added' : 'rejected',
      supersedes_id: op.annotation.id || null,
      content_hash: 'manual-hash',
      algo_version: 'v1.0',
      reviewer: op.reviewer,
      created_at: new Date().toISOString()
    };

    mockStore.picoAnnotations.push(ann);

    mockStore.auditEvents.unshift({
      id: Date.now(),
      review_id: mockStore.review.id,
      actor: `reviewer:${op.reviewer}`,
      action: `pico_${op.op}`,
      entity_type: 'pico_annotation',
      entity_id: ann.id,
      before_json: op.annotation.id ? { id: op.annotation.id } : null,
      after_json: { label: ann.label, text: ann.text, status: ann.status },
      run_id: null,
      created_at: new Date().toISOString()
    });

    return ann;
  },

  // Level 2 Loop: History, Diff, Conflicts & Revert
  async getDiff(queryId: number, againstVersionId?: number): Promise<DiffSummary> {
    const live = await checkBackend();
    if (live) {
      const url = new URL(`/api/queries/${queryId}/diff`, window.location.origin);
      if (againstVersionId) url.searchParams.set('against', String(againstVersionId));
      const res = await fetch(url.toString());
      return res.json();
    }
    return mockStore.diffSummary;
  },

  async getConflicts(reviewId: number): Promise<Conflict[]> {
    const live = await checkBackend();
    if (live) {
      const res = await fetch(`/api/reviews/${reviewId}/conflicts`);
      return res.json();
    }
    return mockStore.conflicts;
  },

  async resolveConflict(conflictId: number, data: {
    resolution: 'unify' | 'split' | 'maybe';
    decision?: 'include' | 'exclude' | 'maybe';
    reason?: string;
    reviewer: string;
  }): Promise<Conflict> {
    const live = await checkBackend();
    if (live) {
      const res = await fetch(`/api/conflicts/${conflictId}/resolve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
      });
      return res.json();
    }

    const conf = mockStore.conflicts.find(c => c.id === conflictId);
    if (!conf) throw new ApiError('Conflict not found', 'NOT_FOUND');

    conf.status = 'resolved';
    conf.resolved_at = new Date().toISOString();
    conf.resolution_json = data;
    conf.reviewer = data.reviewer;

    if (data.resolution === 'unify' && data.decision) {
      conf.record_ids_json.forEach(rid => {
        const r = mockStore.records.find(item => item.id === rid);
        if (r) {
          r.current_decision = {
            id: Date.now() + rid,
            review_id: conf.review_id,
            record_id: rid,
            decision: data.decision!,
            reason_text: data.reason || 'Resolved via group conflict resolution',
            reviewer: data.reviewer,
            origin: 'conflict_resolution',
            criteria_version_id: mockStore.criteriaVersion.id,
            created_at: new Date().toISOString()
          };
        }
      });
    }

    mockStore.auditEvents.unshift({
      id: Date.now(),
      review_id: conf.review_id,
      actor: `reviewer:${data.reviewer}`,
      action: 'resolve_conflict',
      entity_type: 'conflict',
      entity_id: conflictId,
      before_json: { status: 'open' },
      after_json: data,
      run_id: null,
      created_at: new Date().toISOString()
    });

    return conf;
  },

  async revertQuery(queryId: number): Promise<{ message: string; version_no: number }> {
    const live = await checkBackend();
    if (live) {
      const res = await fetch(`/api/queries/${queryId}/revert`, { method: 'POST' });
      return res.json();
    }
    const targetQ = mockStore.queryVersions.find(q => q.id === queryId);
    if (!targetQ) throw new ApiError('Target query version not found', 'NOT_FOUND');

    // Invert scope to target version active set
    mockStore.records.forEach(r => {
      r.is_representative = r.query_versions?.includes(targetQ.version_no) ?? true;
    });

    mockStore.auditEvents.unshift({
      id: Date.now(),
      review_id: mockStore.review.id,
      actor: `reviewer:${getActiveReviewer()}`,
      action: 'exact_revert',
      entity_type: 'query_version',
      entity_id: queryId,
      before_json: { active_versions: [1, 2] },
      after_json: { active_versions: [targetQ.version_no], restored_group_snapshot: true },
      run_id: null,
      created_at: new Date().toISOString()
    });

    return { message: 'Reverted successfully without API refetch', version_no: targetQ.version_no };
  },

  // Audit Log (Append-only)
  async getAuditEvents(reviewId: number): Promise<AuditEvent[]> {
    const live = await checkBackend();
    if (live) {
      const res = await fetch(`/api/reviews/${reviewId}/audit`);
      return res.json();
    }
    return mockStore.auditEvents;
  },

  // Export CSV
  async exportCsv(reviewId: number): Promise<string> {
    const live = await checkBackend();
    if (live) {
      const res = await fetch(`/api/reviews/${reviewId}/export.csv`);
      return res.text();
    }

    const includedReps = mockStore.records.filter(r => r.is_representative && r.current_decision?.decision === 'include');
    const header = ['ID', 'Title', 'First Author', 'Year', 'Journal', 'DOI', 'PMID', 'Decision', 'Reviewer', 'Reason', 'Population (P)', 'Intervention (I)', 'Comparator (C)', 'Outcome (O)'].join(',');
    const rows = includedReps.map(r => {
      const picos = mockStore.picoAnnotations.filter(p => p.record_id === r.id);
      const p = picos.find(x => x.label === 'P')?.text || '';
      const i = picos.find(x => x.label === 'I')?.text || '';
      const c = picos.find(x => x.label === 'C')?.text || '';
      const o = picos.find(x => x.label === 'O')?.text || '';
      return [
        r.id,
        `"${r.title.replace(/"/g, '""')}"`,
        `"${r.first_author_norm || ''}"`,
        r.year || '',
        `"${(r.journal || '').replace(/"/g, '""')}"`,
        r.doi_norm || '',
        r.pmid || '',
        r.current_decision?.decision || '',
        `"${r.current_decision?.reviewer || ''}"`,
        `"${(r.current_decision?.reason_text || '').replace(/"/g, '""')}"`,
        `"${p.replace(/"/g, '""')}"`,
        `"${i.replace(/"/g, '""')}"`,
        `"${c.replace(/"/g, '""')}"`,
        `"${o.replace(/"/g, '""')}"`
      ].join(',');
    });
    return [header, ...rows].join('\n');
  }
};
