import uuid
from django.db import models
from django.utils.text import slugify
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
        ('CHANGES_REQUESTED', 'Changes Requested'),
        ('APPROVED', 'Approved'),
        ('PUBLISHED', 'Published'),
        ('ARCHIVED', 'Archived'),
    ]

    VISIBILITY_CHOICES = [
        ('PRIVATE', 'Private'),
        ('CAMPUS_ONLY', 'Campus Only'),
        ('PUBLIC', 'Public'),
        ('EMBARGOED', 'Embargoed'),
    ]

    TYPE_CHOICES = [
        ('THESIS', 'Thesis'),
        ('CAPSTONE', 'Capstone'),
        ('DISSERTATION', 'Dissertation'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='theses')
    title = models.CharField(max_length=500)
    abstract = models.TextField()
    year = models.IntegerField()
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='DRAFT')
    visibility = models.CharField(max_length=50, choices=VISIBILITY_CHOICES, default='PRIVATE')
    thesis_type = models.CharField(max_length=50, choices=TYPE_CHOICES, default='THESIS')
    language = models.CharField(max_length=50, default='English')
    research_category = models.CharField(max_length=255, blank=True)
    methodology = models.CharField(max_length=255, blank=True)
    college_name = models.CharField(max_length=255, blank=True)
    campus_name = models.CharField(max_length=255, blank=True)
    rights_license = models.CharField(max_length=255, blank=True)
    public_slug = models.SlugField(max_length=255, blank=True)
    panel_members = models.JSONField(default=list, blank=True)
    defense_date = models.DateField(null=True, blank=True)
    embargo_until = models.DateField(null=True, blank=True)

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
            models.Index(fields=['tenant', 'public_slug']),
            models.Index(fields=['tenant', 'visibility', 'status']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['tenant', 'public_slug'],
                condition=~models.Q(public_slug=''),
                name='uniq_repository_thesis_public_slug_per_tenant',
            ),
        ]

    def build_public_slug(self):
        base_slug = slugify(self.title)[:220] or str(self.id)
        candidate = base_slug
        suffix = 2

        while Thesis.objects.filter(
            tenant=self.tenant,
            public_slug=candidate,
        ).exclude(pk=self.pk).exists():
            candidate = f"{base_slug[:210]}-{suffix}"
            suffix += 1

        return candidate

    def save(self, *args, **kwargs):
        if not self.public_slug:
            self.public_slug = self.build_public_slug()
        super().save(*args, **kwargs)
        if hasattr(self, 'id') and self.id:
            # We must use update() since SearchVector is a query expression, not a string value
            Thesis.objects.filter(pk=self.pk).update(
                search_vector=SearchVector('title', weight='A', config='english') + 
                              SearchVector('abstract', weight='B', config='english')
            )

    def __str__(self):
        return self.title

    @property
    def is_embargo_active(self):
        if self.visibility != 'EMBARGOED' or not self.embargo_until:
            return False
        from django.utils import timezone
        return self.embargo_until >= timezone.localdate()

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


class ThesisMetadataVersion(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='thesis_metadata_versions')
    thesis = models.ForeignKey(Thesis, on_delete=models.CASCADE, related_name='metadata_versions')
    version_number = models.PositiveIntegerField(default=1)
    snapshot = models.JSONField(default=dict, blank=True)
    note = models.CharField(max_length=255, blank=True)
    created_by_membership = models.ForeignKey(
        TenantMembership,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='metadata_versions',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-version_number', '-created_at']
        unique_together = ('thesis', 'version_number')

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
    ACCESS_CHOICES = [
        ('PRIVATE', 'Private'),
        ('VIEW_ONLY', 'View Only'),
        ('DOWNLOADABLE', 'Downloadable'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    thesis = models.ForeignKey(Thesis, on_delete=models.CASCADE, related_name='files')
    file_object = models.ForeignKey(FileObject, on_delete=models.CASCADE)
    
    kind = models.CharField(max_length=50, choices=KIND_CHOICES, default='MAIN_PDF')
    access_level = models.CharField(max_length=50, choices=ACCESS_CHOICES, default='DOWNLOADABLE')
    version_number = models.PositiveIntegerField(default=1)
    is_current = models.BooleanField(default=True)
    label = models.CharField(max_length=255, blank=True)
    uploaded_by_membership = models.ForeignKey(TenantMembership, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.kind} for {self.thesis.title}"
