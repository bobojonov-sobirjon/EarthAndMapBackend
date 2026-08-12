from rest_framework import viewsets
from rest_framework.filters import SearchFilter

from .models import User
from .permissions import IsAdminRole
from .serializers import AdminUserSerializer


class AdminUserViewSet(viewsets.ModelViewSet):
    """Админ-панель: управление пользователями."""

    queryset = User.objects.all().order_by('-date_joined')
    serializer_class = AdminUserSerializer
    permission_classes = [IsAdminRole]
    filter_backends = [SearchFilter]
    search_fields = ['username', 'email', 'organization', 'first_name', 'last_name']
    filterset_fields = ['role', 'is_active', 'is_staff', 'is_superuser']
