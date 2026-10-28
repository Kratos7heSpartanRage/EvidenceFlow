/** Wire-format API types. UI view models live in api.ts; keep the namespaces distinct. */
export type LiteratureSource = "europe_pmc" | "pubmed";

export interface Author {
  full_name: string;
  last_name?: string | null;
  initials?: string | null;
}

export interface RecordIn {
  source: LiteratureSource;
  source_record_id: string;
  title: string;
  abstract?: string | null;
  doi?: string | null;
  pmid?: string | null;
  pmcid?: string | null;
  authors: Author[];
  year?: number | null;
  publication_date?: string | null;
  journal?: string | null;
  volume?: string | null;
  issue?: string | null;
  pages?: string | null;
  language?: string | null;
  pub_types: string[];
  mesh_terms: string[];
  keywords: string[];
  raw: Record<string, unknown>;
}

export interface QueryPreview {
  query_id: string;
  estimated_hits: number;
  sample_records: RecordIn[];
  is_frozen: boolean;
  warnings: string[];
}

export type PairDecisionTarget =
  | { duplicate_pair_id: string; record_a_id?: never; record_b_id?: never }
  | { duplicate_pair_id?: never; record_a_id: string; record_b_id: string };

export type PairDecisionInput = PairDecisionTarget & {
  decision: "confirm" | "reject";
  reviewer_name?: string;
  note?: string | null;
};

export interface RecordSummary {
  id: string;
  review_id: string;
  source: string;
  source_record_id: string;
  title: string;
  authors: string[];
  journal?: string | null;
  publication_year?: number | null;
  doi?: string | null;
  pmid?: string | null;
}

export interface PairDecisionResult {
  status: "recorded";
  decision_id: string;
  duplicate_pair_id: string;
  affected_group_id: string | null;
}

export type ScreeningDecisionType = "include" | "exclude" | "maybe" | "unscreened";

export interface ScreeningDecisionInput {
  decision: "include" | "exclude" | "maybe";
  criterion_id?: string | null;
  reason_text?: string | null;
  reviewer_name: string;
  note?: string | null;
}

export interface ScreeningDecision {
  id: string;
  record_id: string;
  group_id?: string | null;
  decision: "include" | "exclude" | "maybe";
  criterion_id?: string | null;
  reason_text?: string | null;
  reviewer_name: string;
  origin: "human" | "inherited" | "conflict_resolution";
  note?: string | null;
  superseded_by_id?: string | null;
  created_at: string;
}

export interface PicoSpan {
  id: string;
  element: "P" | "I" | "C" | "O";
  text: string;
  start_index?: number | null;
  end_index?: number | null;
  confidence?: number | null;
  origin: "machine" | "human";
  is_confirmed: boolean;
  status?: string | null;
  supersedes_id?: string | null;
  reviewer?: string | null;
}

export interface PicoOp {
  op: "confirm" | "correct" | "reject";
  span_id: string;
  text?: string | null;
  start_index?: number | null;
  end_index?: number | null;
}

export interface PicoPatchInput {
  ops: PicoOp[];
}

export interface PicoPatchResult {
  status: "updated";
  updated_count: number;
}

export interface Conflict {
  id: string;
  review_id: string;
  group_id: string;
  reason: string;
  status: "open" | "resolved";
  open_fingerprint?: string | null;
  created_at: string;
  resolved_at?: string | null;
  resolved_by?: string | null;
  resolution_note?: string | null;
}

export interface ConflictResolveInput {
  decision: "include" | "exclude" | "maybe";
  reviewer: string;
  note?: string | null;
  criterion_id?: string | null;
  reason_text?: string | null;
}

export interface ConflictResolveResult {
  status: "resolved";
  conflict_id: string;
  affected_records_count: number;
}

export interface QueryRevertResult {
  status: "reverted";
  restored_version_id: string;
  restored_records_count?: number | null;
  hidden_records_count?: number | null;
}

export interface RecordItem {
  id: string;
  review_id: string;
  source: string;
  source_record_id: string;
  title: string;
  authors: Array<string | Author>;
  journal?: string | null;
  publication_year?: number | null;
  doi?: string | null;
  pmid?: string | null;
  group_id?: string | null;
  is_representative: boolean;
  is_hidden: boolean;
  decision?: ScreeningDecision | null;
}

export interface RecordDetail extends RecordItem {
  abstract?: string | null;
  mesh_headings: string[];
  publication_types: string[];
  language?: string | null;
  decisions: ScreeningDecision[];
  pico_spans: PicoSpan[];
  pico_history?: PicoSpan[];
  cluster_members: RecordItem[];
}

export interface AuditEvent {
  id: string;
  review_id: string;
  actor: string;
  event_type: string;
  target_type: string;
  target_id: string;
  timestamp: string;
  before_state?: Record<string, unknown> | null;
  after_state?: Record<string, unknown> | null;
  note?: string | null;
}
