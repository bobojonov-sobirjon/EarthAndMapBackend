"""
ТЗ: годы мониторинга, версии объектов, урбанизация, категории suv/maydon/xiyobon,
публичные ID и сообщения администратора.
"""
from django.core.management.base import BaseCommand

from lands.models import (
    LandCategory,
    MonitoringRecord,
    MonitoringYear,
    ObjectVersion,
    PublicLand,
    SystemNotice,
    UrbanizationLayer,
)
from lands.registry_utils import next_public_id


EXTRA_CATEGORIES = [
    ('suv', 'Suv tarmoqlari', 'Водные сети', 'LineString', '#3498db', 11),
    ('maydon', 'Maydonlar', 'Площади', 'Polygon', '#9b59b6', 12),
    ('xiyobon', 'Xiyobonlar', 'Бульвары', 'Polygon', '#1abc9c', 13),
]

MONITORING_YEARS = [2018, 2020, 2022, 2024, 2026]
URBAN_YEARS = [2000, 2005, 2010, 2015, 2020, 2025]
SCALES = {2018: 0.78, 2020: 0.85, 2022: 0.91, 2024: 0.96, 2026: 1.0}


class Command(BaseCommand):
    help = 'Заполнение данных по ТЗ Buxoro GIS (годы, версии, урбанизация)'

    def handle(self, *args, **options):
        self.stdout.write('Категории (suv, maydon, xiyobon)...')
        for code, name_uz, name_ru, geom, color, order in EXTRA_CATEGORIES:
            LandCategory.objects.update_or_create(
                code=code,
                defaults={
                    'name_uz': name_uz,
                    'name_ru': name_ru,
                    'geometry_type': geom,
                    'color': color,
                    'order': order,
                    'is_active': True,
                },
            )

        self.stdout.write('Годы мониторинга / урбанизации...')
        MonitoringYear.objects.all().delete()
        for y in MONITORING_YEARS:
            MonitoringYear.objects.create(
                year=y,
                year_type=MonitoringYear.YearType.MONITORING,
                is_current=(y == 2026),
            )
        for y in URBAN_YEARS:
            MonitoringYear.objects.create(
                year=y,
                year_type=MonitoringYear.YearType.URBANIZATION,
                is_current=(y == 2025),
            )

        self.stdout.write('Публичные ID объектов...')
        road_cycle = ['magistral', 'shahar', 'mahalliy', 'piyoda']
        roads = list(PublicLand.objects.filter(category__code='yollar', is_active=True))
        for i, land in enumerate(roads):
            land.road_class = road_cycle[i % len(road_cycle)]
            land.monitoring_year = 2026
            if not land.public_id:
                land.public_id = next_public_id('yollar', land.road_class)
            land.save()

        for land in PublicLand.objects.filter(is_active=True).exclude(category__code='yollar'):
            land.monitoring_year = 2026
            if not land.public_id:
                land.public_id = next_public_id(land.category.code)
            if not land.mahalla:
                land.mahalla = 'Марказий'
            land.save()

        self.stdout.write('Версии объектов по годам...')
        ObjectVersion.objects.all().delete()
        created_v = 0
        for land in PublicLand.objects.filter(is_active=True).iterator():
            for y in MONITORING_YEARS:
                scale = SCALES[y]
                area = (land.area_sqm or 0) * scale if land.area_sqm else None
                length = (land.length_m or 0) * scale if land.length_m else None
                ObjectVersion.objects.create(
                    land=land,
                    year=y,
                    geometry=land.geometry,
                    area_sqm=area,
                    length_m=length,
                    status=land.status,
                    condition=land.condition or 'good',
                    change_note=f'Снимок {y}',
                )
                created_v += 1
        self.stdout.write(f'  версий: {created_v}')

        self.stdout.write('Записи мониторинга...')
        MonitoringRecord.objects.all().delete()
        sample = PublicLand.objects.filter(is_active=True, category__code__in=['park', 'istirohat'])[:5]
        for land in sample:
            MonitoringRecord.objects.create(
                land=land,
                year=2026,
                description=f'Площадь объекта {land.public_id} расширена',
                delta_area_ha=0.15,
                status=MonitoringRecord.RecordStatus.APPROVED,
            )

        self.stdout.write('Слои урбанизации...')
        UrbanizationLayer.objects.all().delete()
        for y in URBAN_YEARS:
            t = (y - 2000) / 25
            UrbanizationLayer.objects.create(
                year=y,
                name=f'Городская территория {y}',
                layer_kind=UrbanizationLayer.LayerKind.URBAN,
                area_ha=round(4200 + t * 2445.6, 1),
                growth_pct=round(t * 58.2, 1),
                color='#e74c3c',
                geometry={
                    'type': 'Polygon',
                    'coordinates': [[
                        [64.38 + t * 0.02, 39.74],
                        [64.50 + t * 0.03, 39.74],
                        [64.50 + t * 0.03, 39.82],
                        [64.38 + t * 0.02, 39.82],
                        [64.38 + t * 0.02, 39.74],
                    ]],
                },
            )
            UrbanizationLayer.objects.create(
                year=y,
                name=f'Сельхозугодья {y}',
                layer_kind=UrbanizationLayer.LayerKind.AGRICULTURE,
                area_ha=round(3200 - t * 1045.8, 1),
                growth_pct=round(-t * 32.7, 1),
                color='#27ae60',
            )

        SystemNotice.objects.update_or_create(
            title='Добро пожаловать в Buxoro GIS',
            defaults={
                'message': (
                    'Система электронного реестра и геоинформационного мониторинга '
                    'земель общего пользования города Бухары. Текущий год мониторинга: 2026.'
                ),
                'is_active': True,
            },
        )

        # демо водных сетей если пусто
        suv = LandCategory.objects.get(code='suv')
        if not PublicLand.objects.filter(category=suv).exists():
            PublicLand.objects.create(
                category=suv,
                name='Канал Шахристан',
                geometry={
                    'type': 'LineString',
                    'coordinates': [[64.40, 39.77], [64.42, 39.775], [64.45, 39.78]],
                },
                status='active',
                address='г. Бухара',
                monitoring_year=2026,
                data_source='ТЗ demo',
            )

        self.stdout.write(self.style.SUCCESS('seed_tt_data завершён'))
