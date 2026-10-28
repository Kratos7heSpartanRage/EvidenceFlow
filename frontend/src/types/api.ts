// View models used by the workspace. Backend wire contracts are namespaced below.
export type EntityId = string | number;

export interface ReviewStats {
  total_records: number;
  unique_groups: number;
  included: number;
  excluded: number;
  maybe: number;
  unscreened: number;
  conflicts: number;
  uncertain_duplicates: number;
}
/**
 * EvidenceFlow API TypeScript Contracts
 * Workspace view models mapped from the wire contracts in backend.ts.
 */

export type SourceType = 'europe_pmc' | 'pubmed' | 'snapshot';

export type DecisionType = 'include' | 'exclude' | 'maybe';

export type DecisionOrigin = 'human' | 'direct' | 'group_applied' | 'inherited' | 'conflict_resolution';

export type PairDecisionType = 'confirm' | 'reject';

export type DedupTier = 'auto' | 'uncertain';

export type DedupMethod = 'unspecified' | 'doi' | 'pmid' | 'title_year_author' | 'fuzzy';

export type PicoLabel = 'P' | 'I' | 'C' | 'O';

export type PicoStatus = 'suggested' | 'confirmed' | 'corrected' | 'rejected' | 'added' | 'unknown';

export type ConflictType = 'group_decision_conflict' | 'pair_override_bypassed' | 'stale_after_criteria_change';

export type ConflictStatus = 'open' | 'resolved' | 'obsolete';

export type RunStatus = 'queued' | 'pending' | 'running' | 'completed' | 'failed';

export type StepType = 'fetch' | 'store' | 'dedup' | 'reconcile' | 'screen' | 'pico' | 'diff';

export type TriggerType = 'import' | 'criteria_change' | 'pair_decision' | 'revert' | 'workspace_change';

export interface Review {
  id: EntityId;
  title: string;
  question: string;
  population: string;
  intervention: string;
  comparator: string;
  outcome: string;
  active_criteria_version_id?: EntityId | null;
  stats?: ReviewStats;
  created_at: string;
  updated_at: string;
}

export interface Criterion {
  id: EntityId;
  criteria_version_id: EntityId;
  kind: 'include' | 'exclude';
  code: string;
  label: string;
  reason: string;
  detector: 'metadata' | 'rule' | 'metadata_then_rule' | 'manual_only';
  params_json?: Record<string, unknown>;
  is_active: boolean;
  detector_rule?: string | null;
  field_target?: string | null;
}

export interface CriteriaVersion {
  id: EntityId;
  review_id: EntityId;
  version_no: number;
  created_at: string;
  created_by: string;
  criteria: Criterion[];
}

export interface QuerySpec {
  expression: string;
  date_from?: string;
  date_to?: string;
  source: SourceType;
  options?: {
    synonym?: boolean;
    [key: string]: unknown;
  };
  cap?: number;
}

export interface QueryVersion {
  id: EntityId;
  review_id: EntityId;
  lineage_root_id?: EntityId;
  parent_id?: EntityId | null;
  version_no: number;
  label: string;
  source?: SourceType;
  expression?: string;
  date_from?: string;
  date_to?: string;
  options_json?: Record<string, unknown>;
  import_cap: number;
  status: 'draft' | 'previewed' | 'approved' | 'importing' | 'imported' | 'failed';
  hit_count?: number | null;
  imported_count?: number | null;
  created_at: string;
  executed_at?: string | null;
  request_fingerprint?: string;
}

export interface LiteratureRecord {
  id: EntityId;
  review_id: EntityId;
  source: SourceType;
  source_record_id: string;
  doi_norm?: string | null;
  pmid?: string | null;
  pmcid?: string | null;
  title: string;
  title_norm: string;
  abstract?: string | null;
  authors_json: string[];
  first_author_norm?: string | null;
  year?: number | null;
  journal?: string | null;
  journal_norm?: string | null;
  volume?: string | null;
  issue?: string | null;
  pages?: string | null;
  language?: string | null;
  pub_types_json: string[];
  mesh_json: string[];
  raw_json?: Record<string, unknown>;
  content_hash: string;
  created_at: string;
  updated_at: string;
  // Computed fields in workspace:
  is_representative?: boolean;
  group_id?: string;
  group_members_count?: number;
  current_decision?: ScreeningDecision | null;
  suggestion?: ScreeningSuggestion | null;
  query_versions?: number[];
  pico_annotations?: PicoAnnotation[];
  decision_history?: ScreeningDecision[];
  is_hidden?: boolean;
  is_stale?: boolean;
}

export interface DuplicatePair {
  id: EntityId;
  review_id: EntityId;
  record_a_id: EntityId;
  record_b_id: EntityId;
  method: DedupMethod;
  score: number;
  tier: DedupTier;
  matched_fields_json: string[];
  conflicting_fields_json: string[];
  algo_version: string;
  created_run_id: EntityId;
  record_a?: LiteratureRecord;
  record_b?: LiteratureRecord;
  decision?: PairDecision;
}

