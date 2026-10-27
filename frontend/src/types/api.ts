/** Shared boundary types for the merged backend. Replace with generated OpenAPI types as endpoints mature. */
export type LiteratureSource = "europe_pmc" | "pubmed";

export interface QuerySpec {
  source: LiteratureSource;
  expression: string;
  date_from?: string | null;
  date_to?: string | null;
  expand_synonyms?: boolean;
  /** Legacy input alias; use expand_synonyms for new callers. */
  synonyms?: boolean;
  title_abstract_only?: boolean;
  /** Compatibility field; currently not applied as a source search filter. */
  language?: string | null;
}

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

export interface ApiError {
  error: { code: string; message: string; details: Record<string, unknown> };
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

export interface PairDecision {
  id: string;
  duplicate_pair_id: string;
  decision: "confirm" | "reject";
  reviewer_name: string;
  note?: string | null;
  created_at: string;
}

export interface DuplicatePair {
  id: string;
  review_id: string;
  record_a_id: string;
  record_b_id: string;
  record_a: RecordSummary | null;
  record_b: RecordSummary | null;
  similarity_score: number;
  tier: string;
  match_reasons: string[];
  status: string;
  created_at: string;
  decisions: PairDecision[];
}

export interface PairDecisionResult {
  status: "recorded";
  decision_id: string;
  duplicate_pair_id: string;
  affected_group_id: string | null;
}
