import jwt
import datetime
from django.conf import settings
from apps.authentication.models import AuthSession, RefreshToken
from apps.users.models import User
import hashlib
import os

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
