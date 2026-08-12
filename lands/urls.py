from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .dashboard_views import (
    CompareYearsView,
    DashboardView,
    MonitoringRecordViewSet,
    MonitoringYearViewSet,
    ObjectVersionViewSet,
    UrbanizationLayerViewSet,
    UrbanizationView,
)
from .views import (
    CityBoundaryViewSet,
    ExportExcelView,
    LandAttachmentViewSet,
    LandCategoryViewSet,
    MahallaViewSet,
    ImportLayerView,
    MapConfigView,
    PublicLandViewSet,
    StatisticsView,
    SystemNoticeViewSet,
)

router = DefaultRouter()
router.register('categories', LandCategoryViewSet, basename='category')
router.register('lands', PublicLandViewSet, basename='land')
router.register('boundaries', CityBoundaryViewSet, basename='boundary')
router.register('attachments', LandAttachmentViewSet, basename='attachment')
router.register('monitoring-years', MonitoringYearViewSet, basename='monitoring-year')
router.register('object-versions', ObjectVersionViewSet, basename='object-version')
router.register('monitoring-records', MonitoringRecordViewSet, basename='monitoring-record')
router.register('urbanization-layers', UrbanizationLayerViewSet, basename='urbanization-layer')
router.register('mahallas', MahallaViewSet, basename='mahalla')
router.register('notices', SystemNoticeViewSet, basename='notice')

urlpatterns = [
    path('', include(router.urls)),
    path('statistics/', StatisticsView.as_view(), name='statistics'),
    path('dashboard/', DashboardView.as_view(), name='dashboard'),
    path('compare/', CompareYearsView.as_view(), name='compare-years'),
    path('urbanization/', UrbanizationView.as_view(), name='urbanization'),
    path('export/excel/', ExportExcelView.as_view(), name='export-excel'),
    path('map-config/', MapConfigView.as_view(), name='map-config'),
    path('import/', ImportLayerView.as_view(), name='import-layer'),
]
