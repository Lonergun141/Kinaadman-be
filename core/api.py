from typing import List
import jwt
from django.conf import settings
from ninja import Router
from ninja.errors import HttpError
from core.models import AuditLog
from core.schemas import AuditLogSchema
from apps.repository.api import get_tenant_from_request
from apps.users.models import TenantMembership

core_router = Router(tags=["System"])
AUDIT_LOG_ROLES = {"LIBRARIAN", "TENANT_ADMIN"}


def get_audit_membership_from_request(request, tenant):
    authorization = request.headers.get("Authorization", "")

    if not authorization.startswith("Bearer "):
        raise HttpError(401, "Authentication is required to view audit logs.")

    access_token = authorization.split(" ", 1)[1].strip()

    try:
        payload = jwt.decode(
            access_token,
            getattr(settings, "SECRET_KEY"),
            algorithms=["HS256"],
        )
    except jwt.InvalidTokenError as exc:
        raise HttpError(401, "Authentication token is invalid.") from exc

    user_id = payload.get("sub")
    if not user_id:
        raise HttpError(401, "Authentication token is invalid.")

    membership = TenantMembership.objects.filter(
        tenant=tenant,
        user_id=user_id,
        status="ACTIVE",
    ).first()

    if not membership or membership.role not in AUDIT_LOG_ROLES:
        raise HttpError(403, "You do not have permission to view audit logs.")

    return membership

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
