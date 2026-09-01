from datetime import timedelta

from django.db.models import Count, Q, Sum
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
from .geo_utils import geometry_centroid, to_feature, to_feature_collection
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
    search_fields = ['name_uz', 'name_ru', 'name_en', 'code']
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
    search_fields = ['name', 'name_ru', 'name_en', 'cadastral_number', 'address', 'address_ru', 'address_en', 'description', 'public_id', 'mahalla']
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
        mahalla = (request.query_params.get('mahalla') or '').strip()
        qs = PublicLand.objects.filter(is_active=True).select_related('category')
        if category:
            raw = str(category).strip()
            if raw.isdigit():
                qs = qs.filter(category_id=int(raw))
            else:
                qs = qs.filter(category__code=raw)
        if status_filter:
            qs = qs.filter(status=status_filter)
        if road_class:
            qs = qs.filter(road_class=road_class)
        if mahalla:
            qs = qs.filter(mahalla__iexact=mahalla)
        # year — monitoring yili bo'yicha filtr (0 yoki bo'sh yuborilmasin)
        if year not in (None, ''):
            try:
                y = int(year)
                if y > 0:
                    qs = qs.filter(monitoring_year=y)
            except (TypeError, ValueError):
                pass
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

    @action(detail=False, methods=['post'], parser_classes=[MultiPartParser, FormParser])
    def parse_geometry(self, request):
        uploaded = request.FILES.get('file')
        if not uploaded:
            return Response({'detail': 'Fayl yuboring'}, status=status.HTTP_400_BAD_REQUEST)
        from .import_utils import geometry_from_upload
        try:
            geom, source_name, count = geometry_from_upload(uploaded)
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({
            'geometry': geom,
            'source': source_name,
            'features': count,
        })


