from django.contrib.auth import get_user_model

from rest_framework import serializers

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source="uuid", read_only=True)

    class Meta:
        model = User
        fields = [
            "id", "username", "email", "name", "phone",
            "role", "is_staff", "is_superuser", "is_active", "date_joined",
        ]
        read_only_fields = ["username", "is_staff", "is_superuser", "is_active", "date_joined"]
