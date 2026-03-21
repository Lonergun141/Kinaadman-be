from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.repository.models import (
    Department,
    FileObject,
    Keyword,
    Program,
    Thesis,
    ThesisAdviser,
    ThesisAuthor,
    ThesisFile,
    ThesisKeyword,
    ThesisReview,
    ThesisStatusHistory,
)
from apps.tenants.models import Tenant, TenantBranding, TenantEmailDomain, TenantPolicy
from apps.users.models import TenantMembership


User = get_user_model()


SHOWCASE_RECORDS = [
    {
        "title": "Capstone Project: Barangay Service Request and Incident Mapping Platform",
        "abstract": (
            "This capstone introduces a campus-built service request platform for local "
            "barangays that combines intake workflows, incident mapping, and response "
            "analytics to shorten turnaround time for community reports."
        ),
        "year": 2026,
        "status": "PUBLISHED",
        "department": "College of Computer Studies",
        "program": "BS Information Technology",
        "creator_email": "student1@uok.edu.ph",
        "authors": [
            ("Katrina Mae Dela Pena", "student1@uok.edu.ph"),
            ("Joshua Vincent Ramos", "student2@uok.edu.ph"),
        ],
        "adviser_email": "adviser1@uok.edu.ph",
        "keywords": ["Capstone", "Mapping", "Service Requests"],
    },
    {
        "title": "Capstone Project: QR-Based Laboratory Asset Tracking for Campus Facilities",
        "abstract": (
            "The study designs a capstone system for tracking laboratory devices through "
            "QR check-in, maintenance logging, and equipment utilization dashboards for "
            "shared university facilities."
        ),
        "year": 2025,
        "status": "PUBLISHED",
        "department": "College of Computer Studies",
        "program": "BS Information Technology",
        "creator_email": "student2@uok.edu.ph",
        "authors": [
            ("Angelica Joy Tan", "student2@uok.edu.ph"),
            ("Mark Steven Flores", "student3@uok.edu.ph"),
        ],
        "adviser_email": "adviser2@uok.edu.ph",
        "keywords": ["Capstone", "QR Code", "Asset Tracking"],
    },
    {
        "title": "Undergraduate Thesis: Flood Risk Prediction for River Communities Using LSTM Models",
        "abstract": (
            "This thesis evaluates an LSTM-based forecasting pipeline for short-term flood "
            "risk prediction using rainfall, river level, and watershed indicators gathered "
            "from local monitoring stations."
        ),
        "year": 2026,
        "status": "PUBLISHED",
        "department": "College of Computer Studies",
        "program": "BS Computer Science",
        "creator_email": "student1@uok.edu.ph",
        "authors": [("Paula Camille Gomez", "student1@uok.edu.ph")],
        "adviser_email": "adviser1@uok.edu.ph",
        "keywords": ["Thesis", "Machine Learning", "Flood Prediction"],
    },
    {
        "title": "Undergraduate Thesis: Classifying Corn Leaf Diseases with Lightweight Vision Transformers",
        "abstract": (
            "The research compares compact vision transformer variants for leaf disease "
            "classification and assesses deployment feasibility for low-cost mobile imaging "
            "in agricultural extension settings."
        ),
        "year": 2025,
        "status": "APPROVED",
        "department": "College of Computer Studies",
        "program": "BS Computer Science",
        "creator_email": "student3@uok.edu.ph",
        "authors": [("John Paul Navarro", "student3@uok.edu.ph")],
        "adviser_email": "adviser1@uok.edu.ph",
        "keywords": ["Thesis", "Computer Vision", "Agriculture"],
    },
    {
        "title": "Capstone Project: Alumni Tracer and Skills Analytics Portal for the CCS",
        "abstract": (
            "This capstone develops an alumni tracer platform that collects graduate "
            "employment data, visualizes skills demand trends, and generates summary reports "
            "for program accreditation reviews."
        ),
        "year": 2026,
        "status": "IN_REVIEW",
        "department": "College of Computer Studies",
        "program": "BS Information Technology",
        "creator_email": "student1@uok.edu.ph",
        "authors": [
            ("Rhea Anne Cabrera", "student1@uok.edu.ph"),
            ("Kevin Louie Mercado", "student2@uok.edu.ph"),
        ],
        "adviser_email": "adviser2@uok.edu.ph",
        "keywords": ["Capstone", "Analytics", "Alumni Tracking"],
    },
    {
        "title": "Undergraduate Thesis: Traffic Volume Forecasting with Spatiotemporal Graph Networks",
        "abstract": (
            "The thesis studies graph-based neural forecasting for urban intersections and "
            "benchmarks it against recurrent baselines for daily traffic management scenarios."
        ),
        "year": 2024,
        "status": "PUBLISHED",
        "department": "College of Computer Studies",
        "program": "BS Computer Science",
        "creator_email": "student2@uok.edu.ph",
        "authors": [("Miguel Luis Bautista", "student2@uok.edu.ph")],
        "adviser_email": "adviser1@uok.edu.ph",
        "keywords": ["Thesis", "Forecasting", "Traffic"],
    },
    {
        "title": "Capstone Project: Smart Queue and Appointment System for Registrar Services",
        "abstract": (
            "The capstone proposes a queue and appointment platform that reduces walk-in "
            "congestion through booking slots, digital tickets, and service time analytics."
        ),
        "year": 2025,
        "status": "SUBMITTED",
        "department": "College of Computer Studies",
        "program": "BS Information Technology",
        "creator_email": "student3@uok.edu.ph",
        "authors": [("Justine Marie Velasco", "student3@uok.edu.ph")],
        "adviser_email": "adviser2@uok.edu.ph",
        "keywords": ["Capstone", "Queueing", "Registrar"],
    },
    {
        "title": "Undergraduate Thesis: Early Detection of Concrete Crack Progression from UAV Imagery",
        "abstract": (
            "This engineering thesis evaluates crack progression detection from UAV imagery "
            "using segmentation pipelines that support visual inspection and maintenance planning."
        ),
        "year": 2026,
        "status": "APPROVED",
        "department": "College of Engineering",
        "program": "BS Civil Engineering",
        "creator_email": "student2@uok.edu.ph",
        "authors": [("Carlo Sebastian Uy", "student2@uok.edu.ph")],
        "adviser_email": "adviser1@uok.edu.ph",
        "keywords": ["Thesis", "Civil Engineering", "UAV"],
    },
    {
        "title": "Capstone Project: Research Archive Recommendation Engine for Student Search Sessions",
        "abstract": (
            "This capstone explores content-based and behavior-aware ranking strategies for "
            "recommending related archived studies to students browsing institutional repository records."
        ),
        "year": 2026,
        "status": "DRAFT",
        "department": "College of Computer Studies",
        "program": "BS Information Technology",
        "creator_email": "student1@uok.edu.ph",
        "authors": [
            ("Alyssa Nicole Sarmiento", "student1@uok.edu.ph"),
            ("Daphne Claire Ong", "student3@uok.edu.ph"),
        ],
        "adviser_email": "adviser2@uok.edu.ph",
        "keywords": ["Capstone", "Search", "Recommendations"],
    },
    {
        "title": "Undergraduate Thesis: Predicting Bridge Maintenance Priority with Inspection Data",
        "abstract": (
            "The study builds a machine-assisted prioritization workflow for bridge maintenance "
            "using tabular inspection findings, risk factors, and structural age indicators."
        ),
        "year": 2024,
        "status": "PUBLISHED",
        "department": "College of Engineering",
        "program": "BS Civil Engineering",
        "creator_email": "student3@uok.edu.ph",
        "authors": [("Nathaniel Cruz", "student3@uok.edu.ph")],
        "adviser_email": "adviser1@uok.edu.ph",
        "keywords": ["Thesis", "Bridge Maintenance", "Prediction"],
    },
    {
        "title": "Capstone Project: Scholarship Application Triage and Document Verification Portal",
        "abstract": (
            "This capstone delivers a workflow portal for scholarship applications that "
            "scores submission completeness, flags missing requirements, and speeds up manual review."
        ),
        "year": 2025,
        "status": "IN_REVIEW",
        "department": "College of Computer Studies",
        "program": "BS Information Technology",
        "creator_email": "student2@uok.edu.ph",
        "authors": [
            ("Clarisse Mae Requinto", "student2@uok.edu.ph"),
            ("Ethan Miguel Go", "student1@uok.edu.ph"),
        ],
        "adviser_email": "adviser2@uok.edu.ph",
        "keywords": ["Capstone", "Documents", "Scholarship"],
    },
    {
        "title": "Undergraduate Thesis: Riverbank Erosion Susceptibility Mapping with GIS and Remote Sensing",
        "abstract": (
            "This thesis integrates GIS layers, historical terrain changes, and remote sensing "
            "products to map erosion susceptibility along vulnerable riverbank sections."
        ),
        "year": 2025,
        "status": "PUBLISHED",
        "department": "College of Engineering",
        "program": "BS Civil Engineering",
        "creator_email": "student1@uok.edu.ph",
        "authors": [("Maria Teresa Lim", "student1@uok.edu.ph")],
        "adviser_email": "adviser1@uok.edu.ph",
        "keywords": ["Thesis", "GIS", "Remote Sensing"],
    },
]


