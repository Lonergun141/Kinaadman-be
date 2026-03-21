import json
from datetime import timedelta

from django.test import Client, TestCase
from django.utils import timezone

from apps.repository.models import Thesis, ThesisAuthor
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
        self.student_membership = TenantMembership.objects.create(
            tenant=self.tenant,
            user=self.student_user,
            role="STUDENT",
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
        )
        ThesisAuthor.objects.create(
            tenant=self.tenant,
            thesis=self.thesis,
            user=self.student_user,
            display_name="Lifecycle Student",
            sort_order=0,
        )
        self.client = Client(
            HTTP_HOST="127.0.0.1",
            HTTP_X_TENANT_ID=str(self.tenant.id),
        )

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
                    "reviewer_membership_id": str(self.reviewer_membership.id),
                    "note": "Review opened",
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(start_review_response.status_code, 200)

        approve_response = self.client.post(
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
