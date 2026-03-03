// Enums
export type SupportedProduct = 'stripe' | 'twilio' | 'sendgrid';
export type UserRole =
  | 'frontend_developer'
  | 'backend_developer'
  | 'security_engineer'
  | 'devops_engineer'
  | 'product_manager'
  | 'team_lead';
export type ExperienceLevel = 'beginner' | 'intermediate' | 'advanced';
export type GuideStatus = 'pending' | 'generating' | 'evaluating' | 'regenerating' | 'complete' | 'failed';

// Request
export interface GuideRequest {
  product: SupportedProduct;
  role: UserRole;
  experience_level: ExperienceLevel;
  focus_areas: string[];
  tech_stack: string[];
}

// Guide structures
export interface CodeExample {
  language: string;
  code: string;
  description: string;
}

export interface Citation {
  source_url: string;
  source_title: string;
  chunk_id: string;
  relevance_score: number;
}

export interface GuideSection {
  section_number: number;
  title: string;
  summary: string;
  content: string;
  key_takeaways: string[];
  code_examples: CodeExample[];
  warnings: string[];
  citations: Citation[];
  estimated_time_minutes: number;
  prerequisites: string[];
}

// Evaluation
export interface DimensionScore {
  dimension: string;
  score: number;
  reasoning: string;
  suggestions: string[];
}

export interface SectionEvaluation {
  section_number: number;
  overall_score: number;
  dimensions: DimensionScore[];
  pass_threshold: boolean;
  needs_regeneration: boolean;
}

export interface GenerationMetadata {
  model: string;
  total_tokens_used: number;
  total_cost_usd: number;
  generation_time_seconds: number;
  retrieval_latency_ms: number;
  chunks_retrieved: number;
  chunks_after_reranking: number;
  regeneration_count: number;
  langsmith_trace_url: string | null;
}

export interface GuideEvaluation {
  guide_id: string;
  overall_score: number;
  section_evaluations: SectionEvaluation[];
  generation_metadata: GenerationMetadata;
}

export interface GuideResponse {
  id: string;
  product: SupportedProduct;
  role: UserRole;
  title: string;
  description: string;
  sections: GuideSection[];
  evaluation: GuideEvaluation;
  metadata: GenerationMetadata;
  created_at: string;
}

// SSE Events
export type SSEEvent =
  | { type: 'agent_start'; agent: string; message: string }
  | { type: 'agent_complete'; agent: string; duration_ms: number }
  | { type: 'section_generated'; section: GuideSection; index: number }
  | { type: 'section_evaluated'; evaluation: SectionEvaluation; index: number }
  | { type: 'regeneration_triggered'; sections: number[]; attempt: number }
  | { type: 'guide_complete'; guide: GuideResponse }
  | { type: 'error'; message: string; recoverable: boolean }
  | { type: 'keepalive' };

// Product info
export interface ProductInfo {
  id: string;
  name: string;
  description: string;
  doc_count: number;
  chunk_count: number;
  available_roles: UserRole[];
}

// Role display info (for UI)
export interface RoleDisplayInfo {
  role: UserRole;
  label: string;
  icon: string;
  description: string;
}