class CityBoundaryViewSet(viewsets.ModelViewSet):
    queryset = CityBoundary.objects.all()
    serializer_class = CityBoundarySerializer
    search_fields = ['name', 'code']
    filterset_fields = ['boundary_type', 'is_visible', 'monitoring_year']

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
        year_raw = request.query_params.get('year')
        if year_raw not in (None, ''):
            try:
                year = int(year_raw)
                if year > 0:
                    qs = qs.filter(
                        Q(monitoring_year=year) | Q(boundary_type=CityBoundary.BoundaryType.REGION),
                    )
            except (TypeError, ValueError):
                pass

        features = []
        for b in qs:
            features.append({
                'type': 'Feature',
                'id': b.id,
                'geometry': b.geometry,
                'properties': {
                    'id': b.id,
                    'code': b.code,
                    'monitoring_year': b.monitoring_year,
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
    search_fields = ['name', 'code']
    filterset_fields = ['is_active']

    def get_permissions(self):
        if self.action in ('list', 'retrieve', 'geojson'):
            return [AllowAny()]
        return [IsNotObserver()]

    @action(detail=False, methods=['get'], permission_classes=[AllowAny])
    def geojson(self, request):
        """Buxoro shahri MFY chegaralarini GeoJSON sifatida qaytaradi."""
        qs = Mahalla.objects.filter(is_active=True)
        code = (request.query_params.get('code') or '').strip()
        if code:
            qs = qs.filter(code__iexact=code)

        features = []
        for m in qs:
            if not m.geometry:
                continue
            centroid = geometry_centroid(m.geometry)
            props = {
                'id': m.id,
                'code': m.code,
                'name': m.name,
                'name_ru': m.name_ru,
                'name_en': m.name_en,
                'centroid': centroid,
            }
            features.append({
                'type': 'Feature',
                'id': m.id,
                'geometry': m.geometry,
                'properties': {**props, 'kind': 'area'},
            })
            if centroid:
                features.append({
                    'type': 'Feature',
                    'id': f'{m.id}-point',
                    'geometry': {'type': 'Point', 'coordinates': centroid},
                    'properties': {**props, 'kind': 'point'},
                })
        return Response({'type': 'FeatureCollection', 'features': features})


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

        from .monitoring_years import collect_monitoring_years

        years = collect_monitoring_years()
        return Response({
            'center': settings.BUKHARA_CENTER,
            'categories': LandCategorySerializer(
                LandCategory.objects.filter(is_active=True), many=True
            ).data,
            'years': years,
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

        from .bundle_import import import_bundle
        from .import_utils import (
            as_line_geometry, dissolve_city_geometry, find_shp,
            iter_geojson_features, pick_name, read_shapefile,
        )
        from .registry_utils import PublicIdSeq

        target = request.data.get('target', 'layer')  # layer | boundary
        mode = (request.data.get('mode') or 'single').strip().lower()
        category_code = request.data.get('category')
        replace = str(request.data.get('replace', '')).lower() in ('1', 'true', 'yes')
        prefix = (request.data.get('prefix') or 'Объект').strip() or 'Объект'
        year_raw = request.data.get('year')
        year = int(year_raw) if str(year_raw or '').isdigit() else None
        color = (request.data.get('color') or '').strip()
        uploaded = request.FILES.get('file')
        geojson_raw = request.data.get('geojson')

        records = []
        source_name = 'upload'

        def extract_zip(data, dest: Path):
            zpath = dest / 'upload.zip'
            zpath.write_bytes(data)
            with zipfile.ZipFile(zpath) as zf:
                dest_res = dest.resolve()
                for info in zf.infolist():
                    out = (dest / info.filename).resolve()
                    if not str(out).startswith(str(dest_res)):
                        continue
                    zf.extract(info, dest)

        if mode == 'bundle':
            if not uploaded:
                return Response({'detail': 'Загрузите ZIP со всеми shapefile'}, status=400)
            suffix = Path(uploaded.name).suffix.lower()
            if suffix != '.zip':
                return Response({'detail': 'Пакетный импорт принимает только .zip'}, status=400)
            with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
                tmp_path = Path(tmp)
                extract_zip(uploaded.read(), tmp_path)
                packed = import_bundle(
                    tmp_path,
                    year_fallback=year or 2026,
                    replace=replace,
                    user=request.user,
                )
            if not packed:
                return Response(
                    {'detail': 'В ZIP не найдено .shp файлов. Нужны группы .shp + .shx + .dbf.'},
                    status=400,
                )
            return Response({
                'mode': 'bundle',
                'imported': packed['imported'],
                'files': packed['files'],
                'replaced': replace,
                'layers': packed['layers'],
                'source': uploaded.name,
            })

        if uploaded:
            source_name = uploaded.name
            suffix = Path(uploaded.name).suffix.lower()
            if suffix == '.geojson' or suffix == '.json':
                try:
                    data = json.loads(uploaded.read().decode('utf-8'))
                except Exception:
                    return Response({'detail': 'Не удалось прочитать GeoJSON'}, status=400)
                records = list(iter_geojson_features(data))
            elif suffix in ('.zip', '.shp'):
                with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
                    tmp_path = Path(tmp)
                    if suffix == '.zip':
                        extract_zip(uploaded.read(), tmp_path)
                    else:
                        (tmp_path / uploaded.name).write_bytes(uploaded.read())
                    shp = find_shp(tmp_path)
                    if not shp:
                        return Response(
                            {'detail': 'В ZIP нет .shp. Нужны .shp + .shx + .dbf.'},
                            status=400,
                        )
                    records = list(read_shapefile(shp))
                    source_name = shp.name
            else:
                return Response(
                    {'detail': 'Допустимы .zip (shapefile), .shp или .geojson'},
                    status=400,
                )
        elif geojson_raw:
            try:
                data = json.loads(geojson_raw) if isinstance(geojson_raw, str) else geojson_raw
            except Exception:
                return Response({'detail': 'Некорректный GeoJSON'}, status=400)
            records = list(iter_geojson_features(data))
        else:
            return Response({'detail': 'Отправьте файл или GeoJSON'}, status=400)

        if not records:
            return Response({'detail': 'В файле нет геометрии'}, status=400)

        if target == 'boundary':
            props, _first = records[0]
            geom = dissolve_city_geometry([g for _, g in records if g])
            if not geom:
                return Response({'detail': 'В файле нет геометрии'}, status=400)
            code = request.data.get('boundary_code') or 'bukhara_city'
            name = pick_name(props, 'Chegara', 1)
            btype = request.data.get('boundary_type') or 'city'
            obj, _ = CityBoundary.objects.update_or_create(
                code=code,
                monitoring_year=year or 2026,
                defaults={
                    'name': name,
                    'boundary_type': btype,
                    'geometry': geom,
                    'is_visible': True,
                    'fill_opacity': 0.22,
                },
            )
            return Response({
                'imported': len(records),
                'target': 'boundary',
                'id': obj.id,
                'name': obj.name,
                'source': source_name,
            })

        if not category_code:
            return Response({'detail': 'Выберите категорию'}, status=400)
        try:
            category = LandCategory.objects.get(code=category_code)
        except LandCategory.DoesNotExist:
            return Response({'detail': f'Категория не найдена: {category_code}'}, status=400)

        if color and len(color) <= 7:
            category.color = color
            category.save(update_fields=['color'])

        if replace:
            qs = PublicLand.objects.filter(category=category)
            if year:
                qs = qs.filter(monitoring_year=year)
            qs.delete()

        created = 0
        from .bundle_import import park_class_from_props
        id_seqs = {}

        def next_public_id(road_class: str) -> str:
            key = road_class or ''
            if key not in id_seqs:
                id_seqs[key] = PublicIdSeq(category.code, key)
            return id_seqs[key].next()

        for i, (props, geom) in enumerate(records, start=1):
            if not geom:
                continue
            if category.geometry_type == LandCategory.GeometryType.LINE:
                geom = as_line_geometry(geom)
            road_class = ''
            if category.code in ('istirohat', 'park'):
                road_class = park_class_from_props(props)
            fclass_raw = props.get('fclass') or props.get('FCLASS') or road_class or ''
            PublicLand.objects.create(
                category=category,
                public_id=next_public_id(road_class),
                name=pick_name(props, prefix, i),
                cadastral_number=str(props.get('osm_id') or props.get('id') or props.get('OBJECTID') or '')[:100],
                address='Buxoro shahri',
                description=(
                    f'[IMPORT] {source_name}'
                    + (f' | {year}' if year else '')
                    + (f' | fclass={fclass_raw}' if fclass_raw else '')
                ),
                geometry=geom,
                status=PublicLand.Status.ACTIVE,
                is_active=True,
                monitoring_year=year or 2026,
                road_class=road_class or '',
                created_by=request.user if request.user.is_authenticated else None,
            )
            created += 1

        return Response({
            'imported': created,
            'target': 'layer',
            'category': category.code,
            'year': year,
            'color': category.color,
            'replaced': replace,
            'source': source_name,
        })


class ReverseGeocodeView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        import json
        import urllib.parse
        import urllib.request

        try:
            lat = float(request.query_params.get('lat'))
            lng = float(request.query_params.get('lng') or request.query_params.get('lon'))
        except (TypeError, ValueError):
            return Response({'label': ''}, status=status.HTTP_400_BAD_REQUEST)

        lang = request.query_params.get('lang') or 'uz'
        loc = 'ru' if lang == 'ru' else 'en' if lang == 'en' else 'uz'
        qs = urllib.parse.urlencode({
            'format': 'jsonv2',
            'lat': f'{lat:.6f}',
            'lon': f'{lng:.6f}',
            'accept-language': loc,
        })
        url = f'https://nominatim.openstreetmap.org/reverse?{qs}'
        req = urllib.request.Request(
            url,
            headers={
                'User-Agent': 'BuxoroGIS/1.0 (map reverse geocode)',
                'Accept': 'application/json',
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read().decode('utf-8'))
        except Exception:
            return Response({'label': 'Buxoro, O‘zbekiston'})

        addr = data.get('address') or {}
        parts = [
            addr.get('road') or addr.get('pedestrian') or addr.get('residential'),
            addr.get('neighbourhood') or addr.get('suburb') or addr.get('village'),
            addr.get('city') or addr.get('town') or addr.get('county') or addr.get('state'),
        ]
        seen = []
        for p in parts:
            if p and p not in seen:
                seen.append(p)
        label = ', '.join(seen) or data.get('display_name') or 'Buxoro, O‘zbekiston'
        return Response({'label': label})
