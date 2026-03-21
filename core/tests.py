from django.test import Client, TestCase

from apps.authentication.models import AuthSession
from apps.authentication.services import generate_tokens_for_user
from apps.tenants.models import Tenant
from apps.users.models import TenantMembership, User
from core.models import AuditLog


class AuditLogAccessTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(
            slug="audit-fixtures",
            name="Audit Fixtures University",
        )
        self.librarian_user = User.objects.create_user(
            email="librarian.audit@example.edu",
            password="password123",
            email_verification_status="VERIFIED",
        )
        self.student_user = User.objects.create_user(
            email="student.audit@example.edu",
            password="password123",
            email_verification_status="VERIFIED",
        )
        self.librarian_membership = TenantMembership.objects.create(
            tenant=self.tenant,
            user=self.librarian_user,
            role="LIBRARIAN",
            status="ACTIVE",
        )
        self.student_membership = TenantMembership.objects.create(
            tenant=self.tenant,
            user=self.student_user,
            role="STUDENT",
            status="ACTIVE",
        )
        AuditLog.objects.create(
            tenant=self.tenant,
            actor_membership=self.librarian_membership,
            action="thesis.published",
            entity_type="thesis",
            entity_id=self.tenant.id,
        )
        self.client = Client(
            HTTP_HOST="127.0.0.1",
            HTTP_X_TENANT_ID=str(self.tenant.id),
        )

    def build_auth_header(self, user, membership):
        session = AuthSession.objects.create(
            tenant=self.tenant,
            user=user,
            membership=membership,
        )
        tokens = generate_tokens_for_user(user, session)
        return {"HTTP_AUTHORIZATION": f"Bearer {tokens['access_token']}"}

    def test_librarian_can_view_audit_log(self):
        response = self.client.get(
            "/v1/core/audit",
            **self.build_auth_header(self.librarian_user, self.librarian_membership),
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)

    def test_student_cannot_view_audit_log(self):
        response = self.client.get(
            "/v1/core/audit",
            **self.build_auth_header(self.student_user, self.student_membership),
        )

        self.assertEqual(response.status_code, 403)

    def test_super_admin_can_view_audit_log(self):
        super_admin = User.objects.create_user(
            email="super.audit@example.edu",
            password="password123",
            email_verification_status="VERIFIED",
            is_super_admin=True,
            is_staff=True,
        )
        session = AuthSession.objects.create(
            tenant=self.tenant,
            user=super_admin,
            membership=None,
        )
        tokens = generate_tokens_for_user(super_admin, session)
        client = Client(
            HTTP_HOST="127.0.0.1",
            HTTP_X_TENANT_ID=str(self.tenant.id),
            HTTP_AUTHORIZATION=f"Bearer {tokens['access_token']}",
        )

        response = client.get("/v1/core/audit")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)
