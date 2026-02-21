from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline
from .models import User, TenantMembership, Invitation

class TenantMembershipInline(TabularInline):
    model = TenantMembership
    extra = 1

@admin.register(User)
class CustomUserAdmin(ModelAdmin):
    list_display = ('email', 'is_active', 'is_staff', 'is_super_admin', 'email_verification_status', 'created_at')
    list_filter = ('is_active', 'is_staff', 'is_super_admin', 'email_verification_status')
    search_fields = ('email',)
    readonly_fields = ('id', 'created_at', 'updated_at', 'last_login_at', 'last_failed_login_at')
    inlines = [TenantMembershipInline]
    
    fieldsets = (
        ('Account Info', {
            'fields': ('id', 'email', 'password')
        }),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_super_admin', 'is_superuser', 'groups', 'user_permissions')
        }),
        ('Security & Verification', {
            'fields': ('email_verification_status', 'email_verified_at', 'failed_login_count', 'locked_until')
        }),
        ('Timestamps', {
            'fields': ('last_login_at', 'last_failed_login_at', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

@admin.register(TenantMembership)
class TenantMembershipAdmin(ModelAdmin):
    list_display = ('user', 'tenant', 'role', 'status')
    list_filter = ('role', 'status', 'tenant')
    search_fields = ('user__email', 'tenant__name')
    readonly_fields = ('id', 'created_at', 'updated_at')

@admin.register(Invitation)
class InvitationAdmin(ModelAdmin):
    list_display = ('email', 'tenant', 'role', 'expires_at', 'accepted_at')
    list_filter = ('role', 'tenant')
    search_fields = ('email', 'tenant__name')
    readonly_fields = ('id', 'token_hash', 'token_algo', 'created_at')
