from datetime import datetime
from typing import List, Optional
from uuid import UUID
from ninja import Schema, ModelSchema

from .models import (
    Department, Program, Thesis, ThesisStatusHistory, ThesisReview,
    ThesisAuthor, ThesisAdviser, Keyword, ThesisKeyword, FileObject, ThesisFile
)


# ==========================================
# Departments
# ==========================================
class DepartmentSchema(ModelSchema):
    class Meta:
        model = Department
        fields = ['id', 'name', 'is_active']

class DepartmentCreateSchema(Schema):
    name: str


# ==========================================
# Programs
# ==========================================
class ProgramSchema(ModelSchema):
    department_id: UUID

    class Meta:
        model = Program
        fields = ['id', 'name', 'is_active']

class ProgramCreateSchema(Schema):
    name: str
    department_id: UUID


# ==========================================
# Theses - Support Entities
# ==========================================
class ThesisAuthorSchema(ModelSchema):
    class Meta:
        model = ThesisAuthor
        fields = ['id', 'display_name', 'sort_order']

class ThesisAdviserSchema(ModelSchema):
    adviser_email: str

    @staticmethod
    def resolve_adviser_email(obj):
        return obj.adviser_membership.user.email if obj.adviser_membership else None

    class Meta:
        model = ThesisAdviser
        fields = ['id']

class KeywordSchema(ModelSchema):
    class Meta:
        model = Keyword
        fields = ['id', 'value']


# ==========================================
# Theses
# ==========================================
class ThesisListSchema(ModelSchema):
    department: Optional[DepartmentSchema] = None
    program: Optional[ProgramSchema] = None
    
    class Meta:
        model = Thesis
        fields = ['id', 'title', 'year', 'status', 'submitted_at', 'approved_at', 'published_at', 'created_at', 'updated_at']

class ThesisDetailSchema(ModelSchema):
    department: Optional[DepartmentSchema] = None
    program: Optional[ProgramSchema] = None
    authors: List[ThesisAuthorSchema] = []
    advisers: List[ThesisAdviserSchema] = []
    
    class Meta:
        model = Thesis
        fields = ['id', 'title', 'abstract', 'year', 'status', 'submitted_at', 'approved_at', 'published_at', 'created_at', 'updated_at']

class ThesisCreateUpdateSchema(Schema):
    title: str
    abstract: str
    year: int
    department_id: Optional[UUID] = None
    program_id: Optional[UUID] = None

class ThesisSubmitSchema(Schema):
    submitter_membership_id: Optional[UUID] = None
    note: Optional[str] = "Submitted for review"

class ThesisReviewCreateSchema(Schema):
    decision: str
    comment: Optional[str] = ""
    reviewer_membership_id: UUID
