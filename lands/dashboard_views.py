from django.db.models import Count, Sum
from django.utils import timezone
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import viewsets

from accounts.permissions import IsNotObserver
from monitoring.models import ChangeLog, Issue
from monitoring.serializers import ChangeLogSerializer, IssueSerializer

from .models import (
    LandCategory,
    MonitoringRecord,
    MonitoringYear,
    ObjectVersion,
    PublicLand,
    SystemNotice,
    UrbanizationLayer,
)
from .registry_utils import m_to_km, sqm_to_ha
from .serializers import (
    MonitoringRecordSerializer,
    MonitoringYearSerializer,
    ObjectVersionSerializer,
    SystemNoticeSerializer,
    UrbanizationLayerSerializer,
)


MONITORING_YEARS = [2018, 2020, 2022, 2024, 2026]
URBAN_YEARS = [2000, 2005, 2010, 2015, 2020, 2025]
RESEARCH_CODES = ['yollar', 'suv', 'istirohat', 'park', 'qabriston']
CATEGORY_NAMES = {
    'yollar': "Avtomobil yo'llari",
    'suv': "Sug'orish tarmoqlari",
    'istirohat': "Istirohat bog'lari",
    'park': "Istirohat bog'lari",
    'qabriston': 'Qabristonlar',
}


YEAR_SCALE = {2018: 0.78, 2020: 0.85, 2022: 0.91, 2024: 0.96, 2025: 0.98, 2026: 1.0}
ROAD_ONLY = {'magistral', 'shahar', 'mahalliy', 'piyoda'}


def _scale_for(year):
    return YEAR_SCALE.get(int(year), 1.0)


def _agg_lands(qs, scale=1.0):
    total_objects = qs.count()
    total_area = (qs.aggregate(s=Sum('area_sqm'))['s'] or 0) * scale
    roads = qs.filter(category__code='yollar')
    water = qs.filter(category__code='suv')
    parks = qs.filter(category__code__in=['park', 'istirohat'])
    cemeteries = qs.filter(category__code='qabriston')

    roads_m = (roads.aggregate(s=Sum('length_m'))['s'] or 0) * scale
    water_m = (water.aggregate(s=Sum('length_m'))['s'] or 0) * scale
    parks_area = (parks.aggregate(s=Sum('area_sqm'))['s'] or 0) * scale
    cem_area = (cemeteries.aggregate(s=Sum('area_sqm'))['s'] or 0) * scale

    def sc_count(n):
        return n if scale >= 0.999 else int(round(n * scale))

    by_category = []
    for row in (
        qs.values(
            'category__code', 'category__name_uz', 'category__name_ru',
            'category__name_en', 'category__color',
        )
        .annotate(count=Count('id'), total_area=Sum('area_sqm'), total_length=Sum('length_m'))
        .order_by('-count')
    ):
        by_category.append({
            'code': row['category__code'],
            'name': row['category__name_uz'],
            'name_uz': row['category__name_uz'],
            'name_ru': row['category__name_ru'],
            'name_en': row['category__name_en'],
            'color': row['category__color'],
            'count': sc_count(row['count']),
            'area_ha': sqm_to_ha((row['total_area'] or 0) * scale),
            'length_km': m_to_km((row['total_length'] or 0) * scale),
        })

    by_status = [
        {'code': row['status'] or 'unknown', 'count': sc_count(row['count'])}
        for row in qs.values('status').annotate(count=Count('id')).order_by('-count')
    ]
    by_condition = [
        {'code': row['condition'] or 'unknown', 'count': sc_count(row['count'])}
        for row in qs.values('condition').annotate(count=Count('id')).order_by('-count')
    ]

    road_by_class = []
    for code, label in PublicLand.RoadClass.choices:
        if code not in ROAD_ONLY:
            continue
        length = roads.filter(road_class=code).aggregate(s=Sum('length_m'))['s'] or 0
        cnt = roads.filter(road_class=code).count()
        if length or cnt:
            road_by_class.append({
                'code': code,
                'name': label,
                'count': sc_count(cnt),
                'length_km': m_to_km(length * scale),
            })

    water_by_class = []
    for code in ('kanal', 'ariq'):
        length = water.filter(road_class=code).aggregate(s=Sum('length_m'))['s'] or 0
        cnt = water.filter(road_class=code).count()
        if length or cnt:
            water_by_class.append({
                'code': code,
                'count': sc_count(cnt),
                'length_km': m_to_km(length * scale),
            })

    park_by_class = []
    for code in ('park', 'xiyobon', 'square'):
        area = parks.filter(road_class=code).aggregate(s=Sum('area_sqm'))['s'] or 0
        cnt = parks.filter(road_class=code).count()
        if area or cnt:
            park_by_class.append({
                'code': code,
                'count': sc_count(cnt),
                'area_ha': sqm_to_ha(area * scale),
            })

    by_mahalla = []
    for row in (
        qs.exclude(mahalla='')
        .values('mahalla')
        .annotate(count=Count('id'), total_area=Sum('area_sqm'), total_length=Sum('length_m'))
        .order_by('-count')[:20]
    ):
        by_mahalla.append({
            'name': row['mahalla'],
            'count': sc_count(row['count']),
            'area_ha': sqm_to_ha((row['total_area'] or 0) * scale),
            'length_km': m_to_km((row['total_length'] or 0) * scale),
        })

    return {
        'kpis': {
            'total_objects': sc_count(total_objects),
            'total_area_ha': sqm_to_ha(total_area),
            'roads_length_km': m_to_km(roads_m),
            'roads_count': sc_count(roads.count()),
            'water_length_km': m_to_km(water_m),
            'water_count': sc_count(water.count()),
            'parks_count': sc_count(parks.count()),
            'parks_area_ha': sqm_to_ha(parks_area),
            'cemeteries_count': sc_count(cemeteries.count()),
            'cemeteries_area_ha': sqm_to_ha(cem_area),
            'empty_mahalla_count': sc_count(qs.filter(mahalla='').count()),
        },
        'by_category': by_category,
        'by_status': by_status,
        'by_condition': by_condition,
        'road_by_class': road_by_class,
        'water_by_class': water_by_class,
        'park_by_class': park_by_class,
        'by_mahalla': by_mahalla,
    }


