import uuid
from datetime import date
from typing import Optional
from sqlalchemy import String, Date, ForeignKey, Text, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base, TimestampMixin


class Leave(Base, TimestampMixin):
    """Approved employee leave requests to prevent false attendance absence flags."""
    __tablename__ = "leaves"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    org_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    employee_id: Mapped[str] = mapped_column(String(36), ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True)

    leave_type: Mapped[str] = mapped_column(String(50), default="vacation")  # vacation, sick, personal, unpaid
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="approved")  # pending, approved, rejected
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    employee = relationship("Employee")

    __table_args__ = (
        Index("ix_leaves_emp_dates", "employee_id", "start_date", "end_date"),
    )

