from django.contrib import admin
from unfold.admin import ModelAdmin

from .models import (
    Department,
    Program,
    Thesis,
    ThesisStatusHistory,
    ThesisReview,
    ThesisAuthor,
    ThesisAdviser,
    Keyword,
    ThesisKeyword,
    FileObject,
    ThesisFile,
)

# Register your models here.

@admin.register(Department)
class DepartmentAdmin(ModelAdmin):
    list_display = ('name', 'tenant', 'is_active')
    list_filter = ('tenant', 'is_active')
    search_fields = ('name',)
    readonly_fields = ('id',)

@admin.register(Program)
class ProgramAdmin(ModelAdmin):
    list_display = ('name', 'department', 'tenant', 'is_active')
    list_filter = ('department', 'tenant', 'is_active')
    search_fields = ('name',)
    readonly_fields = ('id',)

@admin.register(Thesis)
class ThesisAdmin(ModelAdmin):
    list_display = ('title', 'program', 'status', 'created_at')
    list_filter = ('program', 'status', 'created_at')
    search_fields = ('title', 'abstract')
    readonly_fields = ('id', 'created_at', 'updated_at')

@admin.register(ThesisStatusHistory)
class ThesisStatusHistoryAdmin(ModelAdmin):
    list_display = ('thesis', 'to_status', 'changed_at')
    list_filter = ('thesis', 'to_status', 'changed_at')
    search_fields = ('thesis__title',)
    readonly_fields = ('id', 'changed_at')

@admin.register(ThesisReview)
class ThesisReviewAdmin(ModelAdmin):
    list_display = ('thesis', 'reviewer_membership', 'decision', 'created_at')
    list_filter = ('thesis', 'reviewer_membership', 'decision', 'created_at')
    search_fields = ('thesis__title', 'reviewer_membership__user__email')
    readonly_fields = ('id', 'created_at')

@admin.register(ThesisAuthor)
class ThesisAuthorAdmin(ModelAdmin):
    list_display = ('thesis', 'display_name')
    list_filter = ('thesis',)
    search_fields = ('thesis__title', 'display_name', 'user__email')
    readonly_fields = ('id',)

@admin.register(ThesisAdviser)
class ThesisAdviserAdmin(ModelAdmin):
    list_display = ('thesis', 'adviser_membership')
    list_filter = ('thesis', 'adviser_membership')
    search_fields = ('thesis__title', 'adviser_membership__user__email')
    readonly_fields = ('id',)

@admin.register(Keyword)
class KeywordAdmin(ModelAdmin):
    list_display = ('value', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('value',)
    readonly_fields = ('id', 'created_at')

@admin.register(ThesisKeyword)
class ThesisKeywordAdmin(ModelAdmin):
    list_display = ('thesis', 'keyword')
    list_filter = ('thesis', 'keyword')
    search_fields = ('thesis__title', 'keyword__value')
    readonly_fields = ('id',)

@admin.register(FileObject)
class FileObjectAdmin(ModelAdmin):
    list_display = ('filename', 'provider', 'content_type', 'size_bytes', 'created_at')
    list_filter = ('provider', 'created_at')
    search_fields = ('filename', 'object_key')
    readonly_fields = ('id', 'created_at')

@admin.register(ThesisFile)
class ThesisFileAdmin(ModelAdmin):
    list_display = ('thesis', 'file_object', 'kind', 'created_at')
    list_filter = ('thesis', 'kind', 'created_at')
    search_fields = ('thesis__title', 'file_object__filename')
    readonly_fields = ('id', 'created_at')

