from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.audit_log import AuditLog


class AuditService:
    @staticmethod
    async def log_mutation(
        session: AsyncSession,
        org_id: str,
        actor_employee_id: Optional[str],
        action: str,
        entity_type: str,
        entity_id: str,
        before_json: Optional[Dict[str, Any]] = None,
        after_json: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None
    ) -> AuditLog:
        """Writes an immutable record to audit_log."""
        entry = AuditLog(
            org_id=org_id,
            actor_employee_id=actor_employee_id,
            action=action.upper(),
            entity_type=entity_type.lower(),
            entity_id=str(entity_id),
            before_json=before_json,
            after_json=after_json,
            ip_address=ip_address
        )
        session.add(entry)
        await session.flush()
        return entry

