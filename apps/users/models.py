import uuid
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils import timezone
from apps.tenants.models import Tenant

class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        if password:
            user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_super_admin', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('email_verification_status', 'VERIFIED')

        if extra_fields.get('is_super_admin') is not True:
            raise ValueError('Superuser must have is_super_admin=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')

        return self.create_user(email, password, **extra_fields)

class User(AbstractBaseUser, PermissionsMixin):
    VERIFICATION_STATUS_CHOICES = [
        ('UNVERIFIED', 'Unverified'),
        ('VERIFIED', 'Verified'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True, db_index=True)
    
    # We use Django's set_password which handles password_hash/algo automatically,
    # but the ERD expects password_algo tracking explicitly, though Django abstract base does this.
    # To strictly follow ERD, we add standard Django fields plus ERD fields.
    password_algo = models.CharField(max_length=50, blank=True)
    password_changed_at = models.DateTimeField(null=True, blank=True)

    is_active = models.BooleanField(default=True)
    is_super_admin = models.BooleanField(default=False)
    # Django requires is_staff for admin panel access
    is_staff = models.BooleanField(default=False) 

    last_login_at = models.DateTimeField(null=True, blank=True)
    last_failed_login_at = models.DateTimeField(null=True, blank=True)

    failed_login_count = models.IntegerField(default=0)
    locked_until = models.DateTimeField(null=True, blank=True)

    email_verification_status = models.CharField(
        max_length=20, 
        choices=VERIFICATION_STATUS_CHOICES, 
        default='UNVERIFIED'
    )
    email_verified_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.email

    @property
    def is_locked(self):
        if self.locked_until and self.locked_until > timezone.now():
            return True
        return False

class TenantMembership(models.Model):
    ROLE_CHOICES = [
        ('STUDENT', 'Student'),
        ('ADVISER', 'Adviser'),
        ('LIBRARIAN', 'Librarian'),
        ('TENANT_ADMIN', 'Tenant Admin'),
    ]

    STATUS_CHOICES = [
        ('ACTIVE', 'Active'),
        ('SUSPENDED', 'Suspended'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='memberships')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tenant_memberships')
    
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ACTIVE')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('tenant', 'user')

    def __str__(self):
        return f"{self.user.email} - {self.role} in {self.tenant.slug}"

class Invitation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='invitations')
    email = models.EmailField()
    role = models.CharField(max_length=20, choices=TenantMembership.ROLE_CHOICES)

    token_hash = models.CharField(max_length=255, unique=True)
    token_algo = models.CharField(max_length=50)
    
    expires_at = models.DateTimeField()
    accepted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    invited_by_membership = models.ForeignKey(
        TenantMembership, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='sent_invitations'
    )

    def __str__(self):
        return f"Invite for {self.email} to {self.tenant.slug}"
