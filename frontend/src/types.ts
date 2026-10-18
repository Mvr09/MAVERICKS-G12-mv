export interface Assessment {
  supplier_id: string;
  p_link: number;
  p_candidate?: number;
  association_status?: "confirmed" | "review" | "excluded";
  geography_version?: string;
  p_identity?: number;
  p_exposure?: number;
  p_risk: number;
  p_urgent: number;
  is_risk: string;
  urgent: string;
  severity: number | null;
  severity_confidence?: number | null;
  duration_days?: number | null;
  duration_is_lower_bound?: boolean;
  policy_version: string;
  priority: number | null;
  priority_band: "low" | "medium" | "high" | "critical" | null;
  needs_review: boolean;
  review_reasons: string[];
  factor_values: Record<string, number>;
  evidence_ids: string[];
  impact_status: string;
  review_policy_version?: string;
  priority_requires_review?: boolean;
  localized_warnings?: string[];
  human_attention?: string;
}
export interface Analysis {
  review_details?: {
    code: string;
    field: string;
    supplier_id: string | null;
    relevance: string;
    requires_review: boolean;
    value: string | number | null;
    threshold: number | null;
    resolution?: string | null;
  }[];
  event_classification?: {
    category: string;
    confidence: number;
    taxonomy_version: string;
    label_es?: string;
  };
  context_notes?: string[];
  source_reading?: {
    status: string;
    checked_at?: string;
    source_url?: string;
    reason?: string;
  };
  error?: string | null;
  article_id: string;
  news_id: string;
  context_id: string;
  question_version: string;
  policy_version: string;
  analysis_status: "done" | "review" | "error";
  is_risk: string;
  urgent: string;
  affected_supplier_ids: string[];
  assessments: Assessment[];
  evidence: {
    id: string;
    text: string;
    field: "headline" | "summary" | "full_text";
    start: number;
    end: number;
  }[];
  event_type: string | null;
  model_id: string | null;
  review_reasons: string[];
}
export type EventInfo = Partial<
  Pick<
    Analysis,
    | "event_type"
    | "event_classification"
    | "context_notes"
    | "review_reasons"
    | "analysis_status"
  >
>;
export interface Article {
  origin?: string;
  origin_label?: string;
  event_type_confidence?: number;
  enrichment?: { status: string; checked_at?: string; reason?: string };
  generation?: number;
  split?: string;
  id: string;
  headline: string;
  summary: string;
  source: string;
  published_date: string;
  fetched_at: string;
  url?: string;
  state: string;
  analysis: Analysis | null;
  cached: boolean;
  cache_stages?: string[];
  new_requests?: number;
  version: number;
  news_id: string;
}
export interface Incident {
  event_tag?: EventInfo;
  current_headline?: string;
  id: string;
  state: string;
  priority: number;
  historical_priority: number;
  event_type: string;
  event_date: string;
  stale: boolean;
  history: {
    article_id?: string;
    assessment?: Assessment;
    headline?: string;
    explanation?: string;
    at?: string;
    reason?: string;
  }[];
}
export interface Material {
  material_id: string;
  name: string;
  category: string;
  primary_id: string;
  alternate_id: string | null;
  products: string[];
  monthly_requirement: number;
  unit: string;
  primary?: Supplier | null;
  alternate?: Supplier | null;
}
export interface Supplier {
  geography?: {
    version: string;
    status: string;
    places: {
      name: string;
      admin1?: { name: string } | null;
      source_url: string;
    }[];
  };
  materials: Material[];
  supplier_id: string;
  name: string;
  country: string;
  city: string;
  category: string;
  material: string;
  criticality: string;
  single_source: string;
  alternate_id: string | null;
  lead_days: number | null;
  inventory_days: number | null;
  share_category_pct: number;
  annual_spend: number;
  quality_score: number;
  products: string[];
  priority: number | null;
  urgent: boolean;
  needs_review: boolean;
  incidents: Incident[];
  incident_count: number;
  latest_evidence: string | null;
  reason: string;
  status: string;
  alternate?: Supplier | null;
  articles?: Article[];
}
export interface Source {
  job_state?: string | null;
  id: string;
  name: string;
  status: string;
  last_attempt_at: string | null;
  last_success_at: string | null;
  http_status: number | null;
  item_count: number;
  received_count: number;
  duplicates: number;
  error: string | null;
}
export interface Batch {
  filename?: string;
  origin_label?: string;
  queued?: number;
  running?: number;
  job_errors?: number;
  id: string;
  split: string;
  count: number;
  done: number;
  errors: number;
  pending: number;
  logical_date: string;
  elapsed_seconds: number | null;
}
export interface Alert {
  urgent?: string;
  event_tag?: EventInfo;
  id: number;
  incident_id: string;
  revision: number;
  acknowledged: boolean;
  supplier_id: string;
  supplier_name: string;
  priority: number;
  headline: string;
  needs_review: boolean;
  sound_eligible: boolean;
  created_at: string;
  state: string;
}
