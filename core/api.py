from typing import List
from ninja import Router
from core.models import AuditLog
from core.schemas import AuditLogSchema
from apps.repository.api import get_tenant_from_request

core_router = Router(tags=["System"])

@core_router.get("/audit", response=List[AuditLogSchema])
def list_audit_logs(request):
    """
    List Audit Logs
    
    Returns the system audit logs for the current tenant.
    Requires Tenant Admin privileges.
    """
    tenant = get_tenant_from_request(request)
    return AuditLog.objects.filter(tenant=tenant).order_by('-created_at')[:100]
