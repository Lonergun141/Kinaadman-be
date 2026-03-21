from datetime import date, datetime
from datetime import date
from typing import Any, Dict, List, Optional
from uuid import UUID
from ninja import Schema, ModelSchema

from .models import (
    Department, Program, Thesis, ThesisStatusHistory, ThesisReview,
    ThesisAuthor, ThesisAdviser, Keyword, ThesisFile, ThesisMetadataVersion
)


# ==========================================
# Departments
# ==========================================
class DepartmentSchema(ModelSchema):
    class Meta:
        model = Department
        fields = ['id', 'name', 'is_active']

class DepartmentCreateSchema(Schema):
    name: str


# ==========================================
# Programs
# ==========================================
class ProgramSchema(ModelSchema):
    department_id: UUID

    class Meta:
        model = Program
        fields = ['id', 'name', 'is_active']

class ProgramCreateSchema(Schema):
    name: str
    department_id: UUID


# ==========================================
# Theses - Support Entities
# ==========================================
class ThesisAuthorSchema(ModelSchema):
    class Meta:
        model = ThesisAuthor
        fields = ['id', 'display_name', 'sort_order']

class ThesisAdviserSchema(ModelSchema):
    adviser_email: str

    @staticmethod
    def resolve_adviser_email(obj):
        return obj.adviser_membership.user.email if obj.adviser_membership else None

    class Meta:
        model = ThesisAdviser
        fields = ['id']

class KeywordSchema(ModelSchema):
    class Meta:
        model = Keyword
        fields = ['id', 'value']

class ThesisStatusHistorySchema(ModelSchema):
    changed_by_email: Optional[str] = None
    changed_by_role: Optional[str] = None

    @staticmethod
    def resolve_changed_by_email(obj):
        if not obj.changed_by_membership:
            return None
        return obj.changed_by_membership.user.email

    @staticmethod
    def resolve_changed_by_role(obj):
        if not obj.changed_by_membership:
            return None
        return obj.changed_by_membership.role

    class Meta:
        model = ThesisStatusHistory
        fields = ['id', 'from_status', 'to_status', 'note', 'changed_at']

class ThesisReviewSchema(ModelSchema):
    reviewer_email: Optional[str] = None
    reviewer_role: Optional[str] = None

    @staticmethod
    def resolve_reviewer_email(obj):
        return obj.reviewer_membership.user.email if obj.reviewer_membership else None

    @staticmethod
    def resolve_reviewer_role(obj):
        return obj.reviewer_membership.role if obj.reviewer_membership else None

    class Meta:
        model = ThesisReview
        fields = ['id', 'decision', 'comment', 'created_at']

class ThesisFileSchema(ModelSchema):
    filename: Optional[str] = None
    content_type: Optional[str] = None
    size_bytes: Optional[int] = None
    checksum: Optional[str] = None

    @staticmethod
    def resolve_filename(obj):
        return obj.file_object.filename if obj.file_object else None

    @staticmethod
    def resolve_content_type(obj):
        return obj.file_object.content_type if obj.file_object else None

    @staticmethod
    def resolve_size_bytes(obj):
        return obj.file_object.size_bytes if obj.file_object else None

    @staticmethod
    def resolve_checksum(obj):
        return obj.file_object.checksum if obj.file_object else None

    class Meta:
        model = ThesisFile
        fields = ['id', 'kind', 'access_level', 'version_number', 'is_current', 'label', 'created_at']

class ThesisMetadataVersionSchema(ModelSchema):
    class Meta:
        model = ThesisMetadataVersion
        fields = ['id', 'version_number', 'snapshot', 'note', 'created_at']

class CitationExportSchema(Schema):
    format: str
    filename: str
    content: str

class CollectionBucketSchema(Schema):
    value: str
    label: str
    count: int

class PublicCollectionSummarySchema(Schema):
    thesis_types: List[CollectionBucketSchema]
    departments: List[CollectionBucketSchema]
    programs: List[CollectionBucketSchema]
    years: List[CollectionBucketSchema]


# ==========================================
# Theses
# ==========================================
class ThesisListSchema(ModelSchema):
    department: Optional[DepartmentSchema] = None
    program: Optional[ProgramSchema] = None
    authors: List[ThesisAuthorSchema] = []
    keywords: List[KeywordSchema] = []

    @staticmethod
    def resolve_keywords(obj):
        thesis_keywords = getattr(obj, 'thesis_keywords', None)
        if thesis_keywords is None:
            return []
        return [entry.keyword for entry in thesis_keywords.all()]
    
    class Meta:
        model = Thesis
        fields = [
            'id',
            'title',
            'year',
            'status',
            'visibility',
            'thesis_type',
            'language',
            'research_category',
            'methodology',
            'college_name',
            'campus_name',
            'public_slug',
            'submitted_at',
            'approved_at',
            'published_at',
            'defense_date',
            'embargo_until',
            'created_at',
            'updated_at',
        ]

