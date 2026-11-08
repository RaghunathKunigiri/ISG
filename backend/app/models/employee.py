import uuid
from datetime import date
from typing import Optional, List
from sqlalchemy import String, Date, Boolean, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base, TimestampMixin


class Employee(Base, TimestampMixin):
    """Employee record within an organization."""
    __tablename__ = "employees"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    org_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    employee_code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    phone: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    role_id: Mapped[str] = mapped_column(String(36), ForeignKey("roles.id"), nullable=False, index=True)
    manager_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("employees.id", ondelete="SET NULL"), nullable=True, index=True)

    department: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    designation: Mapped[str] = mapped_column(String(100), nullable=False)
    location: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    shift: Mapped[str] = mapped_column(String(50), default="general")
    date_of_joining: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="active", index=True)  # active, inactive, terminated

    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    mfa_secret: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    mfa_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Relationships
    organization = relationship("Organization", back_populates="employees")
    role = relationship("Role", back_populates="employees", lazy="selectin")
    manager = relationship("Employee", remote_side=[id], backref="direct_reports")
    projects_owned = relationship("Project", back_populates="owner")
    project_memberships = relationship("ProjectMember", back_populates="employee")
    assigned_tasks = relationship("Task", foreign_keys="Task.assignee_id", back_populates="assignee")
    reported_tasks = relationship("Task", foreign_keys="Task.reporter_id", back_populates="reporter")
    timesheets = relationship("Timesheet", foreign_keys="Timesheet.employee_id", back_populates="employee")
    login_sessions = relationship("LoginSession", back_populates="employee")
    attendance_records = relationship("Attendance", back_populates="employee")

    __table_args__ = (
        Index("ix_employees_org_email", "org_id", "email", unique=True),
        Index("ix_employees_org_code", "org_id", "employee_code", unique=True),
        Index("ix_employees_org_status", "org_id", "status"),
    )

