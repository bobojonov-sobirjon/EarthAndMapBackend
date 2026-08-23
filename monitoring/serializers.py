from rest_framework import serializers

from .models import ChangeLog, Issue


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