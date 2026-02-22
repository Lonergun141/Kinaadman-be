from ninja import Router
from django.shortcuts import get_object_or_404
from ninja.errors import HttpError
from apps.tenants.models import Tenant, TenantBranding, TenantPolicy
from apps.tenants.schemas import TenantSchema, TenantBrandingSchema, TenantPolicySchema, TenantBrandingUpdateSchema, TenantPolicyUpdateSchema
from apps.repository.api import get_tenant_from_request

tenants_router = Router(tags=["Tenants"])

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
    # Get or create policy
    policy, created = TenantPolicy.objects.get_or_create(tenant=tenant)
    
    for attr, value in payload.dict(exclude_unset=True).items():
        setattr(policy, attr, value)
        
    policy.save()
    return policy
