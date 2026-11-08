import uuid
from datetime import date, datetime
from typing import Optional
from sqlalchemy import String, Date, DateTime, Float, Boolean, ForeignKey, Text, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base, TimestampMixin


class Timesheet(Base, TimestampMixin):
    """Timesheet log with submission and manager approval workflow."""
    __tablename__ = "timesheets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    org_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    employee_id: Mapped[str] = mapped_column(String(36), ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    task_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True, index=True)

    work_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    hours: Mapped[float] = mapped_column(Float, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    billable: Mapped[bool] = mapped_column(Boolean, default=True)

    # Status: draft, submitted, approved, rejected
    status: Mapped[str] = mapped_column(String(50), default="draft")
    approved_by: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("employees.id", ondelete="SET NULL"), nullable=True)
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    employee = relationship("Employee", foreign_keys=[employee_id], back_populates="timesheets")
    project = relationship("Project", back_populates="timesheets")
    task = relationship("Task", back_populates="timesheets")
    approver = relationship("Employee", foreign_keys=[approved_by])

    __table_args__ = (
        Index("ix_timesheets_emp_date", "employee_id", "work_date"),
        Index("ix_timesheets_org_status", "org_id", "status"),
        Index("ix_timesheets_proj_date", "project_id", "work_date"),
    )

