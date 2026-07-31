from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import ChangeLogViewSet, IssueViewSet

router = DefaultRouter()
router.register('changes', ChangeLogViewSet, basename='change')
router.register('issues', IssueViewSet, basename='issue')

urlpatterns = [
    path('', include(router.urls)),
]
