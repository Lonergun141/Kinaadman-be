from django.test import Client, TestCase

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
