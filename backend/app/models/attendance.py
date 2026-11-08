import uuid
from datetime import date, datetime
from typing import Optional
from sqlalchemy import String, Date, DateTime, Integer, Boolean, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base, TimestampMixin


class Attendance(Base, TimestampMixin):
    """Daily derived attendance rollup per employee."""
    __tablename__ = "attendance"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    org_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    employee_id: Mapped[str] = mapped_column(String(36), ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True)

    work_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    first_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_logout_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    total_active_minutes: Mapped[int] = mapped_column(Integer, default=0)
    session_count: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(50), default="absent")  # present, absent, half_day, leave, holiday
    is_late: Mapped[bool] = mapped_column(Boolean, default=False)

    # Relationships
    employee = relationship("Employee", back_populates="attendance_records")

    __table_args__ = (
        Index("ix_attendance_emp_date", "employee_id", "work_date", unique=True),
        Index("ix_attendance_org_date", "org_id", "work_date"),
    )

