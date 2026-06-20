from django.contrib.auth import get_user_model

from rest_framework import mixins
from rest_framework import viewsets
from rest_framework.permissions import IsAdminUser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import UserSerializer

User = get_user_model()


class CurrentUserView(APIView):
    """GET /api/v1/auth/me/ — return the authenticated user."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        return Response({
            "id": str(user.uuid),
            "username": user.username,
            "email": user.email,
            "name": user.name or "",
            "phone": user.phone or "",
            "role": user.role or "",
            "is_staff": bool(user.is_staff),
            "is_superuser": bool(user.is_superuser),
        })


class UserViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """Read-only user directory. Staff only.

    Looked up by the public ``uuid`` rather than the database PK.
    """

    queryset = User.objects.all().order_by("email")
    serializer_class = UserSerializer
    permission_classes = [IsAdminUser]
    lookup_field = "uuid"
    search_fields = ["email", "name", "phone"]
    filterset_fields = ["role", "is_active"]
