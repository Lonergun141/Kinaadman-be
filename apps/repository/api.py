from collections import Counter
from typing import List, Optional
from uuid import UUID
from django.shortcuts import get_object_or_404
from django.db.models import Case, IntegerField, Prefetch, Q, Value, When
from django.utils import timezone
from ninja import Router

from apps.tenants.models import Tenant
from .analytics import build_repository_analytics_overview
from .readiness import get_publication_blockers
from .models import (
    Department, Keyword, Program, Thesis, ThesisAuthor, ThesisAdviser,
    ThesisKeyword, ThesisMetadataVersion, ThesisReview, ThesisStatusHistory
)
from .schemas import (
    AdviserAssignSchema,
    AuthorAssignSchema,
    CitationExportSchema,
    CollectionBucketSchema,
    DepartmentCreateSchema,
    DepartmentSchema,
    ProgramCreateSchema,
    ProgramSchema,
    PublicCollectionSummarySchema,
    PublicThesisDetailSchema,
    PublicThesisListSchema,
    RepositoryAnalyticsOverviewSchema,
    ThesisArchiveSchema,
    ThesisCreateUpdateSchema,
    ThesisDetailSchema,
    ThesisListSchema,
    ThesisPublishSchema,
    ThesisReviewCreateSchema,
    ThesisReviewStartSchema,
    ThesisSubmitSchema,
)
from apps.users.models import TenantMembership, User
from core.models import AuditLog

# Initialize Routers
departments_router = Router(tags=["Departments"])
programs_router = Router(tags=["Programs"])
theses_router = Router(tags=["Theses"])
analytics_router = Router(tags=["Repository Analytics"])
public_router = Router(tags=["Public Repository"])

# ==========================================
# Helpers
# ==========================================
from ninja.errors import HttpError
from apps.tenants.models import TenantHostAlias
from django.contrib.postgres.search import SearchQuery, SearchRank

REVIEWER_ROLES = {"ADVISER", "LIBRARIAN", "TENANT_ADMIN"}
PUBLISHER_ROLES = {"LIBRARIAN", "TENANT_ADMIN"}

def get_tenant_from_request(request):
    """
    Resolves the tenant context required for data isolation.
    1. Checks for explicit 'X-Tenant-ID' header (useful for API testing/client overrides).
    2. Falls back to resolving the HTTP 'Host' header against `TenantHostAlias`.
    Throws a 400 Bad Request if no tenant can be resolved to prevent data spillage.
    """
    # 1. Check explicit header
    tenant_id = request.headers.get('X-Tenant-ID')
    if tenant_id:
        tenant = Tenant.objects.filter(id=tenant_id, is_active=True).first()
        if tenant:
            return tenant

    # 2. Check Host header (e.g. "tenant.kinaadman.com")
    host = request.headers.get('Host', '').split(':')[0]  # strip port
    alias = TenantHostAlias.objects.filter(hostname=host, is_active=True, tenant__is_active=True).select_related('tenant').first()
    
    if alias:
        return alias.tenant

    raise HttpError(400, "Tenant context could not be resolved from headers.")


def get_public_tenant(tenant_slug: str):
    return get_object_or_404(
        Tenant.objects.select_related("branding", "policy"),
        slug=tenant_slug,
        is_active=True,
    )


def build_thesis_queryset(tenant: Tenant):
    return (
        Thesis.objects.filter(tenant=tenant)
        .select_related("tenant", "department", "program")
        .prefetch_related(
            "authors",
            "advisers__adviser_membership__user",
            Prefetch("thesis_keywords", queryset=ThesisKeyword.objects.select_related("keyword")),
            "status_history__changed_by_membership__user",
            "reviews__reviewer_membership__user",
            "files__file_object",
            "metadata_versions",
        )
    )


def get_membership_or_none(tenant: Tenant, membership_id: Optional[UUID]):
    if not membership_id:
        return None
    return get_object_or_404(TenantMembership, id=membership_id, tenant=tenant)


def require_membership_role(membership: Optional[TenantMembership], allowed_roles: set[str], message: str):
    if not membership or membership.role not in allowed_roles:
        raise HttpError(403, message)