class DashboardView(APIView):
    """KPI + atributlar statistikasi, yil filtri bilan."""

    permission_classes = [AllowAny]

    def get(self, request):
        year_raw = request.query_params.get('year', '')
        try:
            year = int(year_raw) if str(year_raw).strip() else None
        except (TypeError, ValueError):
            year = None

        base = PublicLand.objects.filter(
            is_active=True,
            category__code__in=RESEARCH_CODES,
        ).select_related('category')

        db_years = list(
            PublicLand.objects.filter(is_active=True)
            .values_list('monitoring_year', flat=True)
            .distinct()
            .order_by('monitoring_year')
        )
        years = sorted(set(MONITORING_YEARS) | {int(y) for y in db_years if y})
        if not years:
            years = list(MONITORING_YEARS)

        if year is None:
            year = max(db_years) if db_years else max(years)

        exact = base.filter(monitoring_year=year)
        if exact.exists():
            payload = _agg_lands(exact, scale=1.0)
            mode = 'exact'
        else:
            versions = ObjectVersion.objects.filter(
                year=year,
                land__category__code__in=RESEARCH_CODES,
            )
            if versions.exists():
                land_ids = versions.values_list('land_id', flat=True)
                payload = _agg_lands(base.filter(id__in=land_ids), scale=1.0)
                mode = 'versions'
            else:
                max_y = max(db_years) if db_years else year
                current = base.filter(monitoring_year=max_y) if base.filter(monitoring_year=max_y).exists() else base
                payload = _agg_lands(current, scale=_scale_for(year))
                mode = 'scaled'

        area_dynamics = []
        length_dynamics = []
        max_y = max(db_years) if db_years else 2026
        current = base.filter(monitoring_year=max_y) if base.filter(monitoring_year=max_y).exists() else base
        cur_area = current.aggregate(s=Sum('area_sqm'))['s'] or 0
        cur_road = current.filter(category__code='yollar').aggregate(s=Sum('length_m'))['s'] or 0
        cur_water = current.filter(category__code='suv').aggregate(s=Sum('length_m'))['s'] or 0
        for y in years:
            vers = ObjectVersion.objects.filter(year=y)
            if vers.exists():
                a = vers.aggregate(s=Sum('area_sqm'))['s'] or 0
                rl = vers.filter(land__category__code='yollar').aggregate(s=Sum('length_m'))['s'] or 0
                wl = vers.filter(land__category__code='suv').aggregate(s=Sum('length_m'))['s'] or 0
            elif base.filter(monitoring_year=y).exists():
                qs = base.filter(monitoring_year=y)
                a = qs.aggregate(s=Sum('area_sqm'))['s'] or 0
                rl = qs.filter(category__code='yollar').aggregate(s=Sum('length_m'))['s'] or 0
                wl = qs.filter(category__code='suv').aggregate(s=Sum('length_m'))['s'] or 0
            else:
                sc = _scale_for(y)
                a = cur_area * sc
                rl = cur_road * sc
                wl = cur_water * sc
            area_dynamics.append({'year': y, 'area_ha': sqm_to_ha(a)})
            length_dynamics.append({
                'year': y,
                'roads_km': m_to_km(rl),
                'water_km': m_to_km(wl),
            })

        notice = SystemNotice.objects.filter(is_active=True).first()
        current_year = MonitoringYear.objects.filter(
            year_type=MonitoringYear.YearType.MONITORING, is_current=True,
        ).first()
        recent_changes = ChangeLogSerializer(
            ChangeLog.objects.select_related('land', 'changed_by')[:8],
            many=True,
        ).data
        monitoring_records = MonitoringRecordSerializer(
            MonitoringRecord.objects.select_related('land')[:8],
            many=True,
        ).data

        return Response({
            'project': {
                'name': 'Buxoro GIS',
                'title': 'Buxoro shahri umumiy foydalanishdagi yer obyektlarining elektron reyestri',
                'city': 'Buxoro',
            },
            'meta': {
                'selected_year': year,
                'data_mode': mode,
                'current_monitoring_year': current_year.year if current_year else max_y,
                'last_updated': timezone.now().isoformat(),
                'monitoring_years': years,
                'years': years,
                'db_years': db_years,
            },
            'notice': SystemNoticeSerializer(notice).data if notice else None,
            **payload,
            'area_dynamics': area_dynamics,
            'length_dynamics': length_dynamics,
            'recent_changes': recent_changes,
            'monitoring_records': monitoring_records,
        })

