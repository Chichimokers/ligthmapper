from rest_framework import serializers
from django.contrib.auth import get_user_model

User = get_user_model()


class UserProfileSerializer(serializers.ModelSerializer):
    role = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'email', 'username', 'first_name', 'last_name',
            'latitude', 'longitude', 'has_power', 'last_power_update',
            'created_at', 'updated_at', 'role'
        ]
        read_only_fields = ['id', 'email', 'created_at', 'updated_at', 'last_power_update', 'role']
    
    def get_role(self, obj):
        if obj.is_superuser:
            return 'admin'
        return 'user'


class LightStatusPublicSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['latitude', 'longitude', 'has_power', 'last_power_update']


class LightStatusAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'latitude', 'longitude', 'has_power', 'last_power_update']


class GoogleAuthSerializer(serializers.Serializer):
    id_token = serializers.CharField()
