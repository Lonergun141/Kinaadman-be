from typing import List
from uuid import UUID

from ninja import Router
from django.shortcuts import get_object_or_404
from ninja.errors import HttpError
from apps.authentication.services import get_authenticated_actor, get_authenticated_membership
from apps.tenants.models import (
    Tenant,
    TenantBranding,
    TenantEmailDomain,
    TenantHostAlias,
    TenantPolicy,
)
from apps.tenants.schemas import (
    TenantSchema,
    TenantBrandingSchema,
    TenantPolicySchema,
    TenantBrandingUpdateSchema,
    TenantPolicyUpdateSchema,
    TenantEmailDomainSchema,
    TenantHostAliasSchema,
    TenantEmailDomainCreateSchema,
    TenantHostAliasCreateSchema,
)
from apps.repository.api import get_tenant_from_request

tenants_router = Router(tags=["Tenants"])
TENANT_ADMIN_ROLES = {"TENANT_ADMIN"}


def require_tenant_admin(request, tenant):
    return get_authenticated_membership(
        request,
        tenant,
        allowed_roles=TENANT_ADMIN_ROLES,
        forbidden_message="You do not have permission to manage tenant settings.",
        allow_super_admin=True,
    )


def require_super_admin(request):
    _, user, _ = get_authenticated_actor(request)
    if not user.is_super_admin:
        raise HttpError(403, "You do not have permission to view all tenants.")
    return user


@tenants_router.get("/", response=List[TenantSchema])
def list_supervised_tenants(request):
    require_super_admin(request)
    return (
        Tenant.objects.filter(is_active=True)
        .select_related("branding", "policy")
        .order_by("name")
    )

@tenants_router.get("/bootstrap", response=TenantSchema)
def bootstrap_tenant(request):
    """
    Bootstrap Tenant
    
    Resolves the current tenant context and returns its public branding and policies
    so the frontend can render white-labeled views.
    """
    tenant = get_tenant_from_request(request)
    # Ensure nested relationships exist
    if not hasattr(tenant, 'branding'):
        TenantBranding.objects.create(tenant=tenant)
    if not hasattr(tenant, 'policy'):
        TenantPolicy.objects.create(tenant=tenant)
        
    return tenant

@tenants_router.put("/branding", response=TenantBrandingSchema)
def update_branding(request, payload: TenantBrandingUpdateSchema):
    """
    Update Branding
    
    Update the branding (logo, colors, name) of the resolved tenant.
    Requires Tenant Admin privileges.
    """
    tenant = get_tenant_from_request(request)
    require_tenant_admin(request, tenant)
    # Get or create branding
    branding, created = TenantBranding.objects.get_or_create(tenant=tenant)
    
    for attr, value in payload.dict(exclude_unset=True).items():
        setattr(branding, attr, value)
    
    branding.save()
    return branding

@tenants_router.put("/policy", response=TenantPolicySchema)
def update_policy(request, payload: TenantPolicyUpdateSchema):
    """
    Update Policy
    
    Update the security and access policies of the resolved tenant.
    Requires Tenant Admin privileges.
    """
    tenant = get_tenant_from_request(request)
    require_tenant_admin(request, tenant)
    # Get or create policy
    policy, created = TenantPolicy.objects.get_or_create(tenant=tenant)
    
    for attr, value in payload.dict(exclude_unset=True).items():
        setattr(policy, attr, value)
        
    policy.save()
    return policy


@tenants_router.get("/email-domains", response=List[TenantEmailDomainSchema])
def list_email_domains(request):
    tenant = get_tenant_from_request(request)
    require_tenant_admin(request, tenant)
    return TenantEmailDomain.objects.filter(tenant=tenant).order_by("domain")


@tenants_router.post("/email-domains", response=TenantEmailDomainSchema)
def create_email_domain(request, payload: TenantEmailDomainCreateSchema):
    tenant = get_tenant_from_request(request)
    require_tenant_admin(request, tenant)
    email_domain, created = TenantEmailDomain.objects.get_or_create(
        tenant=tenant,
        domain=payload.domain.strip().lower(),
        defaults={"is_active": True},
    )
    if not created and not email_domain.is_active:
        email_domain.is_active = True
        email_domain.save(update_fields=["is_active"])
    return email_domain


@tenants_router.delete("/email-domains/{domain_id}")
def delete_email_domain(request, domain_id: UUID):
    tenant = get_tenant_from_request(request)
    require_tenant_admin(request, tenant)
    email_domain = get_object_or_404(TenantEmailDomain, id=domain_id, tenant=tenant)
    email_domain.delete()
    return {"success": True}


@tenants_router.get("/host-aliases", response=List[TenantHostAliasSchema])
def list_host_aliases(request):
    tenant = get_tenant_from_request(request)
    require_tenant_admin(request, tenant)
    return TenantHostAlias.objects.filter(tenant=tenant).order_by("hostname")


@tenants_router.post("/host-aliases", response=TenantHostAliasSchema)
def create_host_alias(request, payload: TenantHostAliasCreateSchema):
    tenant = get_tenant_from_request(request)
    require_tenant_admin(request, tenant)
    alias, created = TenantHostAlias.objects.get_or_create(
        tenant=tenant,
        hostname=payload.hostname.strip().lower(),
        defaults={"is_active": True},
    )
    if not created and not alias.is_active:
        alias.is_active = True
        alias.save(update_fields=["is_active"])
    return alias


@tenants_router.delete("/host-aliases/{alias_id}")
def delete_host_alias(request, alias_id: UUID):
    tenant = get_tenant_from_request(request)
    require_tenant_admin(request, tenant)
    alias = get_object_or_404(TenantHostAlias, id=alias_id, tenant=tenant)
    alias.delete()
    return {"success": True}
