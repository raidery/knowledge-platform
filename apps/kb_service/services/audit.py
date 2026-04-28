from apps.kb_service.models.audit_log import AuditLog


class AuditService:
    async def log(self, job_id: str, action: str, operator: str, detail: dict | None = None):
        await AuditLog.create(
            job_id=job_id,
            action=action,
            operator=operator,
            detail=detail,
        )