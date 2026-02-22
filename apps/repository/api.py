from typing import List
from uuid import UUID
from django.shortcuts import get_object_or_404
from ninja import Router

from apps.tenants.models import Tenant
from .models import (
    Department, Program, Thesis, ThesisAuthor, ThesisAdviser, 
    ThesisStatusHistory, ThesisReview
)
from .schemas import (
    DepartmentSchema, DepartmentCreateSchema,
    ProgramSchema, ProgramCreateSchema,
    ThesisListSchema, ThesisDetailSchema, ThesisCreateUpdateSchema,
    ThesisSubmitSchema, ThesisReviewCreateSchema,
    AuthorAssignSchema, AdviserAssignSchema
)

# Initialize Routers
departments_router = Router(tags=["Departments"])
programs_router = Router(tags=["Programs"])
theses_router = Router(tags=["Theses"])

# ==========================================
# Helpers
# ==========================================
from ninja.errors import HttpError
from apps.tenants.models import TenantHostAlias

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
from django.contrib.postgres.search import SearchQuery, SearchRank

@theses_router.get("/", response=List[ThesisListSchema])
def list_theses(request, search: str = None, status: str = None):
    """
    ## Browse and Search Theses
    
    Query the thesis repository. Supports optional filtering by `status` and `search` (Full Text Search).

    ---

    ### **Frontend Integration: Full Text Search**
    This endpoint supports powerful native PostgreSQL Full Text Search (FTS). It uses linguistic root lexemes (e.g. searching 'networking' will intelligently match 'network') and it automatically ranks your results by relevance.

    ### 💻 Next.js Integration Example

    ```javascript
    import { useEffect, useState } from 'react';

    export default function SearchTheses() {
      const [results, setResults] = useState([]);
      const [query, setQuery] = useState('network'); // Sample search term
      const tenantId = '3fec168e-2c39-46f3-8734-462d8562d9d7'; // Sample Tenant ID

      useEffect(() => {
        const fetchTheses = async () => {
          const res = await fetch(`http://127.0.0.1:8000/v1/theses/?search=${encodeURIComponent(query)}`, {
            headers: { "X-Tenant-ID": tenantId }
          });
          const data = await res.json();
          // Backend automatically ranks and orders 'data' by FTS relevance!
          setResults(data); 
        };
        fetchTheses();
      }, [query]);

      return (
        <div>
          {results.map(t => (
            <div key={t.id}>
              <h3>{t.title}</h3>
              <p>{t.abstract}</p>
            </div>
          ))}
        </div>
      );
    }
    ```
    """
    tenant = get_tenant_from_request(request)
    qs = Thesis.objects.filter(tenant=tenant).select_related('department', 'program')
    
    if search:
        query = SearchQuery(search, config='english')
        qs = qs.filter(search_vector=query).annotate(
            rank=SearchRank('search_vector', query)
        ).order_by('-rank', '-year')
    elif not search:
        # Default fallback ordering when not searching
        qs = qs.order_by('-year')

    if status:
        qs = qs.filter(status=status)
        
    return qs

@theses_router.post("/", response=ThesisDetailSchema)
def create_thesis(request, payload: ThesisCreateUpdateSchema):
    """
    Create Thesis
    
    Submit a new thesis into the repository as a Draft.
    """
    tenant = get_tenant_from_request(request)
    
    dept = None
    if payload.department_id:
         dept = get_object_or_404(Department, id=payload.department_id, tenant=tenant)
         
    prog = None
    if payload.program_id:
         prog = get_object_or_404(Program, id=payload.program_id, tenant=tenant)

    thesis = Thesis.objects.create(
        tenant=tenant,
        title=payload.title,
        abstract=payload.abstract,
        year=payload.year,
        department=dept,
        program=prog,
        status='DRAFT'
    )
    # Pre-fetch for the schema
    thesis.authors_list = []
    thesis.advisers_list = []
    return thesis

@theses_router.get("/{thesis_id}", response=ThesisDetailSchema)
def get_thesis(request, thesis_id: UUID):
    """
    Retrieve Thesis
    
    Get the full, detailed record of a single thesis. Includes joined authors, 
    advisers, keywords, and file attachments.
    """
    tenant = get_tenant_from_request(request)
    thesis = get_object_or_404(
        Thesis.objects.select_related('department', 'program')
        .prefetch_related('authors', 'advisers__adviser_membership__user'), 
        id=thesis_id, 
        tenant=tenant
    )
    # Map pre-fetched relations onto the object for the Ninja Schema resolver
    thesis.authors_list = list(thesis.authors.all())
    thesis.advisers_list = list(thesis.advisers.all())
    return thesis

