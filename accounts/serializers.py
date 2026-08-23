from rest_framework import serializers

from .models import User


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            'id', 'username', 'email', 'first_name', 'last_name',
            'role', 'organization', 'phone',
            'job_title', 'sector', 'district', 'region', 'purpose', 'interest_layers', 'comment',
            'is_active', 'is_staff', 'is_superuser', 'date_joined', 'last_login',
        )
        read_only_fields = ('id', 'date_joined', 'last_login')


class AdminUserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False, allow_blank=True, min_length=6)

    class Meta:
        model = User
        fields = (
            'id', 'username', 'email', 'password', 'first_name', 'last_name',
            'role', 'organization', 'phone',
            'job_title', 'sector', 'district', 'region', 'purpose', 'interest_layers', 'comment',
            'is_active', 'is_staff', 'is_superuser', 'date_joined', 'last_login',
        )
        read_only_fields = ('id', 'date_joined', 'last_login')

    def create(self, validated_data):
        password = validated_data.pop('password', None) or 'changeme123'
        user = User(**validated_data)
        user.set_password(password)
        if validated_data.get('is_superuser') or validated_data.get('role') == 'admin':
            user.is_staff = True
        user.save()
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        for key, value in validated_data.items():
            setattr(instance, key, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)
    password_confirm = serializers.CharField(write_only=True, min_length=6)

    class Meta:
        model = User
        fields = (
            'username', 'email', 'password', 'password_confirm',
            'first_name', 'last_name', 'organization', 'phone',
            'job_title', 'sector', 'district', 'region', 'purpose', 'interest_layers', 'comment',
        )

    def validate(self, attrs):
        if attrs.get('password') != attrs.get('password_confirm'):
            raise serializers.ValidationError({'password_confirm': 'Parollar mos emas'})
        return attrs

    def create(self, validated_data):
        validated_data.pop('password_confirm', None)
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.role = User.Role.OBSERVER
        user.set_password(password)
        user.save()
        return user