class ThesisDetailSchema(ModelSchema):
    department: Optional[DepartmentSchema] = None
    program: Optional[ProgramSchema] = None
    authors: List[ThesisAuthorSchema] = []
    advisers: List[ThesisAdviserSchema] = []
    keywords: List[KeywordSchema] = []
    status_history: List[ThesisStatusHistorySchema] = []
    reviews: List[ThesisReviewSchema] = []
    files: List[ThesisFileSchema] = []
    metadata_versions: List[ThesisMetadataVersionSchema] = []
    is_embargo_active: bool = False

    @staticmethod
    def resolve_keywords(obj):
        thesis_keywords = getattr(obj, 'thesis_keywords', None)
        if thesis_keywords is None:
            return []
        return [entry.keyword for entry in thesis_keywords.all()]
    
    class Meta:
        model = Thesis
        fields = [
            'id',
            'title',
            'abstract',
            'year',
            'status',
            'visibility',
            'thesis_type',
            'language',
            'research_category',
            'methodology',
            'college_name',
            'campus_name',
            'rights_license',
            'panel_members',
            'public_slug',
            'submitted_at',
            'approved_at',
            'published_at',
            'defense_date',
            'embargo_until',
            'created_at',
            'updated_at',
        ]

class ThesisCreateUpdateSchema(Schema):
    title: str
    abstract: str
    year: int
    department_id: Optional[UUID] = None
    program_id: Optional[UUID] = None
    created_by_membership_id: Optional[UUID] = None
    visibility: Optional[str] = None
    thesis_type: Optional[str] = None
    language: Optional[str] = None
    research_category: Optional[str] = None
    methodology: Optional[str] = None
    college_name: Optional[str] = None
    campus_name: Optional[str] = None
    rights_license: Optional[str] = None
    panel_members: Optional[List[str]] = None
    keywords: Optional[List[str]] = None
    defense_date: Optional[date] = None
    embargo_until: Optional[date] = None
    public_slug: Optional[str] = None
    actor_membership_id: Optional[UUID] = None

class ThesisSubmitSchema(Schema):
    submitter_membership_id: Optional[UUID] = None
    note: Optional[str] = "Submitted for review"

class ThesisReviewCreateSchema(Schema):
    decision: str
    comment: Optional[str] = ""
    reviewer_membership_id: UUID

class ThesisReviewStartSchema(Schema):
    reviewer_membership_id: UUID
    note: Optional[str] = "Review started"

class ThesisPublishSchema(Schema):
    actor_membership_id: Optional[UUID] = None
    note: Optional[str] = ""

class ThesisArchiveSchema(Schema):
    actor_membership_id: Optional[UUID] = None
    note: Optional[str] = "Archived from the active repository"

class AuthorAssignSchema(Schema):
    display_name: str
    user_id: Optional[UUID] = None
    sort_order: int = 0

class AdviserAssignSchema(Schema):
    adviser_membership_id: UUID

class PublicThesisListSchema(ThesisListSchema):
    tenant_slug: str
    tenant_name: str
    public_url: str

    @staticmethod
    def resolve_tenant_slug(obj):
        return obj.tenant.slug

    @staticmethod
    def resolve_tenant_name(obj):
        return obj.tenant.branding.display_name if hasattr(obj.tenant, 'branding') else obj.tenant.name

    @staticmethod
    def resolve_public_url(obj):
        return f"/discover/{obj.tenant.slug}/theses/{obj.public_slug}"

class PublicThesisDetailSchema(ThesisDetailSchema):
    tenant_slug: str
    tenant_name: str
    public_url: str
    citation_formats: Dict[str, str]
    can_download_public_files: bool

    @staticmethod
    def resolve_tenant_slug(obj):
        return obj.tenant.slug

    @staticmethod
    def resolve_tenant_name(obj):
        return obj.tenant.branding.display_name if hasattr(obj.tenant, 'branding') else obj.tenant.name

    @staticmethod
    def resolve_public_url(obj):
        return f"/discover/{obj.tenant.slug}/theses/{obj.public_slug}"

    @staticmethod
    def resolve_citation_formats(obj):
        return getattr(obj, 'citation_formats', {})

    @staticmethod
    def resolve_can_download_public_files(obj):
        return getattr(obj, 'can_download_public_files', False)

    @staticmethod
    def resolve_files(obj):
        return getattr(obj, 'public_files', [])

    @staticmethod
    def resolve_status_history(obj):
        return []

    @staticmethod
    def resolve_reviews(obj):
        return []

    @staticmethod
    def resolve_metadata_versions(obj):
        return []

