"""LLM-as-judge evaluation using Claude with structured output."""

from __future__ import annotations

import logging
from pathlib import Path
from statistics import mean

from langchain_anthropic import ChatAnthropic
from pydantic import BaseModel, Field

from app.agents.state import calculate_cost
from app.config import get_settings
from app.models.schemas import (
    DimensionScore,
    GuideSection,
    RoleProfile,
    SectionEvaluation,
)

logger = logging.getLogger(__name__)

_PROMPT_PATH = Path(__file__).resolve().parents[1] / "agents" / "prompts" / "quality_evaluator.xml"


class DimensionJudgment(BaseModel):
    """Single dimension judgment from the LLM judge."""

    score: float = Field(ge=0.0, le=1.0)
    reasoning: str
    suggestions: list[str] = Field(default=[])


class SectionJudgment(BaseModel):
    """Structured output for the 5-dimension evaluation."""

    completeness: DimensionJudgment
    role_relevance: DimensionJudgment
    actionability: DimensionJudgment
    clarity: DimensionJudgment
    progressive_complexity: DimensionJudgment


class LLMJudge:
    """Evaluates guide sections using Claude as a structured judge."""

    def __init__(self) -> None:
        settings = get_settings()
        self._model_name = settings.evaluation_model
        self._threshold = settings.eval_threshold
        self._llm = ChatAnthropic(
            model=self._model_name,
            api_key=settings.anthropic_api_key,
            max_tokens=2000,
            temperature=0.0,
        )
        self._prompt_template = _PROMPT_PATH.read_text(encoding="utf-8")

    async def evaluate_section(
        self,
        section: GuideSection,
        role_profile: RoleProfile,
        all_sections: list[GuideSection],
    ) -> tuple[SectionEvaluation, int, float]:
        """Evaluate a single section. Returns (evaluation, tokens, cost_usd)."""
        prompt = self._format_prompt(section, role_profile, all_sections)

        llm_with_output = self._llm.with_structured_output(
            SectionJudgment, include_raw=True
        )
        result = await llm_with_output.ainvoke(prompt)

        judgment: SectionJudgment = result["parsed"]
        raw = result["raw"]

        # Extract token usage
        input_tokens = raw.usage_metadata.get("input_tokens", 0)
        output_tokens = raw.usage_metadata.get("output_tokens", 0)
        tokens, cost = calculate_cost(input_tokens, output_tokens, self._model_name)

        # Build dimension scores
        dimensions = []
        dim_names = [
            "completeness", "role_relevance", "actionability",
            "clarity", "progressive_complexity",
        ]
        for dim_name in dim_names:
            dj: DimensionJudgment = getattr(judgment, dim_name)
            dimensions.append(
                DimensionScore(
                    dimension=dim_name,
                    score=dj.score,
                    reasoning=dj.reasoning,
                    suggestions=dj.suggestions,
                )
            )

        overall = mean(d.score for d in dimensions)
        passes = overall >= self._threshold

        evaluation = SectionEvaluation(
            section_number=section.section_number,
            overall_score=round(overall, 4),
            dimensions=dimensions,
            pass_threshold=passes,
            needs_regeneration=not passes,
        )

        logger.info(
            "Section %d evaluated: %.3f (%s)",
            section.section_number,
            overall,
            "PASS" if passes else "FAIL",
        )
        return evaluation, tokens, cost

    def _format_prompt(
        self,
        section: GuideSection,
        role_profile: RoleProfile,
        all_sections: list[GuideSection],
    ) -> str:
        """Format the quality evaluator prompt template."""
        code_examples_str = "\n".join(
            f"- {ex.language}: {ex.description}" for ex in section.code_examples
        ) or "None"

        all_sections_summary = "\n".join(
            f"Section {s.section_number}: {s.title} — {s.summary}"
            for s in all_sections
        ) or "This is the only section so far."

        return self._prompt_template.format(
            role=role_profile.role.value,
            experience_level=role_profile.experience_level.value,
            primary_concerns=", ".join(role_profile.primary_concerns),
            learning_objectives=", ".join(role_profile.learning_objectives),
            section_number=section.section_number,
            title=section.title,
            summary=section.summary,
            content=section.content,
            code_examples=code_examples_str,
            key_takeaways=", ".join(section.key_takeaways),
            all_sections_summary=all_sections_summary,
        )
