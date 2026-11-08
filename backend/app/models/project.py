import uuid
from datetime import date
from typing import Optional, List
from sqlalchemy import String, Date, Float, ForeignKey, Text, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base, TimestampMixin


class Project(Base, TimestampMixin):
    """Project entity belonging to an organization."""
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    org_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    client: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    owner_id: Mapped[str] = mapped_column(String(36), ForeignKey("employees.id"), nullable=False, index=True)

    status: Mapped[str] = mapped_column(String(50), default="planned")  # planned, active, on_hold, completed, cancelled
    priority: Mapped[str] = mapped_column(String(50), default="medium")  # low, medium, high, critical
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    target_end_date: Mapped[date] = mapped_column(Date, nullable=False)
    actual_end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    budget_hours: Mapped[float] = mapped_column(Float, default=0.0)
    budget_cost: Mapped[float] = mapped_column(Float, default=0.0)
    health: Mapped[str] = mapped_column(String(20), default="green")  # green, amber, red
    progress_pct: Mapped[float] = mapped_column(Float, default=0.0)

    # Relationships
    organization = relationship("Organization", back_populates="projects")
    owner = relationship("Employee", foreign_keys=[owner_id], back_populates="projects_owned")
    members = relationship("ProjectMember", back_populates="project", cascade="all, delete-orphan")
    milestones = relationship("Milestone", back_populates="project", cascade="all, delete-orphan")
    tasks = relationship("Task", back_populates="project", cascade="all, delete-orphan")
    snapshots = relationship("ProjectProgressSnapshot", back_populates="project", cascade="all, delete-orphan")
    timesheets = relationship("Timesheet", back_populates="project")

    __table_args__ = (
        Index("ix_projects_org_status", "org_id", "status"),
        Index("ix_projects_org_code", "org_id", "code", unique=True),
    )


class ProjectMember(Base, TimestampMixin):
    """Team member assignment to a project."""
    __tablename__ = "project_members"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    org_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    employee_id: Mapped[str] = mapped_column(String(36), ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True)
    role_on_project: Mapped[str] = mapped_column(String(100), default="Member")
    allocation_pct: Mapped[float] = mapped_column(Float, default=100.0)
    billable_rate: Mapped[float] = mapped_column(Float, default=0.0)

    # Relationships
    project = relationship("Project", back_populates="members")
    employee = relationship("Employee", back_populates="project_memberships")

    __table_args__ = (
        Index("ix_project_members_unique", "project_id", "employee_id", unique=True),
    )

