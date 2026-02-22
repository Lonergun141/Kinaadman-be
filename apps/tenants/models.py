import uuid
from django.db import models
from core.models import TimeStampedModel

class Tenant(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    slug = models.CharField(max_length=100, unique=True, db_index=True)
    name = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} ({self.slug})"

class TenantBranding(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.OneToOneField(Tenant, on_delete=models.CASCADE, related_name='branding')
    display_name = models.CharField(max_length=255, blank=True)
    logo_url = models.URLField(max_length=500, blank=True, null=True)
    primary_color = models.CharField(max_length=7, blank=True, help_text="Hex color code (e.g. #FFFFFF)")
    secondary_color = models.CharField(max_length=7, blank=True, help_text="Hex color code (e.g. #000000)")
    theme_tokens = models.JSONField(default=dict, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Branding for {self.tenant.name}"

class TenantPolicy(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.OneToOneField(Tenant, on_delete=models.CASCADE, related_name='policy')
    
    # Access Rules
    campus_only = models.BooleanField(default=True)
    invite_only = models.BooleanField(default=False)
    enforce_email_domains = models.BooleanField(default=False)
    enforce_ip_allowlist = models.BooleanField(default=False)
    
    # Security Policy
    max_login_attempts = models.IntegerField(default=5)
    lockout_minutes = models.IntegerField(default=15)
    otp_ttl_seconds = models.IntegerField(default=300) # 5 minutes
    access_token_ttl_seconds = models.IntegerField(default=900) # 15 minutes
    refresh_token_ttl_seconds = models.IntegerField(default=604800) # 7 days
    require_2fa_email_otp = models.BooleanField(default=False)
    allow_remember_device = models.BooleanField(default=True)
    
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Policy for {self.tenant.name}"

class TenantEmailDomain(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='email_domains')
    domain = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('tenant', 'domain')

    def __str__(self):
        return self.domain

class TenantHostAlias(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='host_aliases')
    hostname = models.CharField(max_length=255, unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.hostname