def apply_search(qs, search: Optional[str]):
    if not search or not search.strip():
        return qs.order_by("-published_at", "-year", "title")

    normalized_search = search.strip()
    query = SearchQuery(normalized_search, config="english")
    return (
        qs.annotate(
            rank=SearchRank("search_vector", query),
            title_match=Case(
                When(title__icontains=normalized_search, then=Value(3)),
                default=Value(0),
                output_field=IntegerField(),
            ),
            abstract_match=Case(
                When(abstract__icontains=normalized_search, then=Value(2)),
                default=Value(0),
                output_field=IntegerField(),
            ),
            keyword_match=Case(
                When(thesis_keywords__keyword__value__icontains=normalized_search, then=Value(1)),
                default=Value(0),
                output_field=IntegerField(),
            ),
        )
        .filter(
            Q(search_vector=query)
            | Q(title__icontains=normalized_search)
            | Q(abstract__icontains=normalized_search)
            | Q(thesis_keywords__keyword__value__icontains=normalized_search)
        )
        .distinct()
        .order_by("-title_match", "-abstract_match", "-keyword_match", "-rank", "-published_at", "-year", "title")
    )


def build_public_visibility_filter():
    return Q(visibility="PUBLIC") | Q(visibility="EMBARGOED")


def sync_keywords(tenant: Tenant, thesis: Thesis, values: Optional[List[str]]):
    if values is None:
        return

    normalized_values = []
    seen = set()
    for raw_value in values:
        value = raw_value.strip()
        lowered = value.lower()
        if not value or lowered in seen:
            continue
        seen.add(lowered)
        normalized_values.append(value)

    ThesisKeyword.objects.filter(thesis=thesis, tenant=tenant).exclude(
        keyword__value__in=normalized_values,
    ).delete()

    for keyword_value in normalized_values:
        keyword, _ = Keyword.objects.get_or_create(tenant=tenant, value=keyword_value)
        ThesisKeyword.objects.get_or_create(
            tenant=tenant,
            thesis=thesis,
            keyword=keyword,
        )


def snapshot_thesis(thesis: Thesis):
    return {
        "title": thesis.title,
        "abstract": thesis.abstract,
        "year": thesis.year,
        "status": thesis.status,
        "visibility": thesis.visibility,
        "thesis_type": thesis.thesis_type,
        "language": thesis.language,
        "research_category": thesis.research_category,
        "methodology": thesis.methodology,
        "college_name": thesis.college_name,
        "campus_name": thesis.campus_name,
        "rights_license": thesis.rights_license,
        "public_slug": thesis.public_slug,
        "panel_members": thesis.panel_members,
        "defense_date": thesis.defense_date.isoformat() if thesis.defense_date else None,
        "embargo_until": thesis.embargo_until.isoformat() if thesis.embargo_until else None,
        "department_id": str(thesis.department_id) if thesis.department_id else None,
        "program_id": str(thesis.program_id) if thesis.program_id else None,
        "keywords": [entry.keyword.value for entry in thesis.thesis_keywords.all()],
        "authors": [author.display_name for author in thesis.authors.all()],
        "advisers": [
            adviser.adviser_membership.user.email
            for adviser in thesis.advisers.all()
            if adviser.adviser_membership_id
        ],
    }


def create_metadata_version(tenant: Tenant, thesis: Thesis, membership: Optional[TenantMembership], note: str):
    latest = thesis.metadata_versions.order_by("-version_number").first()
    next_version = latest.version_number + 1 if latest else 1
    ThesisMetadataVersion.objects.create(
        tenant=tenant,
        thesis=thesis,
        version_number=next_version,
        snapshot=snapshot_thesis(thesis),
        note=note,
        created_by_membership=membership,
    )


def create_audit_event(
    tenant: Tenant,
    action: str,
    entity_type: str,
    entity_id,
    actor_membership: Optional[TenantMembership] = None,
    metadata: Optional[dict] = None,
):
    AuditLog.objects.create(
        tenant=tenant,
        actor_membership=actor_membership,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        metadata=metadata or {},
    )


def create_status_transition(
    tenant: Tenant,
    thesis: Thesis,
    from_status: str,
    to_status: str,
    membership: Optional[TenantMembership],
    note: str,
):
    ThesisStatusHistory.objects.create(
        tenant=tenant,
        thesis=thesis,
        from_status=from_status,
        to_status=to_status,
        changed_by_membership=membership,
        note=note,
    )
    create_audit_event(
        tenant=tenant,
        action="thesis.status.changed",
        entity_type="thesis",
        entity_id=thesis.id,
        actor_membership=membership,
        metadata={"from_status": from_status, "to_status": to_status, "note": note},
    )


