from ninja import Schema
from pydantic import EmailStr
from typing import Optional

class LoginRequest(Schema):
    email: EmailStr
    password: str
    tenant_hint: Optional[str] = None

class OTPVerifyRequest(Schema):
    challenge_id: str
    code: str

class TokenRefreshRequest(Schema):
    refresh_token: str

class TokenResponse(Schema):
    access_token: str
    refresh_token: str
    expires_in: int

class UserResponse(Schema):
    id: str
    email: str
    role: str
    membership_id: Optional[str] = None
    is_super_admin: bool = False

class LoginResponse(Schema):
    tokens: TokenResponse
    user: UserResponse
    # Could include tenantContext here later
