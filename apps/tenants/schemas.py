from typing import Optional
from ninja import ModelSchema, Schema
from uuid import UUID
from apps.tenants.models import Tenant, TenantBranding, TenantPolicy

class TenantBrandingSchema(ModelSchema):
    class Meta:
        model = TenantBranding
        fields = [
            'display_name', 'logo_url', 'primary_color', 
            'secondary_color', 'theme_tokens', 'updated_at'
        ]

class TenantPolicySchema(ModelSchema):
    class Meta:
        model = TenantPolicy
        fields = [
            'campus_only', 'invite_only', 'enforce_email_domains',
            'enforce_ip_allowlist', 'max_login_attempts',
            'lockout_minutes', 'otp_ttl_seconds', 
            'access_token_ttl_seconds', 'refresh_token_ttl_seconds',
            'require_2fa_email_otp', 'allow_remember_device', 'updated_at'
        ]

class TenantSchema(ModelSchema):
    branding: Optional[TenantBrandingSchema] = None
    policy: Optional[TenantPolicySchema] = None

    class Meta:
        model = Tenant
        fields = ['id', 'slug', 'name', 'is_active']
        
class TenantBrandingUpdateSchema(Schema):
    display_name: str
    logo_url: str = None
    primary_color: str = None
    secondary_color: str = None
    theme_tokens: dict = None

class TenantPolicyUpdateSchema(Schema):
    campus_only: bool
    invite_only: bool
    enforce_email_domains: bool
    enforce_ip_allowlist: bool
    max_login_attempts: int
    lockout_minutes: int
    otp_ttl_seconds: int
    access_token_ttl_seconds: int
    refresh_token_ttl_seconds: int
    require_2fa_email_otp: bool
    allow_remember_device: bool