def update_thesis_from_payload(tenant: Tenant, thesis: Thesis, payload: ThesisCreateUpdateSchema):
    thesis.title = payload.title
    thesis.abstract = payload.abstract
    thesis.year = payload.year
    if payload.visibility is not None:
        thesis.visibility = payload.visibility
    if payload.thesis_type is not None:
        thesis.thesis_type = payload.thesis_type
    if payload.language is not None:
        thesis.language = payload.language
    if payload.research_category is not None:
        thesis.research_category = payload.research_category
    if payload.methodology is not None:
        thesis.methodology = payload.methodology
    if payload.college_name is not None:
        thesis.college_name = payload.college_name
    if payload.campus_name is not None:
        thesis.campus_name = payload.campus_name
    if payload.rights_license is not None:
        thesis.rights_license = payload.rights_license
    if payload.panel_members is not None:
        thesis.panel_members = payload.panel_members
    if payload.panel_approval_status is not None:
        thesis.panel_approval_status = payload.panel_approval_status
    if payload.panel_approval_note is not None:
        thesis.panel_approval_note = payload.panel_approval_note
    if payload.defense_date is not None:
        thesis.defense_date = payload.defense_date
    if payload.embargo_until is not None:
        thesis.embargo_until = payload.embargo_until
    if payload.public_slug is not None:
        thesis.public_slug = payload.public_slug

    thesis.department = (
        get_object_or_404(Department, id=payload.department_id, tenant=tenant)
        if payload.department_id
        else None
    )
    thesis.program = (
        get_object_or_404(Program, id=payload.program_id, tenant=tenant)
        if payload.program_id
        else None
    )


def format_authors_for_citation(thesis: Thesis):
    authors = [author.display_name for author in thesis.authors.all()]
    if not authors:
        return "Unknown author"
    if len(authors) == 1:
        return authors[0]
    if len(authors) == 2:
        return f"{authors[0]} and {authors[1]}"
    return f"{', '.join(authors[:-1])}, and {authors[-1]}"


def build_citation_formats(thesis: Thesis):
    authors = format_authors_for_citation(thesis)
    title = thesis.title
    year = thesis.year
    program = thesis.program.name if thesis.program else "Institutional repository"
    tenant_name = thesis.tenant.branding.display_name if hasattr(thesis.tenant, "branding") else thesis.tenant.name
    url = f"/discover/{thesis.tenant.slug}/theses/{thesis.public_slug}"
    citation_key = thesis.public_slug.replace("-", "_")[:32]

    return {
        "APA": f"{authors} ({year}). {title}. {program}. {tenant_name}. {url}",
        "MLA": f"{authors}. \"{title}.\" {program}, {year}, {tenant_name}, {url}.",
        "Chicago": f"{authors}. \"{title}.\" {program}. {tenant_name}, {year}. {url}.",
        "BIBTEX": (
            f"@thesis{{{citation_key},\n"
            f"  title = {{{title}}},\n"
            f"  author = {{{authors}}},\n"
            f"  year = {{{year}}},\n"
            f"  school = {{{tenant_name}}},\n"
            f"  note = {{{program}}},\n"
            f"  url = {{{url}}}\n"
            f"}}"
        ),
    }


def build_collection_summary(theses: List[Thesis]):
    def to_buckets(counter: Counter):
        return [
            CollectionBucketSchema(value=value, label=value, count=count)
            for value, count in counter.most_common(8)
        ]

    return PublicCollectionSummarySchema(
        thesis_types=to_buckets(Counter(thesis.thesis_type for thesis in theses)),
        departments=to_buckets(Counter(thesis.department.name for thesis in theses if thesis.department_id)),
        programs=to_buckets(Counter(thesis.program.name for thesis in theses if thesis.program_id)),
        years=to_buckets(Counter(str(thesis.year) for thesis in theses)),
    )