MEMBERSHIP_FIXTURES = [
    ("admin@uok.edu.ph", "TENANT_ADMIN"),
    ("librarian@uok.edu.ph", "LIBRARIAN"),
    ("adviser1@uok.edu.ph", "ADVISER"),
    ("adviser2@uok.edu.ph", "ADVISER"),
    ("student1@uok.edu.ph", "STUDENT"),
    ("student2@uok.edu.ph", "STUDENT"),
    ("student3@uok.edu.ph", "STUDENT"),
]


class Command(BaseCommand):
    help = "Seed curated thesis and capstone showcase data for the student repository."

    def add_arguments(self, parser):
        parser.add_argument(
            "--tenant-slug",
            default="uok",
            help="Tenant slug that should receive the showcase repository data.",
        )

    def handle(self, *args, **options):
        tenant_slug = options["tenant_slug"]
        tenant = self.ensure_tenant(tenant_slug)
        memberships = self.ensure_memberships(tenant)
        departments, programs = self.ensure_catalog(tenant)

        created_count = 0
        updated_count = 0

        for index, record in enumerate(SHOWCASE_RECORDS):
            thesis, created = self.upsert_thesis(
                tenant=tenant,
                record=record,
                index=index,
                memberships=memberships,
                departments=departments,
                programs=programs,
            )
            if created:
                created_count += 1
            else:
                updated_count += 1

            self.sync_related_entities(
                tenant=tenant,
                thesis=thesis,
                record=record,
                memberships=memberships,
            )

        total = Thesis.objects.filter(tenant=tenant).count()
        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded showcase data for tenant '{tenant.slug}'. "
                f"Created {created_count}, updated {updated_count}, total theses now {total}."
            )
        )

    def ensure_tenant(self, tenant_slug):
        tenant_defaults = {
            "uok": {
                "name": "University of Kinaadman",
                "branding": {"display_name": "USTP", "primary_color": "#0F2A44"},
                "domain": "uok.edu.ph",
            },
            "ustp": {
                "name": "University of Science & Technology of Southern Philippines",
                "branding": {
                    "display_name": "USTP Theses Repository",
                    "primary_color": "#0F2A44",
                },
                "domain": "ustp.edu.ph",
            },
        }
        settings = tenant_defaults.get(
            tenant_slug,
            {
                "name": tenant_slug.upper(),
                "branding": {"display_name": tenant_slug.upper(), "primary_color": "#0F2A44"},
                "domain": f"{tenant_slug}.edu.ph",
            },
        )

        tenant, _ = Tenant.objects.get_or_create(
            slug=tenant_slug,
            defaults={"name": settings["name"]},
        )
        if tenant.name != settings["name"]:
            tenant.name = settings["name"]
            tenant.save(update_fields=["name"])

        TenantBranding.objects.update_or_create(
            tenant=tenant,
            defaults={
                "display_name": settings["branding"]["display_name"],
                "primary_color": settings["branding"]["primary_color"],
                "secondary_color": "#C9A227",
            },
        )
        TenantPolicy.objects.get_or_create(tenant=tenant, defaults={"campus_only": True})
        TenantEmailDomain.objects.get_or_create(
            tenant=tenant,
            domain=settings["domain"],
            defaults={"is_active": True},
        )
        return tenant

    def ensure_memberships(self, tenant):
        memberships = {}

        for email, role in MEMBERSHIP_FIXTURES:
            user, created = User.objects.get_or_create(email=email)
            if created:
                user.set_password("password123")
                user.is_active = True
                user.email_verification_status = "VERIFIED"
                user.save()

            membership, _ = TenantMembership.objects.get_or_create(
                tenant=tenant,
                user=user,
                defaults={"role": role, "status": "ACTIVE"},
            )
            if membership.role != role or membership.status != "ACTIVE":
                membership.role = role
                membership.status = "ACTIVE"
                membership.save(update_fields=["role", "status", "updated_at"])

            memberships[email] = membership

        return memberships

    def ensure_catalog(self, tenant):
        departments = {}
        programs = {}

        catalog = {
            "College of Computer Studies": [
                "BS Information Technology",
                "BS Computer Science",
            ],
            "College of Engineering": ["BS Civil Engineering"],
        }

        for department_name, program_names in catalog.items():
            department, _ = Department.objects.get_or_create(
                tenant=tenant,
                name=department_name,
                defaults={"is_active": True},
            )
            if not department.is_active:
                department.is_active = True
                department.save(update_fields=["is_active"])
            departments[department_name] = department

            for program_name in program_names:
                program, _ = Program.objects.get_or_create(
                    tenant=tenant,
                    department=department,
                    name=program_name,
                    defaults={"is_active": True},
                )
                if not program.is_active or program.department_id != department.id:
                    program.is_active = True
                    program.department = department
                    program.save(update_fields=["is_active", "department"])
                programs[program_name] = program

        return departments, programs

    def upsert_thesis(self, tenant, record, index, memberships, departments, programs):
        base_date = timezone.now() - timedelta(days=(index + 1) * 18)
        submitted_at = None
        approved_at = None
        published_at = None

        if record["status"] in {"SUBMITTED", "IN_REVIEW", "APPROVED", "PUBLISHED"}:
            submitted_at = base_date
        if record["status"] in {"APPROVED", "PUBLISHED"}:
            approved_at = base_date + timedelta(days=9)
        if record["status"] == "PUBLISHED":
            published_at = base_date + timedelta(days=16)

        thesis, created = Thesis.objects.update_or_create(
            tenant=tenant,
            title=record["title"],
            defaults={
                "abstract": record["abstract"],
                "year": record["year"],
                "status": record["status"],
                "department": departments[record["department"]],
                "program": programs[record["program"]],
                "created_by_membership": memberships[record["creator_email"]],
                "submitted_at": submitted_at,
                "approved_at": approved_at,
                "published_at": published_at,
            },
        )
        return thesis, created

    def sync_related_entities(self, tenant, thesis, record, memberships):
        ThesisAuthor.objects.filter(tenant=tenant, thesis=thesis).delete()
        ThesisAdviser.objects.filter(tenant=tenant, thesis=thesis).delete()
        ThesisKeyword.objects.filter(tenant=tenant, thesis=thesis).delete()
        ThesisReview.objects.filter(tenant=tenant, thesis=thesis).delete()
        ThesisStatusHistory.objects.filter(tenant=tenant, thesis=thesis).delete()

        for sort_order, (display_name, email) in enumerate(record["authors"], start=1):
            membership = memberships.get(email)
            ThesisAuthor.objects.create(
                tenant=tenant,
                thesis=thesis,
                user=membership.user if membership else None,
                display_name=display_name,
                sort_order=sort_order,
            )

        adviser_membership = memberships[record["adviser_email"]]
        ThesisAdviser.objects.create(
            tenant=tenant,
            thesis=thesis,
            adviser_membership=adviser_membership,
        )

        for value in record["keywords"]:
            keyword, _ = Keyword.objects.get_or_create(tenant=tenant, value=value)
            ThesisKeyword.objects.get_or_create(
                tenant=tenant,
                thesis=thesis,
                keyword=keyword,
            )

        if thesis.submitted_at:
            ThesisStatusHistory.objects.create(
                tenant=tenant,
                thesis=thesis,
                from_status="DRAFT",
                to_status="SUBMITTED",
                changed_by_membership=memberships[record["creator_email"]],
                note="Seeded showcase submission event.",
            )

        if thesis.status in {"IN_REVIEW", "APPROVED", "PUBLISHED"}:
            ThesisReview.objects.create(
                tenant=tenant,
                thesis=thesis,
                reviewer_membership=adviser_membership,
                decision="APPROVED" if thesis.status in {"APPROVED", "PUBLISHED"} else "PENDING",
                comment="Showcase review record generated for repository browsing.",
            )

        if thesis.status in {"APPROVED", "PUBLISHED"}:
            ThesisStatusHistory.objects.create(
                tenant=tenant,
                thesis=thesis,
                from_status="SUBMITTED",
                to_status="APPROVED",
                changed_by_membership=adviser_membership,
                note="Seeded showcase approval event.",
            )

        if thesis.status == "PUBLISHED":
            ThesisStatusHistory.objects.create(
                tenant=tenant,
                thesis=thesis,
                from_status="APPROVED",
                to_status="PUBLISHED",
                changed_by_membership=memberships["librarian@uok.edu.ph"],
                note="Seeded showcase publication event.",
            )

        file_object, _ = FileObject.objects.update_or_create(
            tenant=tenant,
            object_key=f"showcase/{thesis.id}/main.pdf",
            defaults={
                "provider": "S3",
                "bucket": "kinaadman-bucket",
                "filename": f"{thesis.id}.pdf",
                "content_type": "application/pdf",
                "size_bytes": 2_400_000,
            },
        )
        ThesisFile.objects.update_or_create(
            tenant=tenant,
            thesis=thesis,
            kind="MAIN_PDF",
            defaults={
                "file_object": file_object,
                "label": "Repository PDF",
                "uploaded_by_membership": memberships[record["creator_email"]],
            },
        )
