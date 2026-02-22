import uuid
from django.db import models
from core.models import TimeStampedModel
from apps.tenants.models import Tenant
from apps.users.models import User, TenantMembership

class Department(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='departments')
    name = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} ({self.tenant.slug})"

class Program(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='programs')
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='programs')
    name = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} - {self.department.name}"

from django.contrib.postgres.search import SearchVector, SearchVectorField
from django.contrib.postgres.indexes import GinIndex

class Thesis(TimeStampedModel):
    STATUS_CHOICES = [
        ('DRAFT', 'Draft'),
        ('SUBMITTED', 'Submitted'),
        ('IN_REVIEW', 'In Review'),
        ('APPROVED', 'Approved'),
        ('PUBLISHED', 'Published'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='theses')
    title = models.CharField(max_length=500)
    abstract = models.TextField()
    year = models.IntegerField()
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='DRAFT')

    # FTS
    search_vector = SearchVectorField(null=True, blank=True)

    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True, related_name='theses')
    program = models.ForeignKey(Program, on_delete=models.SET_NULL, null=True, blank=True, related_name='theses')
    created_by_membership = models.ForeignKey(TenantMembership, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_theses')

    submitted_at = models.DateTimeField(null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    published_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            GinIndex(fields=['search_vector']),
        ]

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if hasattr(self, 'id') and self.id:
            # We must use update() since SearchVector is a query expression, not a string value
            Thesis.objects.filter(pk=self.pk).update(
                search_vector=SearchVector('title', weight='A', config='english') + 
                              SearchVector('abstract', weight='B', config='english')
            )

    def __str__(self):
        return self.title

class ThesisStatusHistory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    thesis = models.ForeignKey(Thesis, on_delete=models.CASCADE, related_name='status_history')

    from_status = models.CharField(max_length=50, blank=True)
    to_status = models.CharField(max_length=50)
    changed_by_membership = models.ForeignKey(TenantMembership, on_delete=models.SET_NULL, null=True, blank=True)
    note = models.TextField(blank=True)
    changed_at = models.DateTimeField(auto_now_add=True)

class ThesisReview(models.Model):
    DECISION_CHOICES = [
        ('PENDING', 'Pending'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
        ('CHANGES_REQUESTED', 'Changes Requested'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    thesis = models.ForeignKey(Thesis, on_delete=models.CASCADE, related_name='reviews')
    reviewer_membership = models.ForeignKey(TenantMembership, on_delete=models.CASCADE, related_name='reviews')
    
    decision = models.CharField(max_length=50, choices=DECISION_CHOICES, default='PENDING')
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

class ThesisAuthor(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    thesis = models.ForeignKey(Thesis, on_delete=models.CASCADE, related_name='authors')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='authored_theses')
    
    display_name = models.CharField(max_length=255)
    sort_order = models.IntegerField(default=0)

    class Meta:
        ordering = ['sort_order']

class ThesisAdviser(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    thesis = models.ForeignKey(Thesis, on_delete=models.CASCADE, related_name='advisers')
    adviser_membership = models.ForeignKey(TenantMembership, on_delete=models.CASCADE, related_name='advised_theses')

class Keyword(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='keywords')
    value = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.value

class ThesisKeyword(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    thesis = models.ForeignKey(Thesis, on_delete=models.CASCADE, related_name='thesis_keywords')
    keyword = models.ForeignKey(Keyword, on_delete=models.CASCADE, related_name='thesis_keywords')

    class Meta:
        unique_together = ('thesis', 'keyword')

class FileObject(models.Model):
    PROVIDER_CHOICES = [
        ('S3', 'S3'),
        ('SPACES', 'Spaces'),
        ('MINIO', 'MinIO'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    provider = models.CharField(max_length=50, choices=PROVIDER_CHOICES, default='S3')
    bucket = models.CharField(max_length=255)
    object_key = models.CharField(max_length=1024)
    filename = models.CharField(max_length=255)
    content_type = models.CharField(max_length=100)
    size_bytes = models.BigIntegerField()
    checksum = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.filename

class ThesisFile(models.Model):
    KIND_CHOICES = [
        ('MAIN_PDF', 'Main PDF'),
        ('ATTACHMENT', 'Attachment'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    thesis = models.ForeignKey(Thesis, on_delete=models.CASCADE, related_name='files')
    file_object = models.ForeignKey(FileObject, on_delete=models.CASCADE)
    
    kind = models.CharField(max_length=50, choices=KIND_CHOICES, default='MAIN_PDF')
    label = models.CharField(max_length=255, blank=True)
    uploaded_by_membership = models.ForeignKey(TenantMembership, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.kind} for {self.thesis.title}"
