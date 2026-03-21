import json

from django.test import Client, TestCase

from apps.tenants.models import Tenant
from apps.users.models import Invitation, TenantMembership, User


def authenticate_client(tenant: Tenant, email: str, password: str) -> Client:
    login_client = Client(
        HTTP_HOST="127.0.0.1",
        HTTP_X_TENANT_ID=str(tenant.id),
    )
    response = login_client.post(
        "/v1/auth/login",
        data=json.dumps(
            {
                "email": email,
                "password": password,
                "tenant_hint": str(tenant.id),
            }
        ),
        content_type="application/json",
    )
    access_token = response.json()["tokens"]["access_token"]
    return Client(
        HTTP_HOST="127.0.0.1",
        HTTP_X_TENANT_ID=str(tenant.id),
        HTTP_AUTHORIZATION=f"Bearer {access_token}",
    )


class UserManagementApiTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(
            slug="user-fixtures",
            name="User Fixtures University",
        )
        self.admin_user = User.objects.create_user(
            email="admin@users.edu",
            password="password123",
            email_verification_status="VERIFIED",
        )
        self.member_user = User.objects.create_user(
            email="student@users.edu",
            password="password123",
            email_verification_status="VERIFIED",
        )
        self.admin_membership = TenantMembership.objects.create(
            tenant=self.tenant,
            user=self.admin_user,
            role="TENANT_ADMIN",
            status="ACTIVE",
        )
        self.member_membership = TenantMembership.objects.create(
            tenant=self.tenant,
            user=self.member_user,
            role="STUDENT",
            status="ACTIVE",
        )
        self.client = authenticate_client(
            tenant=self.tenant,
            email=self.admin_user.email,
            password="password123",
        )

    def test_admin_can_update_membership_role_and_status(self):
        response = self.client.generic(
            "PATCH",
            f"/v1/users/memberships/{self.member_membership.id}",
            data=json.dumps({"role": "LIBRARIAN", "status": "SUSPENDED"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.member_membership.refresh_from_db()
        self.assertEqual(self.member_membership.role, "LIBRARIAN")
        self.assertEqual(self.member_membership.status, "SUSPENDED")

    def test_admin_can_create_and_list_invitations(self):
        create_response = self.client.post(
            "/v1/users/invites",
            data=json.dumps(
                {
                    "email": "newmember@users.edu",
                    "role": "ADVISER",
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(create_response.status_code, 200)
        created_payload = create_response.json()
        self.assertTrue(created_payload["accept_url"].startswith("/invite/"))

        list_response = self.client.get("/v1/users/invites")
        self.assertEqual(list_response.status_code, 200)
        payload = list_response.json()
        self.assertEqual(len(payload), 1)
        self.assertEqual(payload[0]["email"], "newmember@users.edu")

        invitation = Invitation.objects.get(email="newmember@users.edu")
        self.assertEqual(invitation.invited_by_membership_id, self.admin_membership.id)
