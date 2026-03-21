from typing import List, Optional
from ninja import ModelSchema, Schema
from uuid import UUID
from datetime import datetime
from apps.users.models import User, TenantMembership, Invitation

class UserSchema(ModelSchema):
    class Meta:
        model = User
        fields = [
            'id', 'email', 'is_active', 'is_super_admin',
            'last_login_at', 'email_verification_status'
        ]

class TenantMembershipSchema(ModelSchema):
    user: UserSchema

    class Meta:
        model = TenantMembership
        fields = ['id', 'role', 'status', 'created_at', 'updated_at']

class UserProfileSchema(Schema):
    user: UserSchema
    memberships: List[TenantMembershipSchema]

class InvitationSchema(Schema):
    id: UUID
    email: str
    role: str
    expires_at: datetime
    accepted_at: Optional[datetime] = None
    created_at: datetime
    accept_url: Optional[str] = None

class InviteCreateSchema(Schema):
    email: str
    role: str

class InviteAcceptSchema(Schema):
    password: str


class TenantMembershipUpdateSchema(Schema):
    role: Optional[str] = None
    status: Optional[str] = None
