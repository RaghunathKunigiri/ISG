import uuid
from datetime import date, datetime
from typing import Optional, List, Any
from sqlalchemy import String, Date, DateTime, Float, Integer, ForeignKey, Text, JSON, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base, TimestampMixin


class Task(Base, TimestampMixin):
    """Task model supporting subtasks, estimation, and status lifecycle."""
    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    org_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    milestone_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("milestones.id", ondelete="SET NULL"), nullable=True, index=True)
    parent_task_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=True, index=True)

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    assignee_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("employees.id", ondelete="SET NULL"), nullable=True, index=True)
    reporter_id: Mapped[str] = mapped_column(String(36), ForeignKey("employees.id"), nullable=False, index=True)

    # Status: backlog, todo, in_progress, blocked, in_review, done
    status: Mapped[str] = mapped_column(String(50), default="todo")
    # Priority: low, medium, high, urgent
    priority: Mapped[str] = mapped_column(String(50), default="medium")

    story_points: Mapped[int] = mapped_column(Integer, default=1)
    estimated_hours: Mapped[float] = mapped_column(Float, default=0.0)
    actual_hours: Mapped[float] = mapped_column(Float, default=0.0)
    progress_pct: Mapped[float] = mapped_column(Float, default=0.0)

    start_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    due_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    blocked_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    blocked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    tags: Mapped[List[str]] = mapped_column(JSON, default=list)

    # Relationships
    project = relationship("Project", back_populates="tasks")
    milestone = relationship("Milestone", back_populates="tasks")
    parent_task = relationship("Task", remote_side=[id], back_populates="subtasks")
    subtasks = relationship("Task", back_populates="parent_task", cascade="all, delete-orphan")
    assignee = relationship("Employee", foreign_keys=[assignee_id], back_populates="assigned_tasks")
    reporter = relationship("Employee", foreign_keys=[reporter_id], back_populates="reported_tasks")
    updates = relationship("TaskUpdate", back_populates="task", cascade="all, delete-orphan", order_by="desc(TaskUpdate.created_at)")
    timesheets = relationship("Timesheet", back_populates="task")

    __table_args__ = (
        Index("ix_tasks_org_status", "org_id", "status"),
        Index("ix_tasks_assignee_status", "assignee_id", "status"),
        Index("ix_tasks_proj_status", "project_id", "status"),
    )

