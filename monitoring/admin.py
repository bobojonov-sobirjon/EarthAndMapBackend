from django.contrib import admin

from .models import (
    ApplicationOnSite,
    ApplicationSubmission,
    ApplicationType,
    ChangeLog,
    Issue,
)


@admin.register(ChangeLog)
class ChangeLogAdmin(admin.ModelAdmin):
    list_display = ('land', 'change_type', 'field_name', 'changed_by', 'changed_at')
    list_filter = ('change_type', 'changed_at')
    search_fields = ('land__name', 'land__public_id', 'description')
    readonly_fields = ('changed_at',)


@admin.register(Issue)
class IssueAdmin(admin.ModelAdmin):
    list_display = ('title', 'land', 'geometry_kind', 'severity', 'status', 'reported_by', 'created_at')
    list_filter = ('severity', 'status', 'geometry_kind')
    search_fields = ('title', 'description')
    fieldsets = (
        ('Основное', {
            'fields': ('title', 'description', 'land', 'severity', 'status'),
        }),
        ('Геометрия', {
            'fields': ('geometry_kind', 'geometry', 'latitude', 'longitude'),
        }),
        ('Исполнители', {
            'fields': ('reported_by', 'assigned_to', 'created_at', 'updated_at', 'resolved_at'),
        }),
    )
    readonly_fields = ('created_at', 'updated_at')


@admin.register(ApplicationType)
class ApplicationTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('name', 'description')
    fields = ('name', 'description', 'is_active')


@admin.register(ApplicationOnSite)
class ApplicationOnSiteAdmin(admin.ModelAdmin):
    list_display = ('application_type', 'site_url', 'is_active', 'created_at')
    list_filter = ('is_active', 'application_type')
    search_fields = ('site_url', 'application_type__name')


@admin.register(ApplicationSubmission)
class ApplicationSubmissionAdmin(admin.ModelAdmin):
    list_display = (
        'application_type', 'user', 'match_score', 'status', 'submitted_at', 'created_at',
    )
    list_filter = ('status', 'application_type')
    search_fields = ('title', 'description', 'analysis_text', 'user__username')
    readonly_fields = ('created_at', 'updated_at', 'submitted_at')
