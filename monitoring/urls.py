from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    ApplicationOnSiteAdminViewSet,
    ApplicationSubmissionViewSet,
    ApplicationTypeAdminViewSet,
    ApplicationTypeViewSet,
    ChangeLogViewSet,
    EmbedProxyView,
    IssueViewSet,
    ProblemAnalysisView,
)

router = DefaultRouter()
router.register('changes', ChangeLogViewSet, basename='change')
router.register('issues', IssueViewSet, basename='issue')
router.register('application-types', ApplicationTypeViewSet, basename='application-type')
router.register('application-submissions', ApplicationSubmissionViewSet, basename='application-submission')
router.register('admin/application-types', ApplicationTypeAdminViewSet, basename='admin-application-type')
router.register('admin/application-sites', ApplicationOnSiteAdminViewSet, basename='admin-application-site')

urlpatterns = [
    path('embed/', EmbedProxyView.as_view(), name='embed-proxy'),
    path('problem-analysis/', ProblemAnalysisView.as_view(), name='problem-analysis'),
    path('', include(router.urls)),
]
