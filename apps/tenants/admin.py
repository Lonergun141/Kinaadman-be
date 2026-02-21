from django.contrib import admin
from unfold.admin import ModelAdmin, StackedInline, TabularInline
from .models import Tenant, TenantBranding, TenantPolicy, TenantEmailDomain, TenantHostAlias

class TenantBrandingInline(StackedInline):
    model = TenantBranding
    can_delete = False

class TenantPolicyInline(StackedInline):
    model = TenantPolicy
    can_delete = False

class TenantEmailDomainInline(TabularInline):
    model = TenantEmailDomain
    extra = 1

class TenantHostAliasInline(TabularInline):
    model = TenantHostAlias
    extra = 1

@admin.register(Tenant)
class TenantAdmin(ModelAdmin):
    list_display = ('name', 'slug', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('name', 'slug')
    readonly_fields = ('id', 'created_at', 'updated_at')
    inlines = [TenantBrandingInline, TenantPolicyInline, TenantEmailDomainInline, TenantHostAliasInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'name', 'slug', 'is_active')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

@admin.register(TenantBranding)
class TenantBrandingAdmin(ModelAdmin):
    list_display = ('tenant', 'display_name')
    search_fields = ('tenant__name', 'display_name')

@admin.register(TenantPolicy)
class TenantPolicyAdmin(ModelAdmin):
    list_display = ('tenant', 'campus_only', 'invite_only', 'require_2fa_email_otp')
    list_filter = ('campus_only', 'invite_only', 'require_2fa_email_otp')
    search_fields = ('tenant__name',)

@admin.register(TenantEmailDomain)
class TenantEmailDomainAdmin(ModelAdmin):
    list_display = ('domain', 'tenant', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('domain', 'tenant__name')

@admin.register(TenantHostAlias)
class TenantHostAliasAdmin(ModelAdmin):
    list_display = ('hostname', 'tenant', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('hostname', 'tenant__name')
