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
 * Fully mirrors backend models and specifications in docs/API_CONTRACTS.md
 */

export type SourceType = 'europe_pmc' | 'pubmed' | 'snapshot';

export type DecisionType = 'include' | 'exclude' | 'maybe';

export type DecisionOrigin = 'direct' | 'group_applied' | 'inherited' | 'conflict_resolution';

export type PairDecisionType = 'confirm' | 'reject';

export type DedupTier = 'auto' | 'uncertain';

export type DedupMethod = 'doi' | 'pmid' | 'title_year_author' | 'fuzzy';

export type PicoLabel = 'P' | 'I' | 'C' | 'O';

export type PicoStatus = 'suggested' | 'confirmed' | 'corrected' | 'rejected' | 'added' | 'unknown';

export type ConflictType = 'group_decision_conflict' | 'pair_override_bypassed' | 'stale_after_criteria_change';

export type ConflictStatus = 'open' | 'resolved' | 'obsolete';

export type RunStatus = 'pending' | 'running' | 'completed' | 'failed';

export type StepType = 'fetch' | 'store' | 'dedup' | 'reconcile' | 'screen' | 'pico' | 'diff';

export type TriggerType = 'import' | 'criteria_change' | 'pair_decision' | 'revert' | 'workspace_change';

export interface Review {
  id: number;
  title: string;
  question: string;
  population: string;
  intervention: string;
  comparator: string;
  outcome: string;
  active_criteria_version_id?: number | null;
  stats?: ReviewStats;
  created_at: string;
  updated_at: string;
}

export interface Criterion {
  id: number;
  criteria_version_id: number;
  kind: 'include' | 'exclude';
  code: string;
  label: string;
  reason: string;
  detector: 'metadata' | 'rule' | 'metadata_then_rule' | 'manual_only';
  params_json?: Record<string, any>;
  is_active: boolean;
}

export interface CriteriaVersion {
  id: number;
  review_id: number;
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
    [key: string]: any;
  };
  cap?: number;
}

export interface QueryVersion {
  id: number;
  review_id: number;
  lineage_root_id?: number;
  parent_id?: number | null;
  version_no: number;
  label: string;
  source?: SourceType;
  expression?: string;
  date_from?: string;
  date_to?: string;
  options_json?: Record<string, any>;
  import_cap: number;
  status: 'draft' | 'previewed' | 'importing' | 'imported' | 'failed';
  hit_count?: number | null;
  imported_count?: number | null;
  created_at: string;
  executed_at?: string | null;
  request_fingerprint?: string;
}

export interface LiteratureRecord {
  id: number;
  review_id: number;
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
  raw_json?: Record<string, any>;
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
  is_hidden?: boolean;
  is_stale?: boolean;
}

export interface DuplicatePair {
  id: number;
  review_id: number;
  record_a_id: number;
  record_b_id: number;
  method: DedupMethod;
  score: number;
  tier: DedupTier;
  matched_fields_json: string[];
  conflicting_fields_json: string[];
  algo_version: string;
  created_run_id: number;
  record_a?: LiteratureRecord;
  record_b?: LiteratureRecord;
  decision?: PairDecision;
}

export interface PairDecision {
  id: number;
  review_id: number;
  record_a_id: number;
  record_b_id: number;
  decision: PairDecisionType;
  note?: string | null;
  reviewer: string;
  created_at: string;
  superseded_by_id?: number | null;
}

export interface RepresentativePin {
  review_id: number;
  record_id: number;
  pinned_at: string;
  reviewer: string;
}

export interface ScreeningSuggestion {
  id: number;
  record_id: number;
  criteria_version_id: number;
  content_hash: string;
  algo_version: string;
  suggestion: DecisionType;
  criterion_id?: number | null;
  criterion?: Criterion;
  evidence_json: {
    rule_hits?: string[];
    metadata_fields_used?: Record<string, any>;
    strength?: 'strong' | 'weak';
    explanation?: string;
    [key: string]: any;
  };
  created_at: string;
}

export interface ScreeningDecision {
  id: number;
  review_id: number;
  record_id: number;
  decision: DecisionType;
  criterion_id?: number | null;
  criterion?: Criterion;
  reason_text?: string | null;
  note?: string | null;
  reviewer: string;
  origin: DecisionOrigin;
  criteria_version_id: number;
  created_at: string;
  superseded_by_id?: number | null;
}

export interface PicoAnnotation {
  id: number;
  record_id: number;
  label: PicoLabel;
  text: string;
  start_char: number;
  end_char?: number | null;
  origin: 'machine' | 'human';
  status: PicoStatus;
  supersedes_id?: number | null;
  content_hash?: string;
  algo_version?: string;
  reviewer?: string;
  created_at: string;
}

export interface Conflict {
  id: number;
  review_id: number;
  type: ConflictType;
  fingerprint: string;
  record_ids_json: number[];
  details_json: {
    conflicting_decisions?: {
      record_id: number;
      decision: DecisionType;
      reason?: string;
      reviewer: string;
      time: string;
    }[];
    bridging_pairs?: {
      pair_id: number;
      score: number;
      method: string;
      matched_fields: string[];
    }[];
    explanation?: string;
    [key: string]: any;
  };
  status: ConflictStatus;
  created_run_id: number;
  resolved_at?: string | null;
  resolution_json?: Record<string, any> | null;
  reviewer?: string | null;
  records?: LiteratureRecord[];
}

export interface PipelineStep {
  id: number;
  run_id: number;
  step: StepType;
  status: RunStatus;
  started_at?: string | null;
  finished_at?: string | null;
  input_summary_json?: Record<string, any>;
  output_summary_json?: Record<string, any>;
  error?: string | null;
}

export interface PipelineRun {
  id: number;
  review_id: number;
  query_version_id?: number | null;
  trigger: TriggerType;
  active_version_ids_json: number[];
  status: RunStatus;
  started_at: string;
  finished_at?: string | null;
  error?: string | null;
  steps: PipelineStep[];
}

export interface DiffSummary {
  from_version_id: number;
  to_version_id: number;
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
  id: number;
  review_id: number;
  actor: string;
  action: string;
  entity_type: string;
  entity_id: number;
  before_json?: Record<string, any> | null;
  after_json?: Record<string, any> | null;
  run_id?: number | null;
  created_at: string;
}

export interface PreviewResponse {
  query_version_id: number;
  hit_count: number;
  sample_records: any[];
  source?: SourceType;
  expression?: string;
}

export interface ResolveConflictRequest {
  action: 'apply_decision' | 'split_duplicates' | 'keep_maybe';
  decision?: DecisionType;
  criterion_id?: number;
  reason_text?: string | null;
  note?: string | null;
  reviewer: string;
}

export interface ScreeningSubmission {
  record_id: number;
  decision: DecisionType;
  criterion_id?: number | null;
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
