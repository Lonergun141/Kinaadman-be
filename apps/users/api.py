from typing import List, Optional
from uuid import UUID
from django.shortcuts import get_object_or_404
from django.utils import timezone
from ninja import Router
from ninja.errors import HttpError
import hashlib
import secrets

from apps.users.models import User, TenantMembership, Invitation
from apps.users.schemas import (
    UserProfileSchema,
    TenantMembershipSchema,
    InvitationSchema,
    InviteCreateSchema,
    InviteAcceptSchema,
    TenantMembershipUpdateSchema,
)
from apps.authentication.services import get_authenticated_actor, get_authenticated_membership
from apps.repository.api import get_tenant_from_request

users_router = Router(tags=["Users"])
TENANT_ADMIN_ROLES = {"TENANT_ADMIN"}


def build_invitation_response(invitation: Invitation, accept_url: Optional[str] = None):
    return {
        "id": invitation.id,
        "email": invitation.email,
        "role": invitation.role,
        "expires_at": invitation.expires_at,
        "accepted_at": invitation.accepted_at,
        "created_at": invitation.created_at,
        "accept_url": accept_url,
    }


def require_tenant_admin(request, tenant):
    return get_authenticated_membership(
        request,
        tenant,
        allowed_roles=TENANT_ADMIN_ROLES,
        forbidden_message="You do not have permission to manage tenant users.",
        allow_super_admin=True,
    )

@users_router.get("/me", response=UserProfileSchema)
def get_my_profile(request):
    """
    Get Current User Profile
    
    Returns the user's profile and their memberships in the tenant.
    Assumes standard authentication is applied.
    """
    tenant = get_tenant_from_request(request)
    _, user, _ = get_authenticated_actor(request, tenant)
    memberships = TenantMembership.objects.filter(user=user, tenant=tenant).select_related("user")
    return {
        "user": user,
        "memberships": list(memberships)
    }

@users_router.get("/memberships", response=List[TenantMembershipSchema])
def list_tenant_memberships(request):
    """
    List Tenant Memberships
    
    Lists all user memberships within the current tenant organization (Tenant Admin).
    """
    tenant = get_tenant_from_request(request)
    get_authenticated_membership(request, tenant, allow_super_admin=True)
    return TenantMembership.objects.filter(tenant=tenant).select_related("user").order_by("user__email")


@users_router.patch("/memberships/{membership_id}", response=TenantMembershipSchema)
def update_tenant_membership(request, membership_id: UUID, payload: TenantMembershipUpdateSchema):
    tenant = get_tenant_from_request(request)
    require_tenant_admin(request, tenant)
    membership = get_object_or_404(
        TenantMembership.objects.select_related("user"),
        id=membership_id,
        tenant=tenant,
    )

    updated_fields = []
    if payload.role is not None:
        membership.role = payload.role
        updated_fields.append("role")
    if payload.status is not None:
        membership.status = payload.status
        updated_fields.append("status")

    if not updated_fields:
        raise HttpError(400, "At least one membership field must be provided.")

    updated_fields.append("updated_at")
    membership.save(update_fields=updated_fields)
    return membership


@users_router.get("/invites", response=List[InvitationSchema])
def list_invitations(request):
    tenant = get_tenant_from_request(request)
    require_tenant_admin(request, tenant)
    invitations = Invitation.objects.filter(tenant=tenant).order_by("-created_at")
    return [build_invitation_response(invitation) for invitation in invitations]

@users_router.post("/invites", response=InvitationSchema)
def send_invitation(request, payload: InviteCreateSchema):
    """
    Send Invitation
    
    Invite a user to the tenant organization by email with a specific role.
    """
    tenant = get_tenant_from_request(request)
    invited_by_membership = require_tenant_admin(request, tenant)
    
    # Generate a secure token
    raw_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    
    expires_at = timezone.now() + timezone.timedelta(days=7)
    
    invitation = Invitation.objects.create(
        tenant=tenant,
        email=payload.email,
        role=payload.role,
        token_hash=token_hash,
        token_algo='sha256',
        expires_at=expires_at,
        invited_by_membership=invited_by_membership,
    )
    
    # Normally we would send an email here with `raw_token` in a link
    
    return build_invitation_response(
        invitation,
        accept_url=f"/invite/{raw_token}",
    )

@users_router.post("/invites/{raw_token}/accept")
def accept_invitation(request, raw_token: str, payload: InviteAcceptSchema):
    """
    Accept Invitation
    
    Accept an invitation by providing the raw token and setting a password.
    """
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    
    invitation = get_object_or_404(Invitation, token_hash=token_hash)
    
    if invitation.expires_at < timezone.now() or invitation.accepted_at:
        raise HttpError(400, "Invitation expired or already accepted")
        
    user = User.objects.filter(email=invitation.email).first()
    if not user:
        user = User.objects.create_user(
            email=invitation.email,
            password=payload.password,
            email_verification_status='VERIFIED',
            email_verified_at=timezone.now()
        )
    else:
        # If user exists, just ensure they are verified or update password if needed
        pass
        
    # Create membership
    membership, created = TenantMembership.objects.get_or_create(
        tenant=invitation.tenant,
        user=user,
        defaults={'role': invitation.role, 'status': 'ACTIVE'}
    )
    if not created:
        membership.role = invitation.role
        membership.status = 'ACTIVE'
        membership.save(update_fields=["role", "status", "updated_at"])
    
    invitation.accepted_at = timezone.now()
    invitation.save()
    
    return {"success": True, "message": "Invitation accepted successfully"}
