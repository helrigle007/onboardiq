"""Tests for Pydantic schema validation and constraints."""

import pytest
from pydantic import ValidationError

from app.models.schemas import (
    DimensionScore,
    ExperienceLevel,
    GenerationMetadata,
    GuideRequest,
    GuideSection,
    GuideStatus,
    ProductInfo,
    RoleProfile,
    SSEAgentComplete,
    SSEAgentStart,
    SSEError,
    SSERegenerationTriggered,
    SupportedProduct,
    UserRole,
)


class TestEnums:
    def test_supported_product_values(self):
        assert SupportedProduct.STRIPE == "stripe"
        assert SupportedProduct.TWILIO == "twilio"
        assert SupportedProduct.SENDGRID == "sendgrid"

    def test_user_role_values(self):
        assert len(UserRole) == 6
        assert UserRole.SECURITY_ENGINEER == "security_engineer"

    def test_experience_level_values(self):
        assert ExperienceLevel.BEGINNER == "beginner"
        assert ExperienceLevel.INTERMEDIATE == "intermediate"
        assert ExperienceLevel.ADVANCED == "advanced"

    def test_guide_status_values(self):
        assert len(GuideStatus) == 6
        assert GuideStatus.PENDING == "pending"
        assert GuideStatus.FAILED == "failed"


class TestGuideRequest:
    def test_valid_request(self):
        req = GuideRequest(product="stripe", role="backend_developer")
        assert req.experience_level == ExperienceLevel.INTERMEDIATE

    def test_default_focus_areas_empty(self):
        req = GuideRequest(product="stripe", role="backend_developer")
        assert req.focus_areas == []

    def test_default_tech_stack_empty(self):
        req = GuideRequest(product="stripe", role="backend_developer")
        assert req.tech_stack == []

    def test_invalid_product_rejected(self):
        with pytest.raises(ValidationError):
            GuideRequest(product="invalid", role="backend_developer")

    def test_invalid_role_rejected(self):
        with pytest.raises(ValidationError):
            GuideRequest(product="stripe", role="invalid_role")

    def test_focus_areas_max_length(self):
        with pytest.raises(ValidationError):
            GuideRequest(
                product="stripe",
                role="backend_developer",
                focus_areas=["a", "b", "c", "d", "e", "f"],
            )

    def test_focus_areas_within_limit(self):
        req = GuideRequest(
            product="stripe",
            role="backend_developer",
            focus_areas=["a", "b", "c", "d", "e"],
        )
        assert len(req.focus_areas) == 5


class TestGuideSection:
    def test_valid_section(self):
        section = GuideSection(
            section_number=1,
            title="Getting Started",
            summary="Overview of setup.",
            content="# Getting Started\n\nContent here.",
            key_takeaways=["Install SDK", "Get API key"],
            estimated_time_minutes=10,
        )
        assert section.section_number == 1

    def test_estimated_time_min_boundary(self):
        with pytest.raises(ValidationError):
            GuideSection(
                section_number=1,
                title="T",
                summary="S",
                content="C",
                key_takeaways=["T"],
                estimated_time_minutes=0,
            )

    def test_estimated_time_max_boundary(self):
        with pytest.raises(ValidationError):
            GuideSection(
                section_number=1,
                title="T",
                summary="S",
                content="C",
                key_takeaways=["T"],
                estimated_time_minutes=121,
            )

    def test_key_takeaways_max_length(self):
        with pytest.raises(ValidationError):
            GuideSection(
                section_number=1,
                title="T",
                summary="S",
                content="C",
                key_takeaways=["a", "b", "c", "d", "e", "f"],
                estimated_time_minutes=10,
            )


class TestDimensionScore:
    def test_valid_score(self):
        ds = DimensionScore(
            dimension="completeness",
            score=0.85,
            reasoning="Good coverage",
        )
        assert ds.score == 0.85

    def test_score_below_zero_rejected(self):
        with pytest.raises(ValidationError):
            DimensionScore(dimension="test", score=-0.1, reasoning="Bad")

    def test_score_above_one_rejected(self):
        with pytest.raises(ValidationError):
            DimensionScore(dimension="test", score=1.1, reasoning="Bad")

    def test_score_boundaries(self):
        DimensionScore(dimension="test", score=0.0, reasoning="Min")
        DimensionScore(dimension="test", score=1.0, reasoning="Max")


class TestGenerationMetadata:
    def test_optional_langsmith_url(self):
        meta = GenerationMetadata(
            model="test",
            total_tokens_used=100,
            total_cost_usd=0.01,
            generation_time_seconds=1.0,
            retrieval_latency_ms=50.0,
            chunks_retrieved=10,
            chunks_after_reranking=5,
            regeneration_count=0,
        )
        assert meta.langsmith_trace_url is None

    def test_with_langsmith_url(self):
        meta = GenerationMetadata(
            model="test",
            total_tokens_used=100,
            total_cost_usd=0.01,
            generation_time_seconds=1.0,
            retrieval_latency_ms=50.0,
            chunks_retrieved=10,
            chunks_after_reranking=5,
            regeneration_count=0,
            langsmith_trace_url="https://smith.langchain.com/trace/123",
        )
        assert meta.langsmith_trace_url is not None


class TestRoleProfile:
    def test_valid_profile(self):
        profile = RoleProfile(
            role=UserRole.SECURITY_ENGINEER,
            experience_level=ExperienceLevel.INTERMEDIATE,
            primary_concerns=["API key security", "PCI compliance"],
            relevant_doc_topics=["authentication", "webhooks", "security"],
            excluded_topics=["UI design"],
            learning_objectives=["Implement secure authentication"],
            complexity_ceiling="deep-dive",
        )
        assert profile.role == UserRole.SECURITY_ENGINEER


class TestSSEModels:
    def test_sse_agent_start_default_type(self):
        ev = SSEAgentStart(agent="role_profiler", message="Starting...")
        assert ev.type == "agent_start"

    def test_sse_agent_complete_default_type(self):
        ev = SSEAgentComplete(agent="role_profiler", duration_ms=1500.0)
        assert ev.type == "agent_complete"

    def test_sse_error_model(self):
        ev = SSEError(message="Something failed", recoverable=True)
        assert ev.type == "error"
        assert ev.recoverable is True

    def test_sse_regeneration_triggered(self):
        ev = SSERegenerationTriggered(sections=[1, 3], attempt=1)
        assert ev.type == "regeneration_triggered"
        assert ev.sections == [1, 3]


class TestProductInfo:
    def test_product_with_all_roles(self):
        info = ProductInfo(
            id="stripe",
            name="Stripe",
            description="Payment processing",
            doc_count=6,
            chunk_count=100,
            available_roles=list(UserRole),
        )
        assert len(info.available_roles) == 6
