from rest_framework import serializers

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
    UrbanizationRasterSet,
    UrbanizationVectorYear,
)
from .registry_utils import m_to_km, sqm_to_ha


class LandCategorySerializer(serializers.ModelSerializer):
    land_count = serializers.SerializerMethodField()

    class Meta:
        model = LandCategory
        fields = (
            'id', 'code', 'name_uz', 'name_ru', 'name_en', 'geometry_type',
            'color', 'icon', 'description', 'description_ru', 'description_en',
            'is_active', 'order', 'land_count',
        )

    def get_land_count(self, obj):
        return obj.lands.filter(is_active=True).count()


class PublicLandSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name_uz', read_only=True)
    category_name_ru = serializers.CharField(source='category.name_ru', read_only=True)
    category_name_en = serializers.CharField(source='category.name_en', read_only=True)
    category_color = serializers.CharField(source='category.color', read_only=True)
    category_code = serializers.CharField(source='category.code', read_only=True)
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)
    area_ha = serializers.SerializerMethodField()
    length_km = serializers.SerializerMethodField()

    class Meta:
        model = PublicLand
        fields = (
            'id', 'public_id', 'category', 'category_name', 'category_name_ru', 'category_name_en',
            'category_color', 'category_code',
            'name', 'name_ru', 'name_en', 'cadastral_number',
            'address', 'address_ru', 'address_en', 'mahalla',
            'description', 'description_ru', 'description_en',
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
            'id', 'code', 'monitoring_year', 'name', 'name_ru', 'name_en', 'boundary_type', 'geometry',
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
            'id', 'land', 'public_id', 'land_name', 'year',
            'description', 'description_ru', 'description_en',
            'delta_area_ha', 'delta_length_km', 'status',
            'recorded_by', 'recorded_by_name', 'recorded_at',
        )
        read_only_fields = ('recorded_by', 'recorded_at')


class UrbanizationLayerSerializer(serializers.ModelSerializer):
    class Meta:
        model = UrbanizationLayer
        fields = (
            'id', 'year', 'name', 'name_ru', 'name_en', 'layer_kind', 'geometry',
            'area_ha', 'growth_pct', 'color', 'is_visible', 'note', 'note_ru', 'note_en',
        )


class UrbanizationRasterSetSerializer(serializers.ModelSerializer):
    rgb_preview_url = serializers.SerializerMethodField()
    classified_preview_url = serializers.SerializerMethodField()
    rgb_tif_url = serializers.SerializerMethodField()
    classified_tif_url = serializers.SerializerMethodField()

    class Meta:
        model = UrbanizationRasterSet
        fields = (
            'id', 'year', 'title', 'rgb_label', 'classified_label',
            'rgb_bounds', 'classified_bounds',
            'rgb_preview_url', 'classified_preview_url',
            'rgb_tif_url', 'classified_tif_url',
            'urban_area_ha', 'non_urban_area_ha', 'note', 'is_visible',
            'created_at', 'updated_at',
        )
        read_only_fields = (
            'rgb_bounds', 'classified_bounds',
            'rgb_preview_url', 'classified_preview_url',
            'rgb_tif_url', 'classified_tif_url',
            'created_at', 'updated_at',
        )

    def _url(self, f):
        if not f:
            return None
        request = self.context.get('request')
        url = f.url
        return request.build_absolute_uri(url) if request else url

    def get_rgb_preview_url(self, obj):
        return self._url(obj.rgb_preview)

    def get_classified_preview_url(self, obj):
        return self._url(obj.classified_preview)

    def get_rgb_tif_url(self, obj):
        return self._url(obj.rgb_tif)

    def get_classified_tif_url(self, obj):
        return self._url(obj.classified_tif)


class UrbanizationRasterSetWriteSerializer(serializers.ModelSerializer):
    rgb_tif = serializers.FileField()
    classified_tif = serializers.FileField()

    class Meta:
        model = UrbanizationRasterSet
        fields = (
            'id', 'year', 'title', 'rgb_tif', 'classified_tif',
            'rgb_label', 'classified_label',
            'urban_area_ha', 'non_urban_area_ha', 'note', 'is_visible',
        )


class UrbanizationVectorYearSerializer(serializers.ModelSerializer):
    class Meta:
        model = UrbanizationVectorYear
        fields = (
            'id', 'year', 'class_field', 'feature_count',
            'urban_area_ha', 'non_urban_area_ha', 'bounds',
            'source_name', 'note', 'is_visible', 'created_at', 'updated_at',
        )
        read_only_fields = (
            'class_field', 'feature_count', 'urban_area_ha', 'non_urban_area_ha',
            'bounds', 'source_name', 'created_at', 'updated_at',
        )


class UrbanizationVectorYearWriteSerializer(serializers.ModelSerializer):
    shapefile = serializers.FileField(write_only=True)

    class Meta:
        model = UrbanizationVectorYear
        fields = ('year', 'shapefile', 'note', 'is_visible')


class SystemNoticeSerializer(serializers.ModelSerializer):
    class Meta:
        model = SystemNotice
        fields = (
            'id', 'title', 'title_ru', 'title_en',
            'message', 'message_ru', 'message_en',
            'is_active', 'created_at', 'updated_at',
        )
        read_only_fields = ('created_at', 'updated_at')


class MahallaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Mahalla
        fields = ('id', 'name', 'name_ru', 'name_en', 'code', 'geometry', 'is_active')

