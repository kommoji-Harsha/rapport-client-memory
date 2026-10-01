export interface Client {
  id: string;
  name: string;
  contact_name: string;
  contact_email: string;
  industry: string;
  primary_quirk: string;
}

export interface BriefItem {
  text: string;
  source_interaction_ids: string[];
  source_memory_ids: string[];
}

export interface RiskFlag {
  type: string;
  text: string;
  sources: string[];
}

export interface RecalledMemory {
  id: string;
  text: string;
  type: string;
  context?: string | null;
  metadata: Record<string, unknown>;
  tags: string[];
  entities: unknown[];
  occurred_start?: string | null;
  mentioned_at?: string | null;
  document_id?: string | null;
  chunk_id?: string | null;
  source_fact_ids: string[];
  scores: Record<string, number | null>;
  source_interaction_id?: string | null;
}

export interface AgentResponse {
  response_id?: string | null;
  client_id: string;
  incoming_text: string;
  memory_enabled: boolean;
  draft_reply: string;
  client_brief: BriefItem[];
  risk_flags: RiskFlag[];
  memory_used: RecalledMemory[];
  warnings: string[];
  model_used: string;
}

export interface CompareResponse {
  memory_on: AgentResponse;
  memory_off: AgentResponse;
}

export interface ObservationItem {
  id: string;
  text: string;
  context?: string | null;
  client_id?: string | null;
  metadata: Record<string, unknown>;
}

export interface HealthResponse {
  status: string;
  version: string;
  memory_backend: string;
}

export interface FeedbackRequest {
  response_id: string;
  outcome: "went_well" | "pushback";
  notes?: string | null;
}

export interface ImportRequest {
  client_id: string;
  text: string;
}

export interface ImportResponse {
  status: string;
  client_id: string;
  import_id: string;
  recalled_extracted: RecalledMemory[];
}

export interface LearningCurveMetric {
  interaction_point: 1 | 5 | 20;
  memory_on_score: number;
  memory_off_score: number;
  citation_accuracy: number;
  notes: string;
}

export interface LearningCurveEval {
  client_id: string;
  metrics: LearningCurveMetric[];
  status: "not_available" | "in_progress" | "complete";
}
