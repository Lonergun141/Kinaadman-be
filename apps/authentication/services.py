import datetime
import hashlib
import os
from typing import Optional

import jwt
from django.conf import settings
from ninja.errors import HttpError

from apps.authentication.models import AuthSession, RefreshToken
from apps.tenants.models import Tenant
from apps.users.models import TenantMembership, User

JWT_SECRET = getattr(settings, 'SECRET_KEY')
JWT_ALGORITHM = 'HS256'
ACCESS_TOKEN_TTL = 900 # 15 mins default

def generate_tokens_for_user(user: User, session: AuthSession) -> dict:
    """
    Generates an access JWT and a hashed refresh token, storing the refresh token in the DB.
    """
    now = datetime.datetime.now(datetime.timezone.utc)
    access_exp = now + datetime.timedelta(seconds=ACCESS_TOKEN_TTL)
    
    # 1. Generate Access Token (JWT)
    access_payload = {
        'sub': str(user.id),
        'session_id': str(session.id),
        'tenant_id': str(session.tenant.id) if session.tenant else None,
        'iat': int(now.timestamp()),
        'exp': int(access_exp.timestamp())
    }
    access_token = jwt.encode(access_payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    
    # 2. Generate Refresh Token (Opaque, Hashed in DB)
    raw_refresh_token = os.urandom(32).hex()
    token_hash = hashlib.sha256(raw_refresh_token.encode()).hexdigest()
    
    refresh_exp = now + datetime.timedelta(days=7) # 7 days default
    
    RefreshToken.objects.create(
        tenant=session.tenant,
        user=user,
        auth_session=session,
        token_hash=token_hash,
        token_algo='SHA-256',
        token_family_id=str(os.urandom(16).hex()),
        issued_at=now,
        expires_at=refresh_exp,
    )
    
    return {
        'access_token': access_token,
        'refresh_token': raw_refresh_token,
        'expires_in': ACCESS_TOKEN_TTL
    }


def decode_access_token(access_token: str) -> dict:
    try:
        payload = jwt.decode(access_token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.InvalidTokenError as exc:
        raise HttpError(401, "Authentication token is invalid.") from exc

    if not payload.get("sub") or not payload.get("session_id"):
        raise HttpError(401, "Authentication token is invalid.")

    return payload


def get_authenticated_session(request) -> AuthSession:
    authorization = request.headers.get("Authorization", "")

    if not authorization.startswith("Bearer "):
        raise HttpError(401, "Authentication is required.")

    access_token = authorization.split(" ", 1)[1].strip()
    payload = decode_access_token(access_token)
    user_id = payload["sub"]
    session_id = payload["session_id"]

    session = (
        AuthSession.objects.select_related("user", "membership", "tenant")
        .filter(
            id=session_id,
            user_id=user_id,
            is_active=True,
            revoked_at__isnull=True,
        )
        .first()
    )

    if not session:
        raise HttpError(401, "Authentication session is no longer active.")

    return session


def get_authenticated_actor(request, tenant: Optional[Tenant] = None):
    session = get_authenticated_session(request)
    user = session.user
    membership = None

    if tenant is not None and not user.is_super_admin and session.tenant_id != tenant.id:
        raise HttpError(401, "Authentication session does not match the requested tenant.")

    if tenant is not None:
        memberships = TenantMembership.objects.select_related("user").filter(
            tenant=tenant,
            user_id=user.id,
            status="ACTIVE",
        )

        if session.membership_id and session.membership and session.membership.tenant_id == tenant.id:
            memberships = memberships.filter(id=session.membership_id)

        membership = memberships.first()

    return session, user, membership


def get_authenticated_membership(
    request,
    tenant: Tenant,
    allowed_roles: Optional[set[str]] = None,
    forbidden_message: Optional[str] = None,
    allow_super_admin: bool = False,
) -> Optional[TenantMembership]:
    _, user, membership = get_authenticated_actor(request, tenant)

    if membership and (not allowed_roles or membership.role in allowed_roles):
        return membership

    if allow_super_admin and user.is_super_admin:
        return membership

    if not membership:
        raise HttpError(403, "You do not have an active membership in this tenant.")

    if allowed_roles and membership.role not in allowed_roles:
        raise HttpError(
            403,
            forbidden_message or "You do not have permission to perform this action.",
        )

    return membership
