from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('username', 'email', 'role', 'organization', 'sector', 'district', 'is_staff', 'is_active')
    list_filter = ('role', 'is_staff', 'is_active')
    search_fields = ('username', 'email', 'organization')
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Роли и организация', {
            'fields': ('role', 'organization', 'phone', 'job_title', 'sector', 'region', 'district', 'purpose', 'interest_layers', 'comment'),
            'description': 'Главный администратор · Специалист · Сотрудник мониторинга · Публичный пользователь',
        }),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Роли и организация', {'fields': ('role', 'organization', 'phone')}),
    )
