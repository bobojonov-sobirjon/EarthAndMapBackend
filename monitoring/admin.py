from django.contrib import admin

from .models import ChangeLog, Issue


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
