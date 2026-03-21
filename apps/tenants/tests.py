import json

from django.test import Client, TestCase

from apps.tenants.models import Tenant
from apps.users.models import TenantMembership, User


def login_for_access_token(tenant: Tenant, email: str, password: str) -> str:
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
    return response.json()["tokens"]["access_token"]


def authenticate_client(tenant: Tenant, email: str, password: str) -> Client:
    access_token = login_for_access_token(tenant, email, password)
    return Client(
        HTTP_HOST="127.0.0.1",
        HTTP_X_TENANT_ID=str(tenant.id),
        HTTP_AUTHORIZATION=f"Bearer {access_token}",
    )


class TenantSettingsApiTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(
            slug="tenant-fixtures",
            name="Tenant Fixtures University",
        )
        self.admin_user = User.objects.create_user(
            email="admin@tenant.edu",
            password="password123",
            email_verification_status="VERIFIED",
        )
        TenantMembership.objects.create(
            tenant=self.tenant,
            user=self.admin_user,
            role="TENANT_ADMIN",
            status="ACTIVE",
        )
        self.client = authenticate_client(
            tenant=self.tenant,
            email=self.admin_user.email,
            password="password123",
        )

    def test_email_domain_crud(self):
        create_response = self.client.post(
            "/v1/tenants/email-domains",
            data=json.dumps({"domain": "tenant.edu"}),
            content_type="application/json",
        )

        self.assertEqual(create_response.status_code, 200)
        created_id = create_response.json()["id"]

        list_response = self.client.get("/v1/tenants/email-domains")
        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(list_response.json()[0]["domain"], "tenant.edu")

        delete_response = self.client.delete(f"/v1/tenants/email-domains/{created_id}")
        self.assertEqual(delete_response.status_code, 200)
        self.assertEqual(self.client.get("/v1/tenants/email-domains").json(), [])

    def test_host_alias_crud(self):
        create_response = self.client.post(
            "/v1/tenants/host-aliases",
            data=json.dumps({"hostname": "archive.tenant.edu"}),
            content_type="application/json",
        )

        self.assertEqual(create_response.status_code, 200)
        created_id = create_response.json()["id"]

        list_response = self.client.get("/v1/tenants/host-aliases")
        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(list_response.json()[0]["hostname"], "archive.tenant.edu")

        delete_response = self.client.delete(f"/v1/tenants/host-aliases/{created_id}")
        self.assertEqual(delete_response.status_code, 200)
        self.assertEqual(self.client.get("/v1/tenants/host-aliases").json(), [])

    def test_super_admin_can_list_all_tenants_and_manage_target_tenant(self):
        target_tenant = Tenant.objects.create(
            slug="tenant-target",
            name="Target Tenant University",
        )
        super_admin = User.objects.create_user(
            email="super.admin@platform.dev",
            password="password123",
            email_verification_status="VERIFIED",
            is_super_admin=True,
            is_staff=True,
        )
        access_token = login_for_access_token(
            tenant=self.tenant,
            email=super_admin.email,
            password="password123",
        )
        super_admin_client = Client(
            HTTP_HOST="127.0.0.1",
            HTTP_X_TENANT_ID=str(target_tenant.id),
            HTTP_AUTHORIZATION=f"Bearer {access_token}",
        )

        list_response = super_admin_client.get("/v1/tenants/")
        self.assertEqual(list_response.status_code, 200)
        listed_ids = {tenant["id"] for tenant in list_response.json()}
        self.assertIn(str(self.tenant.id), listed_ids)
        self.assertIn(str(target_tenant.id), listed_ids)

        create_response = super_admin_client.post(
            "/v1/tenants/email-domains",
            data=json.dumps({"domain": "target.edu"}),
            content_type="application/json",
        )
        self.assertEqual(create_response.status_code, 200)

        domains_response = super_admin_client.get("/v1/tenants/email-domains")
        self.assertEqual(domains_response.status_code, 200)
        self.assertEqual(domains_response.json()[0]["domain"], "target.edu")
