from typing import List
from ninja import Router
from core.models import AuditLog
from core.schemas import AuditLogSchema
from apps.authentication.services import get_authenticated_membership
from apps.repository.api import get_tenant_from_request

core_router = Router(tags=["System"])
AUDIT_LOG_ROLES = {"LIBRARIAN", "TENANT_ADMIN"}


def get_audit_membership_from_request(request, tenant):
    return get_authenticated_membership(
        request,
        tenant,
        allowed_roles=AUDIT_LOG_ROLES,
        forbidden_message="You do not have permission to view audit logs.",
        allow_super_admin=True,
    )

@core_router.get("/audit", response=List[AuditLogSchema])
def list_audit_logs(request):
    """
    List Audit Logs
    
    Returns the system audit logs for the current tenant.
    Requires Librarian or Tenant Admin privileges.
    """
    tenant = get_tenant_from_request(request)
    get_audit_membership_from_request(request, tenant)
    return AuditLog.objects.filter(tenant=tenant).order_by('-created_at')[:100]
