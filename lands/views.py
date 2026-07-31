from datetime import timedelta

from django.db.models import Count, Sum
from django.db.models.functions import TruncMonth
from django.http import HttpResponse
from django.utils import timezone
from openpyxl import Workbook
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsNotObserver

from .filters import PublicLandFilter
from .geo_utils import to_feature, to_feature_collection
from .models import CityBoundary, LandAttachment, LandCategory, PublicLand
from .serializers import (
    CityBoundarySerializer,
    LandAttachmentSerializer,
    LandCategorySerializer,
    PublicLandSerializer,
)


class LandCategoryViewSet(viewsets.ModelViewSet):
    queryset = LandCategory.objects.filter(is_active=True)
    serializer_class = LandCategorySerializer
    permission_classes = [IsNotObserver]
    lookup_field = 'code'
    lookup_url_kwarg = 'code'


class PublicLandViewSet(viewsets.ModelViewSet):
    queryset = PublicLand.objects.filter(is_active=True).select_related('category', 'created_by')
    serializer_class = PublicLandSerializer
    permission_classes = [IsNotObserver]
    filterset_class = PublicLandFilter
    search_fields = ['name', 'cadastral_number', 'address', 'description', 'public_id', 'mahalla']
    ordering_fields = ['name', 'area_sqm', 'created_at', 'updated_at', 'status', 'public_id', 'monitoring_year']

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, updated_by=self.request.user)

    def perform_update(self, serializer):
        instance = serializer.instance
        instance._changed_by = self.request.user
        serializer.save(updated_by=self.request.user)

    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save()

    @action(detail=False, methods=['get'], permission_classes=[AllowAny])
    def geojson(self, request):
        category = request.query_params.get('category')
        status_filter = request.query_params.get('status')
        year = request.query_params.get('year')
        road_class = request.query_params.get('road_class')
        qs = PublicLand.objects.filter(is_active=True).select_related('category')
        if category:
            qs = qs.filter(category_id=category)
        if status_filter:
            qs = qs.filter(status=status_filter)
        if road_class:
            qs = qs.filter(road_class=road_class)
        # year — фильтр по актуальной версии года (если есть)
        if year:
            from .models import ObjectVersion
            land_ids = ObjectVersion.objects.filter(year=int(year)).values_list('land_id', flat=True)
            qs = qs.filter(id__in=land_ids)
        return Response(to_feature_collection(qs))

    @action(detail=True, methods=['get'])
    def feature(self, request, pk=None):
        land = self.get_object()
        return Response(to_feature(land))

    @action(detail=True, methods=['get'])
    def history(self, request, pk=None):
        land = self.get_object()
        from monitoring.models import ChangeLog
        from monitoring.serializers import ChangeLogSerializer
        logs = ChangeLog.objects.filter(land=land).select_related('changed_by')[:50]
        return Response(ChangeLogSerializer(logs, many=True).data)

    @action(detail=True, methods=['get'])
    def versions(self, request, pk=None):
        land = self.get_object()
        from .models import ObjectVersion
        from .serializers import ObjectVersionSerializer
        qs = ObjectVersion.objects.filter(land=land).order_by('year')
        return Response(ObjectVersionSerializer(qs, many=True).data)


class CityBoundaryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = CityBoundary.objects.all()
    serializer_class = CityBoundarySerializer
    permission_classes = [AllowAny]

    @action(detail=False, methods=['get'], permission_classes=[AllowAny])
    def geojson(self, request):
        """Buxoro shahar va viloyat chegaralarini GeoJSON sifatida qaytaradi."""
        qs = CityBoundary.objects.filter(is_visible=True)
        boundary_type = request.query_params.get('type')
        if boundary_type:
            qs = qs.filter(boundary_type=boundary_type)

        features = []
        for b in qs:
            features.append({
                'type': 'Feature',
                'id': b.id,
                'geometry': b.geometry,
                'properties': {
                    'id': b.id,
                    'code': b.code,
                    'name': b.name,
                    'boundary_type': b.boundary_type,
                    'color': b.color,
                    'weight': b.weight,
                    'dash_array': b.dash_array,
                    'fill_opacity': b.fill_opacity,
                },
            })
        return Response({'type': 'FeatureCollection', 'features': features})


class LandAttachmentViewSet(viewsets.ModelViewSet):
    queryset = LandAttachment.objects.select_related('land', 'uploaded_by')
    serializer_class = LandAttachmentSerializer
    permission_classes = [IsNotObserver]

    def perform_create(self, serializer):
        serializer.save(uploaded_by=self.request.user)


class StatisticsView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        lands = PublicLand.objects.filter(is_active=True)

        by_category = (
            lands.values('category__name_uz', 'category__color', 'category__code')
            .annotate(count=Count('id'), total_area=Sum('area_sqm'))
            .order_by('-count')
        )

        by_status = (
            lands.values('status')
            .annotate(count=Count('id'))
            .order_by('-count')
        )

        totals = {
            'total_objects': lands.count(),
            'total_area_sqm': lands.aggregate(s=Sum('area_sqm'))['s'] or 0,
            'total_roads_length_m': lands.filter(
                category__geometry_type='LineString'
            ).aggregate(s=Sum('length_m'))['s'] or 0,
        }

        six_months_ago = timezone.now() - timedelta(days=180)
        changes_by_month = (
            PublicLand.objects.filter(updated_at__gte=six_months_ago)
            .annotate(month=TruncMonth('updated_at'))
            .values('month')
            .annotate(count=Count('id'))
            .order_by('month')
        )

        return Response({
            'totals': totals,
            'by_category': list(by_category),
            'by_status': list(by_status),
            'changes_by_month': [
                {'month': item['month'].strftime('%Y-%m') if item['month'] else None, 'count': item['count']}
                for item in changes_by_month
            ],
        })


class ExportExcelView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        wb = Workbook()
        ws = wb.active
        ws.title = 'Umumfoydalanish yerlari'
        ws.append([
            'ID', 'Nomi', 'Kategoriya', 'Status', 'Maydon (m²)',
            'Uzunlik (m)', 'Manzil', 'Kadastr', 'Yangilangan',
        ])

        lands = PublicLand.objects.filter(is_active=True).select_related('category')
        category = request.query_params.get('category')
        status_filter = request.query_params.get('status')
        if category:
            lands = lands.filter(category_id=category)
        if status_filter:
            lands = lands.filter(status=status_filter)

        for land in lands:
            ws.append([
                land.id,
                land.name,
                land.category.name_uz,
                land.get_status_display(),
                land.area_sqm,
                land.length_m,
                land.address,
                land.cadastral_number,
                land.updated_at.strftime('%Y-%m-%d %H:%M'),
            ])

        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )
        response['Content-Disposition'] = 'attachment; filename="buxoro_gis_export.xlsx"'
        wb.save(response)
        return response


class MapConfigView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        from django.conf import settings
        return Response({
            'center': settings.BUKHARA_CENTER,
            'categories': LandCategorySerializer(
                LandCategory.objects.filter(is_active=True), many=True
            ).data,
        })
