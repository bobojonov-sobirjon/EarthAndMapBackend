from rest_framework import serializers

from .models import (
    CityBoundary,
    LandAttachment,
    LandCategory,
    MonitoringRecord,
    MonitoringYear,
    ObjectVersion,
    PublicLand,
    SystemNotice,
    UrbanizationLayer,
)
from .registry_utils import m_to_km, sqm_to_ha


class LandCategorySerializer(serializers.ModelSerializer):
    land_count = serializers.SerializerMethodField()

    class Meta:
        model = LandCategory
        fields = (
            'id', 'code', 'name_uz', 'name_ru', 'geometry_type',
            'color', 'icon', 'description', 'is_active', 'order', 'land_count',
        )

    def get_land_count(self, obj):
        return obj.lands.filter(is_active=True).count()


class PublicLandSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name_uz', read_only=True)
    category_name_ru = serializers.CharField(source='category.name_ru', read_only=True)
    category_color = serializers.CharField(source='category.color', read_only=True)
    category_code = serializers.CharField(source='category.code', read_only=True)
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)
    area_ha = serializers.SerializerMethodField()
    length_km = serializers.SerializerMethodField()

    class Meta:
        model = PublicLand
        fields = (
            'id', 'public_id', 'category', 'category_name', 'category_name_ru',
            'category_color', 'category_code',
            'name', 'cadastral_number', 'address', 'mahalla', 'description',
            'data_source', 'geometry',
            'area_sqm', 'area_ha', 'length_m', 'length_km',
            'status', 'condition', 'road_class', 'monitoring_year',
            'responsible_org', 'acquisition_date',
            'created_by', 'created_by_name',
            'created_at', 'updated_at', 'is_active',
        )
        read_only_fields = (
            'public_id', 'area_sqm', 'length_m', 'created_at', 'updated_at',
        )

    def get_area_ha(self, obj):
        return sqm_to_ha(obj.area_sqm)

    def get_length_km(self, obj):
        return m_to_km(obj.length_m)


class LandAttachmentSerializer(serializers.ModelSerializer):
    uploaded_by_name = serializers.CharField(source='uploaded_by.username', read_only=True)

    class Meta:
        model = LandAttachment
        fields = (
            'id', 'land', 'file', 'file_type', 'title',
            'uploaded_by', 'uploaded_by_name', 'uploaded_at',
        )
        read_only_fields = ('uploaded_by', 'uploaded_at')


class CityBoundarySerializer(serializers.ModelSerializer):
    class Meta:
        model = CityBoundary
        fields = (
            'id', 'code', 'name', 'boundary_type', 'geometry',
            'color', 'weight', 'dash_array', 'fill_opacity',
            'is_visible', 'order', 'updated_at',
        )


class MonitoringYearSerializer(serializers.ModelSerializer):
    class Meta:
        model = MonitoringYear
        fields = ('id', 'year', 'year_type', 'is_current', 'is_active', 'note')


class ObjectVersionSerializer(serializers.ModelSerializer):
    public_id = serializers.CharField(source='land.public_id', read_only=True)
    land_name = serializers.CharField(source='land.name', read_only=True)
    area_ha = serializers.SerializerMethodField()
    length_km = serializers.SerializerMethodField()

    class Meta:
        model = ObjectVersion
        fields = (
            'id', 'land', 'public_id', 'land_name', 'year',
            'geometry', 'area_sqm', 'area_ha', 'length_m', 'length_km',
            'status', 'condition', 'change_note', 'created_at',
        )

    def get_area_ha(self, obj):
        return sqm_to_ha(obj.area_sqm)

    def get_length_km(self, obj):
        return m_to_km(obj.length_m)


class MonitoringRecordSerializer(serializers.ModelSerializer):
    public_id = serializers.CharField(source='land.public_id', read_only=True)
    land_name = serializers.CharField(source='land.name', read_only=True)
    recorded_by_name = serializers.CharField(source='recorded_by.username', read_only=True)

    class Meta:
        model = MonitoringRecord
        fields = (
            'id', 'land', 'public_id', 'land_name', 'year', 'description',
            'delta_area_ha', 'delta_length_km', 'status',
            'recorded_by', 'recorded_by_name', 'recorded_at',
        )
        read_only_fields = ('recorded_by', 'recorded_at')


class UrbanizationLayerSerializer(serializers.ModelSerializer):
    class Meta:
        model = UrbanizationLayer
        fields = (
            'id', 'year', 'name', 'layer_kind', 'geometry',
            'area_ha', 'growth_pct', 'color', 'is_visible', 'note',
        )


class SystemNoticeSerializer(serializers.ModelSerializer):
    class Meta:
        model = SystemNotice
        fields = ('id', 'title', 'message', 'is_active', 'updated_at')
