from rest_framework import serializers

from .models import (
    ApplicationOnSite,
    ApplicationSubmission,
    ApplicationType,
    ChangeLog,
    Issue,
)


class IssueSerializer(serializers.ModelSerializer):
    reported_by_name = serializers.CharField(source='reported_by.username', read_only=True)
    assigned_to_name = serializers.CharField(source='assigned_to.username', read_only=True)
    land_name = serializers.CharField(source='land.name', read_only=True)
    land_public_id = serializers.CharField(source='land.public_id', read_only=True)

    class Meta:
        model = Issue
        fields = (
            'id', 'land', 'land_name', 'land_public_id',
            'title', 'title_ru', 'title_en',
            'description', 'description_ru', 'description_en',
            'severity', 'status', 'geometry_kind', 'geometry',
            'latitude', 'longitude', 'address',
            'reported_by', 'reported_by_name',
            'assigned_to', 'assigned_to_name',
            'created_at', 'updated_at', 'resolved_at',
        )
        read_only_fields = ('reported_by', 'created_at', 'updated_at')


class ChangeLogSerializer(serializers.ModelSerializer):
    changed_by_name = serializers.CharField(source='changed_by.username', read_only=True)
    land_name = serializers.CharField(source='land.name', read_only=True)
    land_public_id = serializers.CharField(source='land.public_id', read_only=True)

    class Meta:
        model = ChangeLog
        fields = (
            'id', 'land', 'land_name', 'land_public_id', 'change_type', 'field_name',
            'old_value', 'new_value', 'description',
            'changed_by', 'changed_by_name', 'changed_at',
        )
        read_only_fields = fields


class ApplicationOnSiteSerializer(serializers.ModelSerializer):
    application_type_name = serializers.CharField(source='application_type.name', read_only=True)

    class Meta:
        model = ApplicationOnSite
        fields = ('id', 'application_type', 'application_type_name', 'site_url', 'is_active')


class ApplicationTypeSerializer(serializers.ModelSerializer):
    site_url = serializers.SerializerMethodField()
    sites = ApplicationOnSiteSerializer(many=True, read_only=True)

    class Meta:
        model = ApplicationType
        fields = ('id', 'name', 'description', 'site_url', 'sites', 'is_active')

    def get_site_url(self, obj):
        site = obj.sites.filter(is_active=True).first()
        return site.site_url if site else ''


class ProblemAnalysisSerializer(serializers.Serializer):
    text = serializers.CharField(min_length=8, max_length=8000)


class ApplicationSubmissionSerializer(serializers.ModelSerializer):
    application_type_name = serializers.CharField(source='application_type.name', read_only=True)
    site_url = serializers.SerializerMethodField()
    user_name = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = ApplicationSubmission
        fields = (
            'id', 'application_type', 'application_type_name', 'site', 'site_url',
            'analysis_text', 'match_score', 'title', 'description', 'status',
            'external_payload', 'issue', 'user', 'user_name',
            'submitted_at', 'created_at', 'updated_at',
        )
        read_only_fields = ('user', 'issue', 'submitted_at', 'created_at', 'updated_at')

    def get_site_url(self, obj):
        if obj.site_id:
            return obj.site.site_url
        site = obj.application_type.sites.filter(is_active=True).first()
        return site.site_url if site else ''


class ApplicationSubmissionCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ApplicationSubmission
        fields = (
            'application_type', 'site', 'analysis_text', 'match_score',
            'title', 'description', 'external_payload', 'status',
        )

    def create(self, validated_data):
        app_type = validated_data.get('application_type')
        if app_type and not validated_data.get('site'):
            site = app_type.sites.filter(is_active=True).first()
            if site:
                validated_data['site'] = site
        return super().create(validated_data)

    def update(self, instance, validated_data):
        app_type = validated_data.get('application_type', instance.application_type)
        if app_type and not validated_data.get('site') and not instance.site_id:
            site = app_type.sites.filter(is_active=True).first()
            if site:
                validated_data['site'] = site
        return super().update(instance, validated_data)