class CompareYearsView(APIView):
    """Сравнение двух годов мониторинга."""

    permission_classes = [AllowAny]

    def get(self, request):
        year_a = int(request.query_params.get('year_a', 2018))
        year_b = int(request.query_params.get('year_b', 2026))

        def snapshot(year):
            versions = ObjectVersion.objects.filter(
                year=year,
                land__category__code__in=RESEARCH_CODES,
            ).select_related('land', 'land__category')
            if versions.exists():
                return {
                    v.land_id: {
                        'id': v.land_id,
                        'public_id': v.land.public_id,
                        'name': v.land.name,
                        'category': v.land.category.code,
                        'area_ha': sqm_to_ha(v.area_sqm),
                        'length_km': m_to_km(v.length_m),
                    }
                    for v in versions
                }
            scale = {2018: 0.78, 2020: 0.85, 2022: 0.91, 2024: 0.96, 2026: 1.0}.get(year, 1.0)
            out = {}
            for land in PublicLand.objects.filter(
                is_active=True,
                category__code__in=RESEARCH_CODES,
            ).select_related('category'):
                out[land.id] = {
                    'id': land.id,
                    'public_id': land.public_id,
                    'name': land.name,
                    'category': land.category.code,
                    'area_ha': round(sqm_to_ha(land.area_sqm) * scale, 4),
                    'length_km': round(m_to_km(land.length_m) * scale, 3),
                }
            return out

        a = snapshot(year_a)
        b = snapshot(year_b)
        ids_a, ids_b = set(a), set(b)

        expanded, shrunk, new_objects, disappeared, stable = [], [], [], [], []
        for lid in ids_a & ids_b:
            da = b[lid]['area_ha'] - a[lid]['area_ha']
            dl = b[lid]['length_km'] - a[lid]['length_km']
            item = {
                **b[lid],
                'area_a': a[lid]['area_ha'],
                'area_b': b[lid]['area_ha'],
                'delta_ha': round(da, 4),
                'length_a': a[lid]['length_km'],
                'length_b': b[lid]['length_km'],
                'delta_km': round(dl, 3),
            }
            if da > 0.01 or dl > 0.01:
                expanded.append(item)
            elif da < -0.01 or dl < -0.01:
                shrunk.append(item)
            else:
                stable.append(item)

        for lid in ids_b - ids_a:
            new_objects.append(b[lid])
        for lid in ids_a - ids_b:
            disappeared.append(a[lid])

        expanded.sort(key=lambda x: x['delta_ha'], reverse=True)
        shrunk.sort(key=lambda x: x['delta_ha'])

        total_a = sum(x['area_ha'] for x in a.values())
        total_b = sum(x['area_ha'] for x in b.values())
        len_a = sum(x['length_km'] for x in a.values())
        len_b = sum(x['length_km'] for x in b.values())
        delta = total_b - total_a
        pct = round((delta / total_a * 100) if total_a else 0, 2)

        by_cat = {}
        for src, key in ((a, 'a'), (b, 'b')):
            for row in src.values():
                code = 'istirohat' if row['category'] == 'park' else row['category']
                bucket = by_cat.setdefault(code, {
                    'code': code,
                    'name': CATEGORY_NAMES.get(code, code),
                    'area_a': 0, 'area_b': 0,
                    'length_a': 0, 'length_b': 0,
                    'count_a': 0, 'count_b': 0,
                })
                bucket[f'area_{key}'] += row['area_ha']
                bucket[f'length_{key}'] += row['length_km']
                bucket[f'count_{key}'] += 1
        by_category = []
        for code in ['yollar', 'suv', 'istirohat', 'qabriston']:
            row = by_cat.get(code)
            if not row:
                continue
            row['area_a'] = round(row['area_a'], 4)
            row['area_b'] = round(row['area_b'], 4)
            row['delta_ha'] = round(row['area_b'] - row['area_a'], 4)
            row['length_a'] = round(row['length_a'], 3)
            row['length_b'] = round(row['length_b'], 3)
            row['delta_km'] = round(row['length_b'] - row['length_a'], 3)
            by_category.append(row)

        return Response({
            'year_a': year_a,
            'year_b': year_b,
            'summary': {
                'total_area_a_ha': round(total_a, 4),
                'total_area_b_ha': round(total_b, 4),
                'delta_ha': round(delta, 4),
                'delta_pct': pct,
                'total_length_a_km': round(len_a, 3),
                'total_length_b_km': round(len_b, 3),
                'delta_km': round(len_b - len_a, 3),
                'expanded_count': len(expanded),
                'shrunk_count': len(shrunk),
                'new_count': len(new_objects),
                'disappeared_count': len(disappeared),
                'stable_count': len(stable),
            },
            'by_category': by_category,
            'expanded': expanded[:80],
            'shrunk': shrunk[:80],
            'new_objects': new_objects[:80],
            'disappeared': disappeared[:80],
        })