def to_public_detail(thesis: Thesis):
    thesis.citation_formats = build_citation_formats(thesis)
    thesis.can_download_public_files = (
        thesis.visibility == "PUBLIC"
        or (thesis.visibility == "EMBARGOED" and not thesis.is_embargo_active)
    )
    thesis.public_files = (
        [
            thesis_file
            for thesis_file in thesis.files.all()
            if thesis_file.is_current and thesis_file.access_level != "PRIVATE"
        ]
        if thesis.can_download_public_files
        else []
    )
    return thesis


# ==========================================
# Departments Router
# ==========================================
@departments_router.get("/", response=List[DepartmentSchema])
def list_departments(request):
    """
    List Departments
    
    Retrieve a list of all active departments within your tenant organization.
    """
    tenant = get_tenant_from_request(request)
    return Department.objects.filter(tenant=tenant)

@departments_router.post("/", response=DepartmentSchema)
def create_department(request, payload: DepartmentCreateSchema):
    """
    Create Department
    
    Register a new academic department within the current tenant organization.
    """
    tenant = get_tenant_from_request(request)
    dept = Department.objects.create(tenant=tenant, **payload.dict())
    return dept

@departments_router.get("/{dept_id}", response=DepartmentSchema)
def get_department(request, dept_id: UUID):
    """
    Retrieve Department
    
    Fetch the details of a specific department by its unique primary key.
    """
    tenant = get_tenant_from_request(request)
    return get_object_or_404(Department, id=dept_id, tenant=tenant)

@departments_router.put("/{dept_id}", response=DepartmentSchema)
def update_department(request, dept_id: UUID, payload: DepartmentCreateSchema):
    """
    Update Department
    
    Modify the details of an existing academic department.
    """
    tenant = get_tenant_from_request(request)
    dept = get_object_or_404(Department, id=dept_id, tenant=tenant)
    for attr, value in payload.dict().items():
        setattr(dept, attr, value)
    dept.save()
    return dept

@departments_router.delete("/{dept_id}")
def delete_department(request, dept_id: UUID):
    """
    Delete Department
    
    Permanently remove a department from the tenant organization.
    """
    tenant = get_tenant_from_request(request)
    dept = get_object_or_404(Department, id=dept_id, tenant=tenant)
    dept.delete()
    return {"success": True}

@departments_router.get("/{dept_id}/programs/", response=List[ProgramSchema])
def list_department_programs(request, dept_id: UUID):
    """
    List Department Programs
    
    List all academic programs that fall under a specific department.
    """
    tenant = get_tenant_from_request(request)
    dept = get_object_or_404(Department, id=dept_id, tenant=tenant)
    return Program.objects.filter(department=dept, tenant=tenant)


# ==========================================
# Programs Router
# ==========================================
@programs_router.get("/", response=List[ProgramSchema])
def list_programs(request):
    """
    List Programs
    
    Retrieve a list of all programs available across the entire tenant organization.
    """
    tenant = get_tenant_from_request(request)
    return Program.objects.filter(tenant=tenant)

@programs_router.post("/", response=ProgramSchema)
def create_program(request, payload: ProgramCreateSchema):
    """
    Create Program
    
    Add a new academic program and associate it with an existing department.
    """
    tenant = get_tenant_from_request(request)
    dept = get_object_or_404(Department, id=payload.department_id, tenant=tenant)
    program = Program.objects.create(
        tenant=tenant, 
        department=dept,
        name=payload.name
    )
    return program

@programs_router.get("/{program_id}", response=ProgramSchema)
def get_program(request, program_id: UUID):
    """
    Retrieve Program
    
    Fetch the details of a specific program by its unique primary key.
    """
    tenant = get_tenant_from_request(request)
    return get_object_or_404(Program, id=program_id, tenant=tenant)

@programs_router.put("/{program_id}", response=ProgramSchema)
def update_program(request, program_id: UUID, payload: ProgramCreateSchema):
    """
    Update Program
    
    Modify an existing academic program or change its associated department.
    """
    tenant = get_tenant_from_request(request)
    program = get_object_or_404(Program, id=program_id, tenant=tenant)
    
    if payload.department_id != program.department_id:
        program.department = get_object_or_404(Department, id=payload.department_id, tenant=tenant)
    
    program.name = payload.name
    program.save()
    return program

@programs_router.delete("/{program_id}")
def delete_program(request, program_id: UUID):
    """
    Delete Program
    
    Permanently delete an academic program.
    """
    tenant = get_tenant_from_request(request)
    program = get_object_or_404(Program, id=program_id, tenant=tenant)
    program.delete()
    return {"success": True}


