from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field

# ━━━ Enums ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class SupportedProduct(StrEnum):
    STRIPE = "stripe"
    TWILIO = "twilio"
    SENDGRID = "sendgrid"


class UserRole(StrEnum):
    FRONTEND_DEVELOPER = "frontend_developer"
    BACKEND_DEVELOPER = "backend_developer"
    SECURITY_ENGINEER = "security_engineer"
    DEVOPS_ENGINEER = "devops_engineer"
    PRODUCT_MANAGER = "product_manager"
    TEAM_LEAD = "team_lead"


class ExperienceLevel(StrEnum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class GuideStatus(StrEnum):
    PENDING = "pending"
    GENERATING = "generating"
    EVALUATING = "evaluating"
    REGENERATING = "regenerating"
    COMPLETE = "complete"
    FAILED = "failed"


# ━━━ Request Models ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class GuideRequest(BaseModel):
    product: SupportedProduct
    role: UserRole
    experience_level: ExperienceLevel = ExperienceLevel.INTERMEDIATE
    focus_areas: list[str] = Field(
        default=[],
        max_length=5,
        description="Specific topics: 'webhooks', 'authentication', etc.",
    )
    tech_stack: list[str] = Field(
        default=[],
        description="User's tech stack for tailored code examples",
    )


# ━━━ Role Profile (Role Profiler Agent Output) ━━━━━━━━━━━━━━━━━━━


class RoleProfile(BaseModel):
    role: UserRole
    experience_level: ExperienceLevel
    primary_concerns: list[str] = Field(
        description="Top 5 concerns for this role when onboarding to this product",
    )
    relevant_doc_topics: list[str] = Field(
        description="8-12 documentation topic areas to prioritize in retrieval",
    )
    excluded_topics: list[str] = Field(
        description="Topics irrelevant to this role, to filter out",
    )
    learning_objectives: list[str] = Field(
        description="4-6 concrete skills. Each starts with action verb.",
    )
    complexity_ceiling: str = Field(
        description="'conceptual' | 'hands-on' | 'deep-dive'",
    )


# ━━━ Guide Section (Generator Agent Output) ━━━━━━━━━━━━━━━━━━━━━━


class CodeExample(BaseModel):
    language: str
    code: str
    description: str


class Citation(BaseModel):
    source_url: str
    source_title: str
    chunk_id: str
    relevance_score: float


class GuideSection(BaseModel):
    section_number: int
    title: str
    summary: str = Field(description="2-3 sentence overview of this section")
    content: str = Field(description="Full markdown content with steps and explanations")
    key_takeaways: list[str] = Field(max_length=5)
    code_examples: list[CodeExample] = Field(default=[])
    warnings: list[str] = Field(
        default=[],
        description="Common pitfalls and gotchas for this section",
    )
    citations: list[Citation] = Field(default=[])
    estimated_time_minutes: int = Field(ge=1, le=120)
    prerequisites: list[str] = Field(default=[])


# ━━━ Evaluation (Quality Evaluator Agent Output) ━━━━━━━━━━━━━━━━━


class DimensionScore(BaseModel):
    dimension: str  # completeness|role_relevance|actionability|clarity|progressive_complexity
    score: float = Field(ge=0.0, le=1.0)
    reasoning: str
    suggestions: list[str] = Field(default=[])


class SectionEvaluation(BaseModel):
    section_number: int
    overall_score: float = Field(ge=0.0, le=1.0)
    dimensions: list[DimensionScore]
    pass_threshold: bool
    needs_regeneration: bool


class GenerationMetadata(BaseModel):
    model: str
    total_tokens_used: int
    total_cost_usd: float
    generation_time_seconds: float
    retrieval_latency_ms: float
    chunks_retrieved: int
    chunks_after_reranking: int
    regeneration_count: int
    langsmith_trace_url: str | None = None


class GuideEvaluation(BaseModel):
    guide_id: str
    overall_score: float = Field(ge=0.0, le=1.0)
    section_evaluations: list[SectionEvaluation]
    generation_metadata: GenerationMetadata


# ━━━ Full Guide Response ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class GuideResponse(BaseModel):
    id: str
    product: SupportedProduct
    role: UserRole
    title: str
    description: str
    sections: list[GuideSection]
    evaluation: GuideEvaluation
    metadata: GenerationMetadata
    created_at: datetime


class GuideSummary(BaseModel):
    """Lightweight guide listing (for index endpoints)."""

    id: str
    product: SupportedProduct
    role: UserRole
    title: str
    overall_score: float
    sections_count: int
    created_at: datetime


# ━━━ SSE Event Types ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class SSEAgentStart(BaseModel):
    type: str = "agent_start"
    agent: str
    message: str


class SSEAgentComplete(BaseModel):
    type: str = "agent_complete"
    agent: str
    duration_ms: float


class SSESectionGenerated(BaseModel):
    type: str = "section_generated"
    section: GuideSection
    index: int


class SSESectionEvaluated(BaseModel):
    type: str = "section_evaluated"
    evaluation: SectionEvaluation
    index: int


class SSERegenerationTriggered(BaseModel):
    type: str = "regeneration_triggered"
    sections: list[int]
    attempt: int


class SSEGuideComplete(BaseModel):
    type: str = "guide_complete"
    guide: GuideResponse


class SSEError(BaseModel):
    type: str = "error"
    message: str
    recoverable: bool


# ━━━ Product/Config Responses ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class ProductInfo(BaseModel):
    id: str
    name: str
    description: str
    doc_count: int
    chunk_count: int
    available_roles: list[UserRole]


class ProductListResponse(BaseModel):
    products: list[ProductInfo]