class UrbanizationView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        year = request.query_params.get('year')
        qs = UrbanizationLayer.objects.filter(is_visible=True)
        if year:
            qs = qs.filter(year=int(year))

        layers = UrbanizationLayerSerializer(qs, many=True).data
        by_year = {}
        for layer in qs:
            by_year.setdefault(layer.year, {'year': layer.year, 'urban_ha': 0, 'agriculture_ha': 0, 'other_ha': 0})
            if layer.layer_kind == 'urban':
                by_year[layer.year]['urban_ha'] += layer.area_ha
            elif layer.layer_kind == 'agriculture':
                by_year[layer.year]['agriculture_ha'] += layer.area_ha
            else:
                by_year[layer.year]['other_ha'] += layer.area_ha

        # если нет данных — синтетика по ТЗ
        if not by_year:
            for y in URBAN_YEARS:
                t = (y - 2000) / 25
                by_year[y] = {
                    'year': y,
                    'urban_ha': round(4200 + t * 2445.6, 1),
                    'agriculture_ha': round(3200 - t * 1045.8, 1),
                    'other_ha': round(800 - t * 200, 1),
                }

        series = [by_year[y] for y in sorted(by_year)]
        latest = series[-1] if series else {}
        return Response({
            'years': URBAN_YEARS,
            'layers': layers,
            'series': series,
            'summary': {
                'urban_ha': latest.get('urban_ha', 6645.6),
                'agriculture_ha': latest.get('agriculture_ha', 2154.2),
                'period': '2000–2025',
            },
        })


