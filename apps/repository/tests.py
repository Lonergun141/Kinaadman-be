import json
from datetime import timedelta

from django.test import Client, TestCase
from django.utils import timezone

from apps.repository.models import (
    Department,
    FileObject,
    Thesis,
    ThesisAdviser,
    ThesisAuthor,
    ThesisFile,
    ThesisReview,
)
from apps.tenants.models import Tenant
from apps.users.models import TenantMembership, User


class RepositorySearchTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(
            slug="search-fixtures",
            name="Search Fixtures University",
        )
        Thesis.objects.create(
            tenant=self.tenant,
            title="Capstone Project: Barangay Service Request and Incident Mapping Platform",
            abstract="A capstone that streamlines service request intake and mapping.",
            year=2026,
            status="PUBLISHED",
        )
        Thesis.objects.create(
            tenant=self.tenant,
            title="Undergraduate Thesis: Flood Risk Prediction for River Communities",
            abstract="A thesis on flood risk forecasting.",
            year=2025,
            status="PUBLISHED",
        )
        self.client = Client(
            HTTP_HOST="127.0.0.1",
            HTTP_X_TENANT_ID=str(self.tenant.id),
        )

    def test_search_returns_partial_title_match(self):
        response = self.client.get("/v1/theses/", {"search": "barang"})

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(len(payload), 1)
        self.assertIn("Barangay Service Request", payload[0]["title"])

    def test_search_keeps_full_text_matches(self):
        response = self.client.get("/v1/theses/", {"search": "Flood"})

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(len(payload), 1)
        self.assertIn("Flood Risk Prediction", payload[0]["title"])


class RepositoryWorkspaceOwnershipTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(
            slug="workspace-fixtures",
            name="Workspace Fixtures University",
        )
        self.student_user = User.objects.create_user(
            email="student1@example.edu",
            password="password123",
            email_verification_status="VERIFIED",
        )
        self.other_user = User.objects.create_user(
            email="student2@example.edu",
            password="password123",
            email_verification_status="VERIFIED",
        )
        self.student_membership = TenantMembership.objects.create(
            tenant=self.tenant,
            user=self.student_user,
            role="STUDENT",
            status="ACTIVE",
        )
        self.other_membership = TenantMembership.objects.create(
            tenant=self.tenant,
            user=self.other_user,
            role="STUDENT",
            status="ACTIVE",
        )
        self.owned_thesis = Thesis.objects.create(
            tenant=self.tenant,
            title="Student-Owned Draft",
            abstract="Owned by the current student.",
            year=2026,
            status="DRAFT",
            created_by_membership=self.student_membership,
        )
        ThesisAuthor.objects.create(
            tenant=self.tenant,
            thesis=self.owned_thesis,
            user=self.student_user,
            display_name="Student One",
            sort_order=0,
        )
        self.other_thesis = Thesis.objects.create(
            tenant=self.tenant,
            title="Another Student Draft",
            abstract="Owned by another student.",
            year=2026,
            status="SUBMITTED",
            created_by_membership=self.other_membership,
        )
        ThesisAuthor.objects.create(
            tenant=self.tenant,
            thesis=self.other_thesis,
            user=self.other_user,
            display_name="Student Two",
            sort_order=0,
        )
        self.client = Client(
            HTTP_HOST="127.0.0.1",
            HTTP_X_TENANT_ID=str(self.tenant.id),
        )

    def test_list_theses_can_filter_to_authored_records(self):
        response = self.client.get(
            "/v1/theses/",
            {"author_user_id": str(self.student_user.id)},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(len(payload), 1)
        self.assertEqual(payload[0]["title"], "Student-Owned Draft")

    def test_create_thesis_sets_creator_membership(self):
        response = self.client.post(
            "/v1/theses/",
            data={
                "title": "New Student Draft",
                "abstract": "A newly created draft.",
                "year": 2026,
                "department_id": None,
                "program_id": None,
                "created_by_membership_id": str(self.student_membership.id),
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        thesis = Thesis.objects.get(title="New Student Draft")
        self.assertEqual(thesis.created_by_membership_id, self.student_membership.id)


class RepositoryPublicPublishingTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(
            slug="public-fixtures",
            name="Public Fixtures University",
        )
        self.public_thesis = Thesis.objects.create(
            tenant=self.tenant,
            title="Public Repository Record",
            abstract="Visible in the public repository.",
            year=2026,
            status="PUBLISHED",
            visibility="PUBLIC",
            thesis_type="THESIS",
        )
        ThesisAuthor.objects.create(
            tenant=self.tenant,
            thesis=self.public_thesis,
            display_name="Public Author",
            sort_order=0,
        )
        self.embargoed_thesis = Thesis.objects.create(
            tenant=self.tenant,
            title="Embargoed Public Metadata Record",
            abstract="Metadata should stay visible while the file remains restricted.",
            year=2025,
            status="PUBLISHED",
            visibility="EMBARGOED",
            embargo_until=timezone.localdate() + timedelta(days=30),
            thesis_type="CAPSTONE",
        )
        ThesisAuthor.objects.create(
            tenant=self.tenant,
            thesis=self.embargoed_thesis,
            display_name="Embargoed Author",
            sort_order=0,
        )
        Thesis.objects.create(
            tenant=self.tenant,
            title="Campus Only Record",
            abstract="Should not appear in public discovery.",
            year=2024,
            status="PUBLISHED",
            visibility="CAMPUS_ONLY",
        )
        self.client = Client()

    def test_public_list_only_shows_public_and_embargoed_records(self):
        response = self.client.get(f"/v1/public/tenants/{self.tenant.slug}/theses/")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        titles = {item["title"] for item in payload}
        self.assertIn("Public Repository Record", titles)
        self.assertIn("Embargoed Public Metadata Record", titles)
        self.assertNotIn("Campus Only Record", titles)

    def test_public_detail_exposes_citations_and_embargo_download_control(self):
        response = self.client.get(
            f"/v1/public/tenants/{self.tenant.slug}/theses/{self.embargoed_thesis.public_slug}/"
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertFalse(payload["can_download_public_files"])
        self.assertIn("APA", payload["citation_formats"])
        self.assertEqual(payload["files"], [])
        self.assertEqual(payload["reviews"], [])


class RepositoryAnalyticsTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(
            slug="analytics-fixtures",
            name="Analytics Fixtures University",
        )
        self.engineering = Department.objects.create(
            tenant=self.tenant,
            name="Engineering",
        )
        self.business = Department.objects.create(
            tenant=self.tenant,
            name="Business",
        )
        self.student_user = User.objects.create_user(
            email="analytics.student@example.edu",
            password="password123",
            email_verification_status="VERIFIED",
        )
        self.adviser_user = User.objects.create_user(
            email="analytics.adviser@example.edu",
            password="password123",
            email_verification_status="VERIFIED",
        )
        self.student_membership = TenantMembership.objects.create(
            tenant=self.tenant,
            user=self.student_user,
            role="STUDENT",
            status="ACTIVE",
        )
        self.adviser_membership = TenantMembership.objects.create(
            tenant=self.tenant,
            user=self.adviser_user,
            role="ADVISER",
            status="ACTIVE",
        )

        self.ready_thesis = Thesis.objects.create(
            tenant=self.tenant,
            title="Approved Ready Thesis",
            abstract="A ready thesis for analytics.",
            year=2026,
            status="APPROVED",
            visibility="CAMPUS_ONLY",
            thesis_type="THESIS",
            department=self.engineering,
            created_by_membership=self.student_membership,
            panel_members=["Panel A", "Panel B"],
            panel_approval_status="APPROVED",
            defense_date=timezone.localdate(),
            rights_license="CC BY-NC 4.0",
            approved_at=timezone.now(),
        )
        ThesisAuthor.objects.create(
            tenant=self.tenant,
            thesis=self.ready_thesis,
            user=self.student_user,
            display_name="Analytics Student",
            sort_order=0,
        )
        ThesisAdviser.objects.create(
            tenant=self.tenant,
            thesis=self.ready_thesis,
            adviser_membership=self.adviser_membership,
        )
        ThesisReview.objects.create(
            tenant=self.tenant,
            thesis=self.ready_thesis,
            reviewer_membership=self.adviser_membership,
            decision="APPROVED",
            comment="Recommended for publication.",
        )
        ready_file_object = FileObject.objects.create(
            tenant=self.tenant,
            bucket="analytics-fixtures",
            object_key="theses/approved-ready.pdf",
            filename="approved-ready.pdf",
            content_type="application/pdf",
            size_bytes=2048,
            checksum="ready123",
        )
        ThesisFile.objects.create(
            tenant=self.tenant,
            thesis=self.ready_thesis,
            file_object=ready_file_object,
            kind="MAIN_PDF",
            access_level="DOWNLOADABLE",
            is_current=True,
            uploaded_by_membership=self.student_membership,
        )

        self.blocked_thesis = Thesis.objects.create(
            tenant=self.tenant,
            title="Submitted Blocked Thesis",
            abstract="A blocked thesis for analytics.",
            year=2026,
            status="SUBMITTED",
            visibility="PRIVATE",
            thesis_type="CAPSTONE",
            department=self.engineering,
            created_by_membership=self.student_membership,
            submitted_at=timezone.now(),
        )

        self.published_thesis = Thesis.objects.create(
            tenant=self.tenant,
            title="Published Repository Thesis",
            abstract="A published thesis for analytics.",
            year=2025,
            status="PUBLISHED",
            visibility="PUBLIC",
            thesis_type="THESIS",
            department=self.business,
            created_by_membership=self.student_membership,
            panel_members=["Panel C", "Panel D"],
            panel_approval_status="APPROVED",
            defense_date=timezone.localdate(),
            rights_license="CC BY 4.0",
            approved_at=timezone.now() - timedelta(days=4),
            published_at=timezone.now() - timedelta(days=2),
        )
        ThesisAdviser.objects.create(
            tenant=self.tenant,
            thesis=self.published_thesis,
            adviser_membership=self.adviser_membership,
        )
        ThesisReview.objects.create(
            tenant=self.tenant,
            thesis=self.published_thesis,
            reviewer_membership=self.adviser_membership,
            decision="APPROVED",
            comment="Published-ready recommendation.",
        )
        published_file_object = FileObject.objects.create(
            tenant=self.tenant,
            bucket="analytics-fixtures",
            object_key="theses/published-record.pdf",
            filename="published-record.pdf",
            content_type="application/pdf",
            size_bytes=3072,
            checksum="published123",
        )
        ThesisFile.objects.create(
            tenant=self.tenant,
            thesis=self.published_thesis,
            file_object=published_file_object,
            kind="MAIN_PDF",
            access_level="DOWNLOADABLE",
            is_current=True,
            uploaded_by_membership=self.student_membership,
        )

        self.client = Client(
            HTTP_HOST="127.0.0.1",
            HTTP_X_TENANT_ID=str(self.tenant.id),
        )

    def test_repository_analytics_overview_returns_aggregated_metrics(self):
        response = self.client.get("/v1/analytics/repository/overview")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["summary"]["total_records"], 3)
        self.assertEqual(payload["summary"]["published_count"], 1)
        self.assertEqual(payload["summary"]["active_workflow_count"], 2)
        self.assertEqual(payload["summary"]["ready_count"], 1)
        self.assertEqual(payload["summary"]["blocked_count"], 1)
        self.assertEqual(len(payload["monthly_activity"]), 6)
        self.assertEqual(
            sum(entry["created"] for entry in payload["monthly_activity"]),
            3,
        )
        self.assertEqual(
            sum(entry["published"] for entry in payload["monthly_activity"]),
            1,
        )

        status_counts = {
            entry["label"]: entry["count"] for entry in payload["status_data"]
        }
        self.assertEqual(status_counts["Approved"], 1)
        self.assertEqual(status_counts["Submitted"], 1)
        self.assertEqual(status_counts["Published"], 1)

        pipeline_counts = {
            entry["label"]: entry["count"] for entry in payload["pipeline_data"]
        }
        self.assertEqual(pipeline_counts["Submitted"], 1)
        self.assertEqual(pipeline_counts["In review"], 0)
        self.assertEqual(pipeline_counts["Approved"], 1)
        self.assertEqual(pipeline_counts["Ready"], 1)

        blocker_labels = {entry["label"] for entry in payload["blocker_data"]}
        self.assertIn("Adviser recommendation", blocker_labels)
        self.assertIn("Main manuscript uploaded", blocker_labels)

    def test_repository_analytics_overview_applies_department_and_window_filters(self):
        response = self.client.get(
            "/v1/analytics/repository/overview",
            {
                "department_id": str(self.engineering.id),
                "months": 12,
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["window_months"], 12)
        self.assertEqual(payload["summary"]["total_records"], 2)
        self.assertEqual(payload["summary"]["published_count"], 0)
        self.assertEqual(payload["summary"]["active_workflow_count"], 2)
        self.assertEqual(payload["summary"]["ready_count"], 1)
        self.assertEqual(payload["summary"]["blocked_count"], 1)
        self.assertEqual(len(payload["monthly_activity"]), 12)

        status_counts = {
            entry["label"]: entry["count"] for entry in payload["status_data"]
        }
        self.assertEqual(status_counts["Approved"], 1)
        self.assertEqual(status_counts["Submitted"], 1)
        self.assertNotIn("Published", status_counts)

class RepositoryLifecycleTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(
            slug="lifecycle-fixtures",
            name="Lifecycle Fixtures University",
        )
        self.student_user = User.objects.create_user(
            email="student.lifecycle@example.edu",
            password="password123",
            email_verification_status="VERIFIED",
        )
        self.reviewer_user = User.objects.create_user(
            email="reviewer.lifecycle@example.edu",
            password="password123",
            email_verification_status="VERIFIED",
        )
        self.adviser_user = User.objects.create_user(
            email="adviser.lifecycle@example.edu",
            password="password123",
            email_verification_status="VERIFIED",
        )
        self.student_membership = TenantMembership.objects.create(
            tenant=self.tenant,
            user=self.student_user,
            role="STUDENT",
            status="ACTIVE",
        )
        self.adviser_membership = TenantMembership.objects.create(
            tenant=self.tenant,
            user=self.adviser_user,
            role="ADVISER",
            status="ACTIVE",
        )
        self.reviewer_membership = TenantMembership.objects.create(
            tenant=self.tenant,
            user=self.reviewer_user,
            role="LIBRARIAN",
            status="ACTIVE",
        )
        self.thesis = Thesis.objects.create(
            tenant=self.tenant,
            title="Lifecycle Draft",
            abstract="Ready for workflow testing.",
            year=2026,
            status="DRAFT",
            visibility="PUBLIC",
            created_by_membership=self.student_membership,
            panel_members=["Panel Member One", "Panel Member Two"],
            panel_approval_status="APPROVED",
            defense_date=timezone.localdate(),
            rights_license="CC BY-NC 4.0",
        )
        ThesisAdviser.objects.create(
            tenant=self.tenant,
            thesis=self.thesis,
            adviser_membership=self.adviser_membership,
        )
        ThesisAuthor.objects.create(
            tenant=self.tenant,
            thesis=self.thesis,
            user=self.student_user,
            display_name="Lifecycle Student",
            sort_order=0,
        )
        file_object = FileObject.objects.create(
            tenant=self.tenant,
            bucket="repository-fixtures",
            object_key="theses/lifecycle-draft.pdf",
            filename="lifecycle-draft.pdf",
            content_type="application/pdf",
            size_bytes=2048,
            checksum="abc123",
        )
        ThesisFile.objects.create(
            tenant=self.tenant,
            thesis=self.thesis,
            file_object=file_object,
            kind="MAIN_PDF",
            access_level="DOWNLOADABLE",
            is_current=True,
            uploaded_by_membership=self.student_membership,
        )
        self.client = Client(
            HTTP_HOST="127.0.0.1",
            HTTP_X_TENANT_ID=str(self.tenant.id),
        )

    def test_publish_requires_librarian_readiness_checks(self):
        self.thesis.panel_approval_status = "PENDING"
        self.thesis.panel_approval_note = ""
        self.thesis.rights_license = ""
        self.thesis.save(update_fields=["panel_approval_status", "panel_approval_note", "rights_license", "updated_at"])

        self.client.post(
            f"/v1/theses/{self.thesis.id}/submit",
            data=json.dumps(
                {
                    "submitter_membership_id": str(self.student_membership.id),
                    "note": "Submitting for review",
                }
            ),
            content_type="application/json",
        )
        self.client.post(
            f"/v1/theses/{self.thesis.id}/start-review",
            data=json.dumps(
                {
                    "reviewer_membership_id": str(self.reviewer_membership.id),
                    "note": "Review opened",
                }
            ),
            content_type="application/json",
        )
        self.client.post(
            f"/v1/theses/{self.thesis.id}/review",
            data=json.dumps(
                {
                    "reviewer_membership_id": str(self.reviewer_membership.id),
                    "decision": "APPROVED",
                    "comment": "Approved after review.",
                }
            ),
            content_type="application/json",
        )

        publish_response = self.client.post(
            f"/v1/theses/{self.thesis.id}/publish",
            data=json.dumps(
                {
                    "actor_membership_id": str(self.reviewer_membership.id),
                    "note": "Attempting publication without readiness",
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(publish_response.status_code, 400)
        self.assertIn("Adviser recommendation", publish_response.json()["detail"])

    def test_review_lifecycle_creates_versions_and_public_record(self):
        submit_response = self.client.post(
            f"/v1/theses/{self.thesis.id}/submit",
            data=json.dumps(
                {
                    "submitter_membership_id": str(self.student_membership.id),
                    "note": "Submitting for review",
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(submit_response.status_code, 200)

        start_review_response = self.client.post(
            f"/v1/theses/{self.thesis.id}/start-review",
            data=json.dumps(
                {
                    "reviewer_membership_id": str(self.adviser_membership.id),
                    "note": "Adviser review opened",
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(start_review_response.status_code, 200)

        approve_response = self.client.post(
            f"/v1/theses/{self.thesis.id}/review",
            data=json.dumps(
                {
                    "reviewer_membership_id": str(self.adviser_membership.id),
                    "decision": "APPROVED",
                    "comment": "Adviser recommends this record for publishing.",
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(approve_response.status_code, 200)

        publish_response = self.client.post(
            f"/v1/theses/{self.thesis.id}/publish",
            data=json.dumps(
                {
                    "actor_membership_id": str(self.reviewer_membership.id),
                    "note": "Published to the public repository",
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(publish_response.status_code, 200)

        self.thesis.refresh_from_db()
        self.assertEqual(self.thesis.status, "PUBLISHED")
        self.assertGreaterEqual(self.thesis.metadata_versions.count(), 4)
        self.assertEqual(self.thesis.status_history.count(), 4)

        public_response = self.client.get(
            f"/v1/public/tenants/{self.tenant.slug}/theses/{self.thesis.public_slug}/"
        )
        self.assertEqual(public_response.status_code, 200)
        self.assertEqual(public_response.json()["status"], "PUBLISHED")
