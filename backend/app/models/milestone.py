import uuid
from datetime import date
from typing import Optional, List
from sqlalchemy import String, Date, Float, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base, TimestampMixin


class Milestone(Base, TimestampMixin):
    """Project Milestone with weighted progress calculation."""
    __tablename__ = "milestones"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    org_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="pending")  # pending, in_progress, completed
    weight: Mapped[float] = mapped_column(Float, default=1.0)
    progress_pct: Mapped[float] = mapped_column(Float, default=0.0)

    # Relationships
    project = relationship("Project", back_populates="milestones")
    tasks = relationship("Task", back_populates="milestone")

    __table_args__ = (
        Index("ix_milestones_proj_status", "project_id", "status"),
    )

