import uuid
from datetime import date, datetime
from sqlalchemy import String, Date, DateTime, Float, Integer, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base, utc_now


class ProjectProgressSnapshot(Base):
    """Daily snapshot of project progress, SPI, and burndown data."""
    __tablename__ = "project_progress_snapshots"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    org_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)

    snapshot_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    progress_pct: Mapped[float] = mapped_column(Float, nullable=False)
    spi: Mapped[float] = mapped_column(Float, nullable=False)
    effort_variance: Mapped[float] = mapped_column(Float, nullable=False)
    actual_hours: Mapped[float] = mapped_column(Float, nullable=False)
    estimated_hours: Mapped[float] = mapped_column(Float, nullable=False)
    remaining_story_points: Mapped[int] = mapped_column(Integer, nullable=False)
    health: Mapped[str] = mapped_column(String(20), nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Relationships
    project = relationship("Project", back_populates="snapshots")

    __table_args__ = (
        Index("ix_snapshots_proj_date", "project_id", "snapshot_date", unique=True),
    )

