from rest_framework import serializers

from .models import User


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            'id', 'username', 'email', 'first_name', 'last_name',
            'role', 'organization', 'phone',
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

    class Meta:
        model = User
        fields = ('username', 'email', 'password', 'first_name', 'last_name', 'role', 'organization')

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user