# ==========================================
# Theses Router
# ==========================================
@analytics_router.get("/repository/overview", response=RepositoryAnalyticsOverviewSchema)
def repository_analytics_overview(
    request,
    months: int = 6,
    department_id: Optional[UUID] = None,
):
    tenant = get_tenant_from_request(request)
    qs = build_thesis_queryset(tenant)

    if department_id:
        get_object_or_404(Department, id=department_id, tenant=tenant)
        qs = qs.filter(department_id=department_id)

    return build_repository_analytics_overview(qs, month_count=months)


@theses_router.get("/", response=List[ThesisListSchema])
def list_theses(
    request,
    search: Optional[str] = None,
    status: Optional[str] = None,
    visibility: Optional[str] = None,
    thesis_type: Optional[str] = None,
    department_id: Optional[UUID] = None,
    program_id: Optional[UUID] = None,
    year: Optional[int] = None,
    keyword: Optional[str] = None,
    author_user_id: Optional[UUID] = None,
):
    tenant = get_tenant_from_request(request)
    qs = build_thesis_queryset(tenant)

    if author_user_id:
        qs = qs.filter(authors__user_id=author_user_id).distinct()
    if status:
        qs = qs.filter(status=status)
    if visibility:
        qs = qs.filter(visibility=visibility)
    if thesis_type:
        qs = qs.filter(thesis_type=thesis_type)
    if department_id:
        qs = qs.filter(department_id=department_id)
    if program_id:
        qs = qs.filter(program_id=program_id)
    if year:
        qs = qs.filter(year=year)
    if keyword:
        qs = qs.filter(thesis_keywords__keyword__value__icontains=keyword).distinct()

    return apply_search(qs, search)


@theses_router.post("/", response=ThesisDetailSchema)
def create_thesis(request, payload: ThesisCreateUpdateSchema):
    tenant = get_tenant_from_request(request)
    actor_membership = get_membership_or_none(
        tenant,
        payload.actor_membership_id or payload.created_by_membership_id,
    )

    thesis = Thesis(
        tenant=tenant,
        created_by_membership=actor_membership,
        status="DRAFT",
    )
    update_thesis_from_payload(tenant, thesis, payload)
    thesis.save()
    sync_keywords(tenant, thesis, payload.keywords)
    create_status_transition(tenant, thesis, "", "DRAFT", actor_membership, "Draft created")
    create_metadata_version(tenant, thesis, actor_membership, "Initial draft created")
    create_audit_event(
        tenant=tenant,
        action="thesis.created",
        entity_type="thesis",
        entity_id=thesis.id,
        actor_membership=actor_membership,
        metadata={
            "status": thesis.status,
            "visibility": thesis.visibility,
            "thesis_type": thesis.thesis_type,
        },
    )
    return get_object_or_404(build_thesis_queryset(tenant), id=thesis.id)


@theses_router.get("/{thesis_id}", response=ThesisDetailSchema)
def get_thesis(request, thesis_id: UUID):
    tenant = get_tenant_from_request(request)
    return get_object_or_404(build_thesis_queryset(tenant), id=thesis_id)


@theses_router.put("/{thesis_id}", response=ThesisDetailSchema)
def update_thesis(request, thesis_id: UUID, payload: ThesisCreateUpdateSchema):
    tenant = get_tenant_from_request(request)
    thesis = get_object_or_404(build_thesis_queryset(tenant), id=thesis_id)
    actor_membership = get_membership_or_none(tenant, payload.actor_membership_id)

    update_thesis_from_payload(tenant, thesis, payload)
    thesis.save()
    sync_keywords(tenant, thesis, payload.keywords)
    create_metadata_version(tenant, thesis, actor_membership, "Metadata updated")
    create_audit_event(
        tenant=tenant,
        action="thesis.metadata.updated",
        entity_type="thesis",
        entity_id=thesis.id,
        actor_membership=actor_membership,
    )
    return get_object_or_404(build_thesis_queryset(tenant), id=thesis.id)


