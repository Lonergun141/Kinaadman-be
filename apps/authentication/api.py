from ninja import Router
from django.contrib.auth import authenticate
from django.utils import timezone
from ninja.errors import HttpError
from apps.users.models import TenantMembership
from apps.authentication.models import AuthSession, RefreshToken
from apps.authentication.schemas import LoginRequest, TokenRefreshRequest, LoginResponse, TokenResponse
from apps.authentication.services import generate_tokens_for_user
from apps.repository.api import get_tenant_from_request
import hashlib

router = Router(tags=["Authentication"])

@router.post("/login", response=LoginResponse)
def login(request, payload: LoginRequest):
    tenant = get_tenant_from_request(request)
    user = authenticate(email=payload.email, password=payload.password)
    if not user:
        raise HttpError(401, "Invalid credentials")
    
    if user.is_locked:
        raise HttpError(401, "Account locked")

    membership = TenantMembership.objects.filter(
        tenant=tenant,
        user=user,
        status="ACTIVE",
    ).first()

    if not membership and not user.is_super_admin:
        raise HttpError(403, "You do not have an active membership for this archive.")

    policy = tenant.policy if hasattr(tenant, "policy") else None
    if policy and policy.enforce_email_domains and not user.is_super_admin:
        email_domain = user.email.split("@")[-1].lower()
        allowed_domain = tenant.email_domains.filter(
            domain__iexact=email_domain,
            is_active=True,
        ).exists()
        if not allowed_domain:
            raise HttpError(403, "Your email domain is not allowed for this archive.")

    # MVP: Assume OTP is bypassed.
    # Create Auth Session
    session = AuthSession.objects.create(
        tenant=tenant,
        user=user,
        membership=membership,
        ip_address=request.META.get('REMOTE_ADDR'),
        user_agent=request.META.get('HTTP_USER_AGENT', '')[:255]
    )
    
    tokens = generate_tokens_for_user(user, session)
    
    return {
        "tokens": tokens,
        "user": {
            "id": str(user.id),
            "email": user.email,
            "role": "SUPER_ADMIN" if user.is_super_admin else membership.role,
            "membership_id": str(membership.id) if membership else None,
            "is_super_admin": user.is_super_admin,
        }
    }

@router.post("/refresh", response=TokenResponse)
def refresh(request, payload: TokenRefreshRequest):
    token_hash = hashlib.sha256(payload.refresh_token.encode()).hexdigest()
    
    try:
        old_token = RefreshToken.objects.get(token_hash=token_hash)
    except RefreshToken.DoesNotExist:
        raise HttpError(401, "Invalid refresh token")

    if old_token.is_revoked or old_token.expires_at < timezone.now():
        raise HttpError(401, "Refresh token expired or revoked")

    # Rotate
    old_token.is_revoked = True
    old_token.revoked_at = timezone.now()
    old_token.is_replaced = True
    old_token.save()

    session = old_token.auth_session
    tokens = generate_tokens_for_user(old_token.user, session)
    return tokens

@router.post("/logout")
def logout(request, payload: TokenRefreshRequest):
    token_hash = hashlib.sha256(payload.refresh_token.encode()).hexdigest()
    
    try:
        rt = RefreshToken.objects.get(token_hash=token_hash)
        rt.is_revoked = True
        rt.revoked_at = timezone.now()
        rt.save()

        # Revoke session
        session = rt.auth_session
        session.is_active = False
        session.revoked_at = timezone.now()
        session.save()
    except RefreshToken.DoesNotExist:
        pass
        
    return {"success": True}

