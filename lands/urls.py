from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .dashboard_views import (
    CompareYearsView,
    DashboardView,
    MonitoringRecordViewSet,
    MonitoringYearViewSet,
    ObjectVersionViewSet,
    UrbanizationLayerViewSet,
    UrbanizationRasterSetViewSet,
    UrbanizationVectorYearViewSet,
    UrbanizationGeoJsonView,
    UrbanizationBundleUploadView,
    UrbanizationBundlePreviewView,
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
    ReverseGeocodeView,
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
router.register('urbanization-maps', UrbanizationRasterSetViewSet, basename='urbanization-map')
router.register('urbanization-vectors', UrbanizationVectorYearViewSet, basename='urbanization-vector')
router.register('mahallas', MahallaViewSet, basename='mahalla')
router.register('notices', SystemNoticeViewSet, basename='notice')

urlpatterns = [
    path('', include(router.urls)),
    path('statistics/', StatisticsView.as_view(), name='statistics'),
    path('dashboard/', DashboardView.as_view(), name='dashboard'),
    path('compare/', CompareYearsView.as_view(), name='compare-years'),
    path('urbanization/', UrbanizationView.as_view(), name='urbanization'),
    path('urbanization/bundle/', UrbanizationBundleUploadView.as_view(), name='urbanization-bundle'),
    path('urbanization/bundle/preview/', UrbanizationBundlePreviewView.as_view(), name='urbanization-bundle-preview'),
    path('urbanization/geojson/', UrbanizationGeoJsonView.as_view(), name='urbanization-geojson'),
    path('export/excel/', ExportExcelView.as_view(), name='export-excel'),
    path('map-config/', MapConfigView.as_view(), name='map-config'),
    path('geocode/reverse/', ReverseGeocodeView.as_view(), name='geocode-reverse'),
    path('import/', ImportLayerView.as_view(), name='import-layer'),
]
