import json

from django.test import Client, TestCase

from apps.authentication.models import AuthSession
from apps.tenants.models import Tenant
from apps.users.models import TenantMembership, User


class AuthenticationLoginTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(
            slug="auth-fixtures",
            name="Authentication Fixtures University",
        )
        self.user = User.objects.create_user(
            email="member@auth.edu",
            password="password123",
            email_verification_status="VERIFIED",
        )
        self.membership = TenantMembership.objects.create(
            tenant=self.tenant,
            user=self.user,
            role="TENANT_ADMIN",
            status="ACTIVE",
        )
        self.client = Client(
            HTTP_HOST="127.0.0.1",
            HTTP_X_TENANT_ID=str(self.tenant.id),
        )

    def test_login_returns_membership_context_and_scoped_session(self):
        response = self.client.post(
            "/v1/auth/login",
            data=json.dumps(
                {
                    "email": self.user.email,
                    "password": "password123",
                    "tenant_hint": str(self.tenant.id),
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["user"]["role"], "TENANT_ADMIN")
        self.assertEqual(payload["user"]["membership_id"], str(self.membership.id))

        session = AuthSession.objects.get(user=self.user)
        self.assertEqual(session.tenant_id, self.tenant.id)
        self.assertEqual(session.membership_id, self.membership.id)

    def test_super_admin_can_login_without_tenant_membership(self):
        super_admin = User.objects.create_user(
            email="root@platform.dev",
            password="password123",
            email_verification_status="VERIFIED",
            is_super_admin=True,
            is_staff=True,
        )

        response = self.client.post(
            "/v1/auth/login",
            data=json.dumps(
                {
                    "email": super_admin.email,
                    "password": "password123",
                    "tenant_hint": str(self.tenant.id),
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["user"]["role"], "SUPER_ADMIN")
        self.assertIsNone(payload["user"]["membership_id"])
        self.assertTrue(payload["user"]["is_super_admin"])

        session = AuthSession.objects.get(user=super_admin)
        self.assertEqual(session.tenant_id, self.tenant.id)
        self.assertIsNone(session.membership_id)
