import uuid
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import String, DateTime, ForeignKey, JSON, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base, utc_now


class AuditLog(Base):
    """Immutable audit trail of all data mutations across tenants."""
    __tablename__ = "audit_log"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    org_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    actor_employee_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("employees.id", ondelete="SET NULL"), nullable=True, index=True)

    action: Mapped[str] = mapped_column(String(50), nullable=False)  # CREATE, UPDATE, DELETE, LOGIN, APPROVE, REJECT
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # project, task, timesheet, employee, etc.
    entity_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    before_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    after_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False, index=True)

    # Relationships
    actor = relationship("Employee")

    __table_args__ = (
        Index("ix_audit_org_created", "org_id", "created_at"),
        Index("ix_audit_entity", "entity_type", "entity_id"),
    )

