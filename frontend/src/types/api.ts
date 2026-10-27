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