@theses_router.put("/{thesis_id}", response=ThesisDetailSchema)
def update_thesis(request, thesis_id: UUID, payload: ThesisCreateUpdateSchema):
    """
    Update Thesis
    
    Modify the metadata (title, abstract, year, affiliations) of an existing thesis.
    """
    tenant = get_tenant_from_request(request)
    thesis = get_object_or_404(Thesis, id=thesis_id, tenant=tenant)
    
    thesis.title = payload.title
    thesis.abstract = payload.abstract
    thesis.year = payload.year
    
    if payload.department_id:
        thesis.department = get_object_or_404(Department, id=payload.department_id, tenant=tenant)
    if payload.program_id:
        thesis.program = get_object_or_404(Program, id=payload.program_id, tenant=tenant)
        
    thesis.save()
    
    # Reload with relations for the standard response
    return get_thesis(request, thesis_id)

@theses_router.delete("/{thesis_id}")
def delete_thesis(request, thesis_id: UUID):
    """
    Delete Thesis
    
    Permanently remove a thesis record and its associated data from the repository.
    """
    tenant = get_tenant_from_request(request)
    thesis = get_object_or_404(Thesis, id=thesis_id, tenant=tenant)
    thesis.delete()
    return {"success": True}

# ==========================================
# Thesis Workflows (Submit & Review)
# ==========================================
from django.utils import timezone
from apps.users.models import TenantMembership

@theses_router.post("/{thesis_id}/submit", response=ThesisDetailSchema)
def submit_thesis(request, thesis_id: UUID, payload: ThesisSubmitSchema):
    """
    Submit Thesis for Review
    
    Moves a thesis from 'DRAFT' or 'CHANGES_REQUESTED' into 'SUBMITTED' status.
    Generates a history log of the transition.
    """
    tenant = get_tenant_from_request(request)
    thesis = get_object_or_404(
        Thesis.objects.select_related('department', 'program').prefetch_related('authors', 'advisers__adviser_membership__user'), 
        id=thesis_id, 
        tenant=tenant
    )
    
    if thesis.status not in ['DRAFT', 'CHANGES_REQUESTED']:
        raise HttpError(400, "Only drafts or returned theses can be submitted.")

    old_status = thesis.status
    thesis.status = 'SUBMITTED'
    thesis.submitted_at = timezone.now()
    thesis.save()

    # Resolve submitting user
    membership = None
    if payload.submitter_membership_id:
        membership = TenantMembership.objects.filter(id=payload.submitter_membership_id, tenant=tenant).first()

    # Log History
    ThesisStatusHistory.objects.create(
        tenant=tenant,
        thesis=thesis,
        from_status=old_status,
        to_status='SUBMITTED',
        changed_by_membership=membership,
        note=payload.note or "Submitted for review"
    )

    thesis.authors_list = list(thesis.authors.all())
    thesis.advisers_list = list(thesis.advisers.all())
    return thesis

@theses_router.post("/{thesis_id}/review", response=ThesisDetailSchema)
def review_thesis(request, thesis_id: UUID, payload: ThesisReviewCreateSchema):
    """
    Review Thesis
    
    As an adviser or librarian, record a decision (APPROVED, REJECTED, CHANGES_REQUESTED) 
    for a submitted thesis.
    """
    tenant = get_tenant_from_request(request)
    thesis = get_object_or_404(
        Thesis.objects.select_related('department', 'program').prefetch_related('authors', 'advisers__adviser_membership__user'), 
        id=thesis_id, 
        tenant=tenant
    )

    if thesis.status not in ['SUBMITTED', 'IN_REVIEW']:
        raise HttpError(400, "Thesis is not currently in a reviewable state.")

    reviewer = get_object_or_404(TenantMembership, id=payload.reviewer_membership_id, tenant=tenant)

    # 1. Create Review Record
    ThesisReview.objects.create(
        tenant=tenant,
        thesis=thesis,
        reviewer_membership=reviewer,
        decision=payload.decision,
        comment=payload.comment
    )

    # 2. Transition Thesis State based on decision
    old_status = thesis.status
    new_status = thesis.status

    if payload.decision == 'APPROVED':
        new_status = 'APPROVED'
        thesis.approved_at = timezone.now()
    elif payload.decision == 'REJECTED':
         # Depending on business logic, rejected might just stay 'REJECTED' or go to 'DRAFT'
        new_status = 'DRAFT' 
    elif payload.decision == 'CHANGES_REQUESTED':
        new_status = 'CHANGES_REQUESTED'
    
    if new_status != old_status:
        thesis.status = new_status
        thesis.save()

        ThesisStatusHistory.objects.create(
            tenant=tenant,
            thesis=thesis,
            from_status=old_status,
            to_status=new_status,
            changed_by_membership=reviewer,
            note=f"State transitioned via review decision: {payload.decision}"
        )

    thesis.authors_list = list(thesis.authors.all())
    thesis.advisers_list = list(thesis.advisers.all())
    return thesis

