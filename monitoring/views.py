from rest_framework import viewsets

from accounts.permissions import IsNotObserver

from .models import ChangeLog, Issue
from .serializers import ChangeLogSerializer, IssueSerializer


class ChangeLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ChangeLog.objects.select_related('land', 'changed_by')
    serializer_class = ChangeLogSerializer
    filterset_fields = ['land', 'change_type']
    ordering_fields = ['changed_at']


class IssueViewSet(viewsets.ModelViewSet):
    queryset = Issue.objects.select_related('land', 'reported_by', 'assigned_to')
    serializer_class = IssueSerializer
    permission_classes = [IsNotObserver]
    filterset_fields = ['status', 'severity', 'land']
    search_fields = ['title', 'description']
    ordering_fields = ['created_at', 'severity']

    def perform_create(self, serializer):
        serializer.save(reported_by=self.request.user)
