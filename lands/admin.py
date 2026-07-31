from django.contrib import admin
from django.utils.html import format_html

from .models import (
    CityBoundary,
    LandAttachment,
    LandCategory,
    Mahalla,
    MonitoringRecord,
    MonitoringYear,
    ObjectVersion,
    PublicLand,
    SystemNotice,
    UrbanizationLayer,
)


@admin.register(LandCategory)
class LandCategoryAdmin(admin.ModelAdmin):
    list_display = ('name_ru', 'name_uz', 'code', 'geometry_type', 'color_display', 'is_active', 'order')
    list_filter = ('geometry_type', 'is_active')
    search_fields = ('name_uz', 'name_ru', 'code')

    @admin.display(description='Цвет')
    def color_display(self, obj):
        return format_html(
            '<span style="background:{};padding:2px 12px;border-radius:4px;">&nbsp;</span> {}',
            obj.color, obj.color,
        )


class LandAttachmentInline(admin.TabularInline):
    model = LandAttachment
    extra = 0
    verbose_name = 'Вложение'
    verbose_name_plural = 'Вложения'


class ObjectVersionInline(admin.TabularInline):
    model = ObjectVersion
    extra = 0
    verbose_name = 'Версия'
    verbose_name_plural = 'Версии по годам'
    fields = ('year', 'area_sqm', 'length_m', 'status', 'condition', 'change_note')
    readonly_fields = ()


@admin.register(PublicLand)
class PublicLandAdmin(admin.ModelAdmin):
    list_display = (
        'public_id', 'name', 'category', 'monitoring_year',
        'status', 'area_sqm', 'length_m', 'road_class', 'updated_at',
    )
    list_filter = ('category', 'status', 'monitoring_year', 'road_class', 'is_active')
    search_fields = ('public_id', 'name', 'cadastral_number', 'address', 'mahalla')
    readonly_fields = ('public_id', 'area_sqm', 'length_m', 'created_at', 'updated_at')
    inlines = [ObjectVersionInline, LandAttachmentInline]
    fieldsets = (
        ('Реестр', {
            'fields': ('public_id', 'name', 'category', 'monitoring_year', 'status', 'condition', 'is_active'),
        }),
        ('Расположение', {
            'fields': ('address', 'mahalla', 'cadastral_number', 'description', 'data_source', 'responsible_org', 'acquisition_date'),
        }),
        ('Дороги / геометрия', {
            'fields': ('road_class', 'geometry', 'area_sqm', 'length_m'),
        }),
        ('Служебное', {
            'fields': ('created_by', 'updated_by', 'created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )


@admin.register(CityBoundary)
class CityBoundaryAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'boundary_type', 'color', 'weight', 'is_visible', 'order', 'updated_at')
    list_filter = ('boundary_type', 'is_visible')
    search_fields = ('name', 'code')
    list_editable = ('is_visible', 'order', 'weight')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(LandAttachment)
class LandAttachmentAdmin(admin.ModelAdmin):
    list_display = ('title', 'land', 'file_type', 'uploaded_at')
    list_filter = ('file_type',)


@admin.register(MonitoringYear)
class MonitoringYearAdmin(admin.ModelAdmin):
    list_display = ('year', 'year_type', 'is_current', 'is_active', 'note')
    list_filter = ('year_type', 'is_current', 'is_active')
    list_editable = ('is_current', 'is_active')


@admin.register(ObjectVersion)
class ObjectVersionAdmin(admin.ModelAdmin):
    list_display = ('land', 'year', 'area_sqm', 'length_m', 'status', 'created_at')
    list_filter = ('year', 'status')
    search_fields = ('land__public_id', 'land__name', 'change_note')


@admin.register(MonitoringRecord)
class MonitoringRecordAdmin(admin.ModelAdmin):
    list_display = ('land', 'year', 'delta_area_ha', 'status', 'recorded_at')
    list_filter = ('year', 'status')
    search_fields = ('description', 'land__public_id')


@admin.register(UrbanizationLayer)
class UrbanizationLayerAdmin(admin.ModelAdmin):
    list_display = ('year', 'name', 'layer_kind', 'area_ha', 'growth_pct', 'is_visible')
    list_filter = ('year', 'layer_kind', 'is_visible')
    list_editable = ('is_visible',)


@admin.register(SystemNotice)
class SystemNoticeAdmin(admin.ModelAdmin):
    list_display = ('title', 'is_active', 'updated_at')
    list_editable = ('is_active',)


@admin.register(Mahalla)
class MahallaAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'is_active')
    search_fields = ('name', 'code')
