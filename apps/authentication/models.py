import uuid
from django.db import models
from django.conf import settings
from apps.tenants.models import Tenant
from apps.users.models import TenantMembership

# settings.AUTH_USER_MODEL is used to reference the custom User model

class AuthSession(models.Model):
    SESSION_TYPE_CHOICES = [
        ('WEB', 'Web'),
        ('MOBILE', 'Mobile'),
        ('API', 'API'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='auth_sessions', null=True, blank=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='auth_sessions')
    membership = models.ForeignKey(TenantMembership, on_delete=models.SET_NULL, null=True, blank=True)

    session_type = models.CharField(max_length=20, choices=SESSION_TYPE_CHOICES, default='WEB')
    device_id = models.CharField(max_length=255, blank=True, null=True)
    user_agent = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_seen_at = models.DateTimeField(auto_now=True)
    
    revoked_at = models.DateTimeField(null=True, blank=True)
    revoke_reason = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return f"Session {self.id} for {self.user.email}"

class RefreshToken(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, null=True, blank=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    auth_session = models.ForeignKey(AuthSession, on_delete=models.CASCADE, related_name='refresh_tokens')

    token_hash = models.CharField(max_length=255, unique=True)
    token_algo = models.CharField(max_length=50)
    
    token_family_id = models.CharField(max_length=255)
    parent_token = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='child_tokens')

    issued_at = models.DateTimeField()
    expires_at = models.DateTimeField()
    last_used_at = models.DateTimeField(null=True, blank=True)

    is_revoked = models.BooleanField(default=False)
    revoked_at = models.DateTimeField(null=True, blank=True)
    revoke_reason = models.CharField(max_length=255, blank=True)

    is_replaced = models.BooleanField(default=False)
    replaced_by_token = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='replaced_tokens')

    def __str__(self):
        return f"RefreshToken (Fam: {self.token_family_id})"

class AccessTokenJTI(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    auth_session = models.ForeignKey(AuthSession, on_delete=models.CASCADE)

    jti_hash = models.CharField(max_length=255, unique=True)
    hash_algo = models.CharField(max_length=50)
    
    issued_at = models.DateTimeField()
    expires_at = models.DateTimeField()

    is_revoked = models.BooleanField(default=False)
    revoked_at = models.DateTimeField(null=True, blank=True)
    revoke_reason = models.CharField(max_length=255, blank=True)

class OTPChallenge(models.Model):
    PURPOSE_CHOICES = [
        ('LOGIN', 'Login'),
        ('EMAIL_VERIFY', 'Email Verify'),
        ('PASSWORD_RESET', 'Password Reset'),
        ('MFA_STEPUP', 'MFA Step Up'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    membership = models.ForeignKey(TenantMembership, on_delete=models.SET_NULL, null=True, blank=True)

    purpose = models.CharField(max_length=50, choices=PURPOSE_CHOICES)
    channel = models.CharField(max_length=20, default='EMAIL')
    target = models.CharField(max_length=255)
    
    code_hash = models.CharField(max_length=255)
    code_algo = models.CharField(max_length=50)

    attempt_count = models.IntegerField(default=0)
    max_attempts = models.IntegerField(default=3)
    
    sent_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    verified_at = models.DateTimeField(null=True, blank=True)
    last_attempt_at = models.DateTimeField(null=True, blank=True)

    is_consumed = models.BooleanField(default=False)
    consumed_at = models.DateTimeField(null=True, blank=True)

class TrustedDevice(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    auth_session = models.ForeignKey(AuthSession, on_delete=models.SET_NULL, null=True, blank=True)

    device_fingerprint_hash = models.CharField(max_length=255, unique=True)
    hash_algo = models.CharField(max_length=50)

    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField()
    
    is_revoked = models.BooleanField(default=False)
    revoked_at = models.DateTimeField(null=True, blank=True)

class AuthEvent(models.Model):
    EVENT_TYPES = [
        ('LOGIN_SUCCESS', 'Login Success'),
        ('LOGIN_FAILED', 'Login Failed'),
        ('LOGOUT', 'Logout'),
        ('TOKEN_REFRESH', 'Token Refresh'),
        ('OTP_SENT', 'OTP Sent'),
        ('OTP_FAILED', 'OTP Failed'),
        ('OTP_VERIFIED', 'OTP Verified'),
        ('LOCKED', 'Locked'),
        ('UNLOCKED', 'Unlocked'),
        ('PASSWORD_CHANGED', 'Password Changed'),
        ('INVITE_ACCEPTED', 'Invite Accepted')
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    auth_session = models.ForeignKey(AuthSession, on_delete=models.SET_NULL, null=True, blank=True)

    event_type = models.CharField(max_length=50, choices=EVENT_TYPES)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

class PasswordResetToken(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    
    token_hash = models.CharField(max_length=255, unique=True)
    token_algo = models.CharField(max_length=50)
    
    issued_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)
    
    is_revoked = models.BooleanField(default=False)
    revoked_at = models.DateTimeField(null=True, blank=True)

class EmailVerificationToken(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    
    token_hash = models.CharField(max_length=255, unique=True)
    token_algo = models.CharField(max_length=50)
    
    issued_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)
    
    is_revoked = models.BooleanField(default=False)
    revoked_at = models.DateTimeField(null=True, blank=True)
