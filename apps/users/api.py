from typing import List
from uuid import UUID
from django.shortcuts import get_object_or_404
from django.utils import timezone
from ninja import Router
from ninja.errors import HttpError
import hashlib
import secrets

from apps.users.models import User, TenantMembership, Invitation
from apps.users.schemas import UserProfileSchema, TenantMembershipSchema, InvitationSchema, InviteCreateSchema, InviteAcceptSchema
from apps.repository.api import get_tenant_from_request

users_router = Router(tags=["Users"])

@users_router.get("/me", response=UserProfileSchema)
def get_my_profile(request):
    """
    Get Current User Profile
    
    Returns the user's profile and their memberships in the tenant.
    Assumes standard authentication is applied.
    """
    tenant = get_tenant_from_request(request)
    # For MVP without a proper auth dependency that resolves user, we'll
    # assume the first membership for testing if request.user is not authenticated
    if request.user.is_authenticated:
        user = request.user
    else:
        # Fallback for dev/testing when auth middleware isn't fully wired for Ninja
        user = User.objects.first()
        if not user:
            raise HttpError(401, "Not authenticated")
            
    memberships = TenantMembership.objects.filter(user=user, tenant=tenant)
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
    # Ideally checking if requester is TenantAdmin
    return TenantMembership.objects.filter(tenant=tenant)

@users_router.post("/invites", response=InvitationSchema)
def send_invitation(request, payload: InviteCreateSchema):
    """
    Send Invitation
    
    Invite a user to the tenant organization by email with a specific role.
    """
    tenant = get_tenant_from_request(request)
    
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
        expires_at=expires_at
    )
    
    # Normally we would send an email here with `raw_token` in a link
    
    return invitation

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
    TenantMembership.objects.get_or_create(
        tenant=invitation.tenant,
        user=user,
        defaults={'role': invitation.role, 'status': 'ACTIVE'}
    )
    
    invitation.accepted_at = timezone.now()
    invitation.save()
    
    return {"success": True, "message": "Invitation accepted successfully"}