@theses_router.delete("/{thesis_id}")
def delete_thesis(request, thesis_id: UUID):
    tenant = get_tenant_from_request(request)
    thesis = get_object_or_404(Thesis, id=thesis_id, tenant=tenant)
    create_audit_event(
        tenant=tenant,
        action="thesis.deleted",
        entity_type="thesis",
        entity_id=thesis.id,
    )
    thesis.delete()
    return {"success": True}


@theses_router.post("/{thesis_id}/submit", response=ThesisDetailSchema)
def submit_thesis(request, thesis_id: UUID, payload: ThesisSubmitSchema):
    tenant = get_tenant_from_request(request)
    thesis = get_object_or_404(build_thesis_queryset(tenant), id=thesis_id)

    if thesis.status not in {"DRAFT", "CHANGES_REQUESTED"}:
        raise HttpError(400, "Only drafts and returned records can be submitted.")

    membership = get_membership_or_none(tenant, payload.submitter_membership_id)
    old_status = thesis.status
    thesis.status = "SUBMITTED"
    thesis.submitted_at = timezone.now()
    thesis.save(update_fields=["status", "submitted_at", "updated_at"])
    create_status_transition(
        tenant,
        thesis,
        old_status,
        "SUBMITTED",
        membership,
        payload.note or "Submitted for review",
    )
    create_metadata_version(tenant, thesis, membership, "Submitted for review")
    return get_object_or_404(build_thesis_queryset(tenant), id=thesis.id)


@theses_router.post("/{thesis_id}/start-review", response=ThesisDetailSchema)
def start_review(request, thesis_id: UUID, payload: ThesisReviewStartSchema):
    tenant = get_tenant_from_request(request)
    thesis = get_object_or_404(build_thesis_queryset(tenant), id=thesis_id)
    reviewer = get_object_or_404(TenantMembership, id=payload.reviewer_membership_id, tenant=tenant)
    require_membership_role(reviewer, REVIEWER_ROLES, "You do not have permission to start a review.")

    if thesis.status != "SUBMITTED":
        raise HttpError(400, "Only submitted records can move into review.")

    old_status = thesis.status
    thesis.status = "IN_REVIEW"
    thesis.save(update_fields=["status", "updated_at"])
    create_status_transition(tenant, thesis, old_status, "IN_REVIEW", reviewer, payload.note or "Review started")
    create_metadata_version(tenant, thesis, reviewer, "Review started")
    return get_object_or_404(build_thesis_queryset(tenant), id=thesis.id)


@theses_router.post("/{thesis_id}/review", response=ThesisDetailSchema)
def review_thesis(request, thesis_id: UUID, payload: ThesisReviewCreateSchema):
    tenant = get_tenant_from_request(request)
    thesis = get_object_or_404(build_thesis_queryset(tenant), id=thesis_id)
    reviewer = get_object_or_404(TenantMembership, id=payload.reviewer_membership_id, tenant=tenant)
    require_membership_role(reviewer, REVIEWER_ROLES, "You do not have permission to review this record.")

    if thesis.status not in {"SUBMITTED", "IN_REVIEW"}:
        raise HttpError(400, "This record is not currently reviewable.")

    decision = payload.decision.upper()
    if decision not in {"APPROVED", "CHANGES_REQUESTED", "REJECTED"}:
        raise HttpError(400, "Invalid review decision.")

    ThesisReview.objects.create(
        tenant=tenant,
        thesis=thesis,
        reviewer_membership=reviewer,
        decision=decision,
        comment=payload.comment,
    )

    old_status = thesis.status
    if decision == "APPROVED":
        thesis.status = "APPROVED"
        thesis.approved_at = timezone.now()
        note = payload.comment or "Approved for publication"
        thesis.save(update_fields=["status", "approved_at", "updated_at"])
    elif decision == "CHANGES_REQUESTED":
        thesis.status = "CHANGES_REQUESTED"
        note = payload.comment or "Revisions requested"
        thesis.save(update_fields=["status", "updated_at"])
    else:
        thesis.status = "ARCHIVED"
        note = payload.comment or "Rejected and archived"
        thesis.save(update_fields=["status", "updated_at"])

    create_status_transition(tenant, thesis, old_status, thesis.status, reviewer, note)
    create_metadata_version(tenant, thesis, reviewer, f"Review decision: {decision}")
    create_audit_event(
        tenant=tenant,
        action="thesis.review.recorded",
        entity_type="thesis",
        entity_id=thesis.id,
        actor_membership=reviewer,
        metadata={"decision": decision, "comment": payload.comment or ""},
    )
    return get_object_or_404(build_thesis_queryset(tenant), id=thesis.id)