@theses_router.post("/{thesis_id}/publish", response=ThesisDetailSchema)
def publish_thesis(request, thesis_id: UUID):
    """
    Publish Thesis
    
    Change thesis status from 'APPROVED' to 'PUBLISHED'.
    """
    tenant = get_tenant_from_request(request)
    thesis = get_object_or_404(
        Thesis.objects.select_related('department', 'program').prefetch_related('authors', 'advisers__adviser_membership__user'), 
        id=thesis_id, 
        tenant=tenant
    )
    
    if thesis.status != 'APPROVED':
        raise HttpError(400, "Only approved theses can be published.")
        
    old_status = thesis.status
    thesis.status = 'PUBLISHED'
    thesis.published_at = timezone.now()
    thesis.save()
    
    ThesisStatusHistory.objects.create(
        tenant=tenant,
        thesis=thesis,
        from_status=old_status,
        to_status='PUBLISHED',
        note=f"Thesis published automatically or manually."
    )
    
    thesis.authors_list = list(thesis.authors.all())
    thesis.advisers_list = list(thesis.advisers.all())
    return thesis

@theses_router.post("/{thesis_id}/unpublish", response=ThesisDetailSchema)
def unpublish_thesis(request, thesis_id: UUID):
    """
    Unpublish Thesis
    
    Change thesis status from 'PUBLISHED' back to 'APPROVED'.
    """
    tenant = get_tenant_from_request(request)
    thesis = get_object_or_404(
        Thesis.objects.select_related('department', 'program').prefetch_related('authors', 'advisers__adviser_membership__user'), 
        id=thesis_id, 
        tenant=tenant
    )
    
    if thesis.status != 'PUBLISHED':
        raise HttpError(400, "Only published theses can be unpublished.")
        
    old_status = thesis.status
    thesis.status = 'APPROVED'
    thesis.save()
    
    ThesisStatusHistory.objects.create(
        tenant=tenant,
        thesis=thesis,
        from_status=old_status,
        to_status='APPROVED',
        note=f"Thesis unpublished."
    )
    
    thesis.authors_list = list(thesis.authors.all())
    thesis.advisers_list = list(thesis.advisers.all())
    return thesis

from apps.users.models import User
from apps.repository.models import ThesisAuthor, ThesisAdviser

@theses_router.post("/{thesis_id}/authors", response=ThesisDetailSchema)
def assign_author(request, thesis_id: UUID, payload: AuthorAssignSchema):
    """
    Assign Author
    
    Add an author to a thesis.
    """
    tenant = get_tenant_from_request(request)
    thesis = get_object_or_404(
        Thesis.objects.select_related('department', 'program').prefetch_related('authors', 'advisers__adviser_membership__user'), 
        id=thesis_id, 
        tenant=tenant
    )
    
    user = None
    if payload.user_id:
        user = get_object_or_404(User, id=payload.user_id)
        
    ThesisAuthor.objects.create(
        tenant=tenant,
        thesis=thesis,
        user=user,
        display_name=payload.display_name,
        sort_order=payload.sort_order
    )
    
    thesis.authors_list = list(thesis.authors.all())
    thesis.advisers_list = list(thesis.advisers.all())
    return thesis

@theses_router.post("/{thesis_id}/advisers", response=ThesisDetailSchema)
def assign_adviser(request, thesis_id: UUID, payload: AdviserAssignSchema):
    """
    Assign Adviser
    
    Add an adviser to a thesis.
    """
    tenant = get_tenant_from_request(request)
    thesis = get_object_or_404(
        Thesis.objects.select_related('department', 'program').prefetch_related('authors', 'advisers__adviser_membership__user'), 
        id=thesis_id, 
        tenant=tenant
    )
    
    membership = get_object_or_404(TenantMembership, id=payload.adviser_membership_id, tenant=tenant)
    
    ThesisAdviser.objects.create(
        tenant=tenant,
        thesis=thesis,
        adviser_membership=membership
    )
    
    thesis.authors_list = list(thesis.authors.all())
    thesis.advisers_list = list(thesis.advisers.all())
    return thesis