export interface PairDecision {
  id: EntityId;
  review_id: EntityId;
  record_a_id: EntityId;
  record_b_id: EntityId;
  decision: PairDecisionType;
  note?: string | null;
  reviewer: string;
  created_at: string;
  superseded_by_id?: EntityId | null;
}

export interface RepresentativePin {
  review_id: EntityId;
  record_id: EntityId;
  pinned_at: string;
  reviewer: string;
}

export interface ScreeningSuggestion {
  id: EntityId;
  record_id: EntityId;
  criteria_version_id: EntityId;
  content_hash: string;
  algo_version: string;
  suggestion: DecisionType;
  criterion_id?: EntityId | null;
  criterion?: Criterion;
  evidence_json: {
    rule_hits?: string[];
    metadata_fields_used?: string[];
    strength?: 'strong' | 'weak' | 'none';
    explanation?: string;
    [key: string]: unknown;
  };
  created_at: string;
}

export interface ScreeningDecision {
  id: EntityId;
  review_id: EntityId;
  record_id: EntityId;
  decision: DecisionType;
  criterion_id?: EntityId | null;
  criterion?: Criterion;
  reason_text?: string | null;
  note?: string | null;
  reviewer: string;
  origin: DecisionOrigin;
  criteria_version_id: EntityId;
  created_at: string;
  superseded_by_id?: EntityId | null;
}

export interface PicoAnnotation {
  id: EntityId;
  record_id: EntityId;
  label: PicoLabel;
  text: string;
  start_char: number;
  end_char?: number | null;
  origin: 'machine' | 'human';
  status: PicoStatus;
  supersedes_id?: EntityId | null;
  content_hash?: string;
  algo_version?: string;
  reviewer?: string;
  created_at: string;
}

export interface Conflict {
  id: EntityId;
  review_id: EntityId;
  type: ConflictType;
  fingerprint: string;
  record_ids_json: EntityId[];
  details_json: {
    conflicting_decisions?: {
      record_id: EntityId;
      decision: DecisionType;
      reason?: string;
      reviewer: string;
      time: string;
    }[];
    bridging_pairs?: {
      pair_id: EntityId;
      score: number;
      method: string;
      matched_fields: string[];
    }[];
    explanation?: string;
    [key: string]: unknown;
  };
  status: ConflictStatus;
  created_run_id: EntityId;
  resolved_at?: string | null;
  resolution_json?: Record<string, unknown> | null;
  reviewer?: string | null;
  records?: LiteratureRecord[];
}

export interface PipelineStep {
  id: EntityId;
  run_id: EntityId;
  step: StepType;
  status: RunStatus;
  started_at?: string | null;
  finished_at?: string | null;
  input_summary_json?: Record<string, unknown>;
  output_summary_json?: Record<string, unknown>;
  error?: string | null;
}

export interface PipelineRun {
  id: EntityId;
  review_id: EntityId;
  query_version_id?: EntityId | null;
  trigger: TriggerType;
  active_version_ids_json: EntityId[];
  status: RunStatus;
  started_at: string;
  finished_at?: string | null;
  error?: string | null;
  steps: PipelineStep[];
}

export interface DiffSummary {
  from_version_id: EntityId;
  to_version_id: EntityId;
  added_count?: number;
  records_added?: number;
  removed_count?: number;
  records_removed?: number;
  already_present_count?: number;
  already_present?: number;
  groups_merged_count?: number;
  groups_merged?: number;
  groups_split_count?: number;
  groups_split?: number;
  decisions_preserved_count?: number;
  decisions_preserved?: number;
  decisions_inherited_count?: number;
  decisions_inherited?: number;
  conflicts_opened_count?: number;
  conflicts_opened?: number;
  needing_screening_count?: number;
  metrics_available?: boolean;
  needing_screening?: number;
  added_records?: LiteratureRecord[];
  removed_records?: LiteratureRecord[];
  merged_groups?: {
    group_id: string;
    records: LiteratureRecord[];
    has_conflict: boolean;
  }[];
}

export interface AuditEvent {
  id: EntityId;
  review_id: EntityId;
  actor: string;
  action: string;
  entity_type: string;
  entity_id: EntityId;
  before_json?: Record<string, unknown> | null;
  after_json?: Record<string, unknown> | null;
  run_id?: EntityId | null;
  created_at: string;
}

export interface PreviewResponse {
  query_version_id: EntityId;
  hit_count: number;
  warnings?: string[];
  sample_records: import('./backend').RecordIn[];
  source?: SourceType;
  expression?: string;
}

export interface ResolveConflictRequest {
  action: 'apply_decision' | 'split_duplicates' | 'keep_maybe';
  decision?: DecisionType;
  criterion_id?: EntityId;
  reason_text?: string | null;
  note?: string | null;
  reviewer: string;
}

export interface ScreeningSubmission {
  record_id: EntityId;
  decision: DecisionType;
  criterion_id?: EntityId | null;
  reason_text?: string | null;
  note?: string | null;
  reviewer: string;
}

export interface RecordListResponse {
  items: LiteratureRecord[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}


/** Backend payloads are namespaced to avoid merging incompatible view-model declarations. */
export * as BackendApi from './backend';