@theses_router.post("/{thesis_id}/publish", response=ThesisDetailSchema)
def publish_thesis(request, thesis_id: UUID, payload: ThesisPublishSchema):
    tenant = get_tenant_from_request(request)
    thesis = get_object_or_404(build_thesis_queryset(tenant), id=thesis_id)
    actor_membership = get_membership_or_none(tenant, payload.actor_membership_id)
    require_membership_role(actor_membership, PUBLISHER_ROLES, "You do not have permission to publish records.")

    if thesis.status != "APPROVED":
        raise HttpError(400, "Only approved records can be published.")

    blockers = get_publication_blockers(thesis)
    if blockers:
        raise HttpError(
            400,
            "This thesis is not ready for publishing yet. Complete the following first: "
            + ", ".join(blockers),
        )

    old_status = thesis.status
    thesis.status = "PUBLISHED"
    thesis.published_at = timezone.now()
    thesis.save(update_fields=["status", "published_at", "updated_at"])
    create_status_transition(
        tenant,
        thesis,
        old_status,
        "PUBLISHED",
        actor_membership,
        payload.note or "Published to the repository",
    )
    create_metadata_version(tenant, thesis, actor_membership, "Published to the repository")
    return get_object_or_404(build_thesis_queryset(tenant), id=thesis.id)


@theses_router.post("/{thesis_id}/unpublish", response=ThesisDetailSchema)
def unpublish_thesis(request, thesis_id: UUID, payload: ThesisPublishSchema):
    tenant = get_tenant_from_request(request)
    thesis = get_object_or_404(build_thesis_queryset(tenant), id=thesis_id)
    actor_membership = get_membership_or_none(tenant, payload.actor_membership_id)
    require_membership_role(actor_membership, PUBLISHER_ROLES, "You do not have permission to unpublish records.")

    if thesis.status != "PUBLISHED":
        raise HttpError(400, "Only published records can be unpublished.")

    old_status = thesis.status
    thesis.status = "APPROVED"
    thesis.save(update_fields=["status", "updated_at"])
    create_status_transition(
        tenant,
        thesis,
        old_status,
        "APPROVED",
        actor_membership,
        payload.note or "Returned to approved state",
    )
    create_metadata_version(tenant, thesis, actor_membership, "Unpublished")
    return get_object_or_404(build_thesis_queryset(tenant), id=thesis.id)


@theses_router.post("/{thesis_id}/archive", response=ThesisDetailSchema)
def archive_thesis(request, thesis_id: UUID, payload: ThesisArchiveSchema):
    tenant = get_tenant_from_request(request)
    thesis = get_object_or_404(build_thesis_queryset(tenant), id=thesis_id)
    actor_membership = get_membership_or_none(tenant, payload.actor_membership_id)
    require_membership_role(actor_membership, PUBLISHER_ROLES, "You do not have permission to archive records.")

    if thesis.status == "ARCHIVED":
        raise HttpError(400, "This record is already archived.")

    old_status = thesis.status
    thesis.status = "ARCHIVED"
    thesis.save(update_fields=["status", "updated_at"])
    create_status_transition(
        tenant,
        thesis,
        old_status,
        "ARCHIVED",
        actor_membership,
        payload.note or "Archived from the active repository",
    )
    create_metadata_version(tenant, thesis, actor_membership, "Archived")
    return get_object_or_404(build_thesis_queryset(tenant), id=thesis.id)


@theses_router.post("/{thesis_id}/authors", response=ThesisDetailSchema)
def assign_author(request, thesis_id: UUID, payload: AuthorAssignSchema):
    tenant = get_tenant_from_request(request)
    thesis = get_object_or_404(build_thesis_queryset(tenant), id=thesis_id)
    user = get_object_or_404(User, id=payload.user_id) if payload.user_id else None

    ThesisAuthor.objects.create(
        tenant=tenant,
        thesis=thesis,
        user=user,
        display_name=payload.display_name,
        sort_order=payload.sort_order,
    )
    create_audit_event(
        tenant=tenant,
        action="thesis.author.assigned",
        entity_type="thesis",
        entity_id=thesis.id,
        metadata={"display_name": payload.display_name, "user_id": str(payload.user_id) if payload.user_id else None},
    )
    create_metadata_version(tenant, thesis, None, "Author list updated")
    return get_object_or_404(build_thesis_queryset(tenant), id=thesis.id)


