from datetime import timedelta

from django.db.models import Count, Sum
from django.db.models.functions import TruncMonth
from django.http import HttpResponse
from django.utils import timezone
from openpyxl import Workbook
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsAdminRole, IsNotObserver

from .filters import PublicLandFilter
from .geo_utils import to_feature, to_feature_collection
from .models import CityBoundary, LandAttachment, LandCategory, Mahalla, PublicLand, SystemNotice
from .serializers import (
    CityBoundarySerializer,
    LandAttachmentSerializer,
    LandCategorySerializer,
    MahallaSerializer,
    PublicLandSerializer,
    SystemNoticeSerializer,
)


class LandCategoryViewSet(viewsets.ModelViewSet):
    queryset = LandCategory.objects.all()
    serializer_class = LandCategorySerializer
    permission_classes = [IsNotObserver]
    lookup_field = 'code'
    lookup_url_kwarg = 'code'
    search_fields = ['name_uz', 'name_ru', 'code']
    filterset_fields = ['geometry_type', 'is_active']

    def get_queryset(self):
        qs = LandCategory.objects.all().order_by('order', 'name_uz')
        user = self.request.user
        is_admin = user and user.is_authenticated and (
            getattr(user, 'is_superuser', False) or getattr(user, 'role', None) == 'admin'
        )
        if self.action == 'list' and not is_admin:
            qs = qs.filter(is_active=True)
        return qs


class PublicLandViewSet(viewsets.ModelViewSet):
    queryset = PublicLand.objects.select_related('category', 'created_by')
    serializer_class = PublicLandSerializer
    permission_classes = [IsNotObserver]
    filterset_class = PublicLandFilter
    search_fields = ['name', 'cadastral_number', 'address', 'description', 'public_id', 'mahalla']
    ordering_fields = ['name', 'area_sqm', 'created_at', 'updated_at', 'status', 'public_id', 'monitoring_year']

    def get_queryset(self):
        qs = PublicLand.objects.select_related('category', 'created_by')
        user = self.request.user
        is_admin = user and user.is_authenticated and (
            getattr(user, 'is_superuser', False) or getattr(user, 'role', None) == 'admin'
        )
        if not is_admin:
            qs = qs.filter(is_active=True)
        return qs

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


class CityBoundaryViewSet(viewsets.ModelViewSet):
    queryset = CityBoundary.objects.all()
    serializer_class = CityBoundarySerializer
    search_fields = ['name', 'code']
    filterset_fields = ['boundary_type', 'is_visible']

    def get_permissions(self):
        if self.action in ('list', 'retrieve', 'geojson'):
            return [AllowAny()]
        return [IsNotObserver()]

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


class MahallaViewSet(viewsets.ModelViewSet):
    queryset = Mahalla.objects.all()
    serializer_class = MahallaSerializer
    permission_classes = [IsNotObserver]
    search_fields = ['name', 'code']
    filterset_fields = ['is_active']


class SystemNoticeViewSet(viewsets.ModelViewSet):
    queryset = SystemNotice.objects.all()
    serializer_class = SystemNoticeSerializer
    permission_classes = [IsNotObserver]
    search_fields = ['title', 'message']
    filterset_fields = ['is_active']


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


class ImportLayerView(APIView):
    """Admin: shapefile (.zip/.shp) yoki GeoJSON ni xaritaga yuklash."""

    permission_classes = [IsAdminRole]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def post(self, request):
        import json
        import tempfile
        import zipfile
        from pathlib import Path

        from .import_utils import find_shp, iter_geojson_features, pick_name, read_shapefile

        target = request.data.get('target', 'layer')  # layer | boundary
        category_code = request.data.get('category')
        replace = str(request.data.get('replace', '')).lower() in ('1', 'true', 'yes')
        prefix = (request.data.get('prefix') or 'Obyekt').strip() or 'Obyekt'
        uploaded = request.FILES.get('file')
        geojson_raw = request.data.get('geojson')

        records = []
        source_name = 'upload'

        if uploaded:
            source_name = uploaded.name
            suffix = Path(uploaded.name).suffix.lower()
            if suffix == '.geojson' or suffix == '.json':
                try:
                    data = json.loads(uploaded.read().decode('utf-8'))
                except Exception:
                    return Response({'detail': 'GeoJSON o‘qilmadi'}, status=400)
                records = list(iter_geojson_features(data))
            elif suffix in ('.zip', '.shp'):
                with tempfile.TemporaryDirectory() as tmp:
                    tmp_path = Path(tmp)
                    if suffix == '.zip':
                        zpath = tmp_path / uploaded.name
                        zpath.write_bytes(uploaded.read())
                        with zipfile.ZipFile(zpath) as zf:
                            zf.extractall(tmp_path)
                    else:
                        (tmp_path / uploaded.name).write_bytes(uploaded.read())
                    shp = find_shp(tmp_path)
                    if not shp:
                        return Response(
                            {'detail': 'ZIP ichida .shp topilmadi. .shp + .shx + .dbf kerak.'},
                            status=400,
                        )
                    records = list(read_shapefile(shp))
                    source_name = shp.name
            else:
                return Response(
                    {'detail': 'Faqat .zip (shapefile), .shp yoki .geojson qabul qilinadi'},
                    status=400,
                )
        elif geojson_raw:
            try:
                data = json.loads(geojson_raw) if isinstance(geojson_raw, str) else geojson_raw
            except Exception:
                return Response({'detail': 'GeoJSON noto‘g‘ri'}, status=400)
            records = list(iter_geojson_features(data))
        else:
            return Response({'detail': 'Fayl yoki GeoJSON yuboring'}, status=400)

        if not records:
            return Response({'detail': 'Faylda geometriya topilmadi'}, status=400)

        if target == 'boundary':
            props, geom = records[0]
            code = request.data.get('boundary_code') or 'bukhara_city'
            name = pick_name(props, 'Chegara', 1)
            btype = request.data.get('boundary_type') or 'city'
            obj, _ = CityBoundary.objects.update_or_create(
                code=code,
                defaults={
                    'name': name,
                    'boundary_type': btype,
                    'geometry': geom,
                    'is_visible': True,
                },
            )
            return Response({
                'imported': 1,
                'target': 'boundary',
                'id': obj.id,
                'name': obj.name,
                'source': source_name,
            })

        if not category_code:
            return Response({'detail': 'Kategoriya tanlang'}, status=400)
        try:
            category = LandCategory.objects.get(code=category_code)
        except LandCategory.DoesNotExist:
            return Response({'detail': f'Kategoriya topilmadi: {category_code}'}, status=400)

        if replace:
            PublicLand.objects.filter(category=category).delete()

        created = 0
        for i, (props, geom) in enumerate(records, start=1):
            if not geom:
                continue
            PublicLand.objects.create(
                category=category,
                name=pick_name(props, prefix, i),
                cadastral_number=str(props.get('osm_id') or props.get('id') or '')[:100],
                address='Buxoro shahri',
                description=f'[IMPORT] {source_name}',
                geometry=geom,
                status=PublicLand.Status.ACTIVE,
                is_active=True,
                created_by=request.user if request.user.is_authenticated else None,
            )
            created += 1

        return Response({
            'imported': created,
            'target': 'layer',
            'category': category.code,
            'replaced': replace,
            'source': source_name,
        })
