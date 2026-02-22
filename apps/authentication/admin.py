from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import (
    AuthSession, RefreshToken, AccessTokenJTI, OTPChallenge, 
    TrustedDevice, AuthEvent, PasswordResetToken, EmailVerificationToken
)

@admin.register(AuthSession)
class AuthSessionAdmin(ModelAdmin):
    list_display = ('id', 'user', 'tenant', 'session_type', 'is_active', 'created_at', 'last_seen_at')
    list_filter = ('session_type', 'is_active', 'tenant')
    search_fields = ('user__email', 'device_id', 'ip_address')
    readonly_fields = ('id', 'created_at', 'last_seen_at')

@admin.register(RefreshToken)
class RefreshTokenAdmin(ModelAdmin):
    list_display = ('user', 'tenant', 'issued_at', 'expires_at', 'is_revoked', 'is_replaced')
    list_filter = ('is_revoked', 'is_replaced', 'tenant')
    search_fields = ('user__email', 'token_family_id')
    readonly_fields = ('id', 'token_hash', 'token_algo')

@admin.register(AuthEvent)
class AuthEventAdmin(ModelAdmin):
    list_display = ('event_type', 'user', 'tenant', 'ip_address', 'created_at')
    list_filter = ('event_type', 'tenant')
    search_fields = ('user__email', 'ip_address')
    readonly_fields = ('id', 'created_at')
    
    # Audit events should not be modified
    def has_add_permission(self, request):
        return False
    def has_change_permission(self, request, obj=None):
        return False

@admin.register(OTPChallenge)
class OTPChallengeAdmin(ModelAdmin):
    list_display = ('user', 'purpose', 'channel', 'target', 'is_consumed', 'expires_at')
    list_filter = ('purpose', 'channel', 'is_consumed')
    search_fields = ('user__email', 'target')
    readonly_fields = ('id', 'code_hash', 'code_algo')

# Register remaining models simply
@admin.register(AccessTokenJTI)
class AccessTokenJTIAdmin(ModelAdmin):
    pass

@admin.register(TrustedDevice)
class TrustedDeviceAdmin(ModelAdmin):
    pass

@admin.register(PasswordResetToken)
class PasswordResetTokenAdmin(ModelAdmin):
    pass

@admin.register(EmailVerificationToken)
class EmailVerificationTokenAdmin(ModelAdmin):
    pass