@theses_router.post("/{thesis_id}/advisers", response=ThesisDetailSchema)
def assign_adviser(request, thesis_id: UUID, payload: AdviserAssignSchema):
    tenant = get_tenant_from_request(request)
    thesis = get_object_or_404(build_thesis_queryset(tenant), id=thesis_id)
    membership = get_object_or_404(TenantMembership, id=payload.adviser_membership_id, tenant=tenant)

    ThesisAdviser.objects.get_or_create(
        tenant=tenant,
        thesis=thesis,
        adviser_membership=membership,
    )
    create_audit_event(
        tenant=tenant,
        action="thesis.adviser.assigned",
        entity_type="thesis",
        entity_id=thesis.id,
        metadata={"adviser_membership_id": str(payload.adviser_membership_id)},
    )
    create_metadata_version(tenant, thesis, membership, "Adviser list updated")
    return get_object_or_404(build_thesis_queryset(tenant), id=thesis.id)


@public_router.get("/tenants/{tenant_slug}/theses/", response=List[PublicThesisListSchema])
def list_public_theses(
    request,
    tenant_slug: str,
    search: Optional[str] = None,
    thesis_type: Optional[str] = None,
    department: Optional[str] = None,
    program: Optional[str] = None,
    year: Optional[int] = None,
    keyword: Optional[str] = None,
):
    tenant = get_public_tenant(tenant_slug)
    qs = build_thesis_queryset(tenant).filter(
        build_public_visibility_filter(),
        status__in=["PUBLISHED", "ARCHIVED"],
    )

    if thesis_type:
        qs = qs.filter(thesis_type=thesis_type)
    if department:
        qs = qs.filter(department__name__icontains=department)
    if program:
        qs = qs.filter(program__name__icontains=program)
    if year:
        qs = qs.filter(year=year)
    if keyword:
        qs = qs.filter(thesis_keywords__keyword__value__icontains=keyword).distinct()

    return apply_search(qs, search)


@public_router.get("/tenants/{tenant_slug}/collections/", response=PublicCollectionSummarySchema)
def public_collections(request, tenant_slug: str):
    tenant = get_public_tenant(tenant_slug)
    theses = list(
        build_thesis_queryset(tenant).filter(
            build_public_visibility_filter(),
            status__in=["PUBLISHED", "ARCHIVED"],
        )
    )
    return build_collection_summary(theses)


@public_router.get("/tenants/{tenant_slug}/theses/{public_slug}/", response=PublicThesisDetailSchema)
def public_thesis_detail(request, tenant_slug: str, public_slug: str):
    tenant = get_public_tenant(tenant_slug)
    thesis = get_object_or_404(
        build_thesis_queryset(tenant).filter(
            build_public_visibility_filter(),
            status__in=["PUBLISHED", "ARCHIVED"],
        ),
        public_slug=public_slug,
    )
    return to_public_detail(thesis)


@public_router.get("/tenants/{tenant_slug}/theses/{public_slug}/citation/", response=List[CitationExportSchema])
def public_thesis_citations(request, tenant_slug: str, public_slug: str):
    tenant = get_public_tenant(tenant_slug)
    thesis = get_object_or_404(
        build_thesis_queryset(tenant).filter(
            build_public_visibility_filter(),
            status__in=["PUBLISHED", "ARCHIVED"],
        ),
        public_slug=public_slug,
    )
    citation_formats = build_citation_formats(thesis)
    base_filename = thesis.public_slug or thesis.build_public_slug()
    return [
        CitationExportSchema(format="APA", filename=f"{base_filename}-apa.txt", content=citation_formats["APA"]),
        CitationExportSchema(format="MLA", filename=f"{base_filename}-mla.txt", content=citation_formats["MLA"]),
        CitationExportSchema(format="Chicago", filename=f"{base_filename}-chicago.txt", content=citation_formats["Chicago"]),
        CitationExportSchema(format="BibTeX", filename=f"{base_filename}.bib", content=citation_formats["BIBTEX"]),
    ]
