from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, Index, Integer, String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Guide(Base):
    __tablename__ = "guides"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    product: Mapped[str] = mapped_column(String, nullable=False)
    role: Mapped[str] = mapped_column(String, nullable=False)
    experience_level: Mapped[str] = mapped_column(String, nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=False)
    sections: Mapped[dict] = mapped_column(JSON, nullable=True)
    evaluation: Mapped[dict] = mapped_column(JSON, nullable=True)
    generation_metadata: Mapped[dict] = mapped_column("generation_metadata", JSON, nullable=True)
    focus_areas: Mapped[dict] = mapped_column(JSON, nullable=True)
    tech_stack: Mapped[dict] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String, default="pending", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("ix_guides_product_role", "product", "role"),
    )


class EvaluationRun(Base):
    __tablename__ = "evaluation_runs"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    guide_id: Mapped[str] = mapped_column(String, index=True, nullable=False)
    run_type: Mapped[str] = mapped_column(String, nullable=False)
    overall_score: Mapped[float] = mapped_column(Float, nullable=True)
    dimension_scores: Mapped[dict] = mapped_column(JSON, nullable=True)
    section_scores: Mapped[dict] = mapped_column(JSON, nullable=True)
    ragas_metrics: Mapped[dict] = mapped_column(JSON, nullable=True)
    tokens_used: Mapped[int] = mapped_column(Integer, nullable=True)
    cost_usd: Mapped[float] = mapped_column(Float, nullable=True)
    latency_seconds: Mapped[float] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