class MonitoringYearViewSet(viewsets.ModelViewSet):
    queryset = MonitoringYear.objects.all()
    serializer_class = MonitoringYearSerializer
    search_fields = ['note']
    filterset_fields = ['year_type', 'is_current', 'is_active']

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return [AllowAny()]
        return [IsNotObserver()]

    def get_queryset(self):
        qs = MonitoringYear.objects.all().order_by('-year')
        if self.action in ('list', 'retrieve') and not (
            self.request.user and self.request.user.is_authenticated
            and (getattr(self.request.user, 'is_superuser', False) or getattr(self.request.user, 'role', None) == 'admin')
        ):
            qs = qs.filter(is_active=True)
        return qs


class ObjectVersionViewSet(viewsets.ModelViewSet):
    queryset = ObjectVersion.objects.select_related('land', 'land__category')
    serializer_class = ObjectVersionSerializer
    search_fields = ['land__public_id', 'land__name', 'change_note']
    filterset_fields = ['land', 'year', 'status']

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return [AllowAny()]
        return [IsNotObserver()]


class MonitoringRecordViewSet(viewsets.ModelViewSet):
    queryset = MonitoringRecord.objects.select_related('land', 'recorded_by')
    serializer_class = MonitoringRecordSerializer
    permission_classes = [IsNotObserver]
    filterset_fields = ['year', 'status', 'land']
    search_fields = ['description', 'land__public_id', 'land__name']

    def perform_create(self, serializer):
        serializer.save(recorded_by=self.request.user)


class UrbanizationLayerViewSet(viewsets.ModelViewSet):
    queryset = UrbanizationLayer.objects.all()
    serializer_class = UrbanizationLayerSerializer
    search_fields = ['name', 'note']
    filterset_fields = ['year', 'layer_kind', 'is_visible']

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return [AllowAny()]
        return [IsNotObserver()]

    def get_queryset(self):
        qs = UrbanizationLayer.objects.all().order_by('-year', 'name')
        if self.action in ('list', 'retrieve') and not (
            self.request.user and self.request.user.is_authenticated
            and (getattr(self.request.user, 'is_superuser', False) or getattr(self.request.user, 'role', None) == 'admin')
        ):
            qs = qs.filter(is_visible=True)
        return qs

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        if request.query_params.get('format') == 'geojson':
            features = []
            for layer in self.filter_queryset(self.get_queryset()):
                if not layer.geometry:
                    continue
                features.append({
                    'type': 'Feature',
                    'id': layer.id,
                    'geometry': layer.geometry,
                    'properties': {
                        'id': layer.id,
                        'name': layer.name,
                        'year': layer.year,
                        'layer_kind': layer.layer_kind,
                        'area_ha': layer.area_ha,
                        'growth_pct': layer.growth_pct,
                        'color': layer.color,
                    },
                })
            return Response({'type': 'FeatureCollection', 'features': features})
        return response
