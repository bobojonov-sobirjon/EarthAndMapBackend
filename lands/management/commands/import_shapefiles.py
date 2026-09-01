"""
16.02.2026 shapefile papkasidan Buxoro shahar obyektlarini import qilish.

Foydalanish:
  python manage.py import_shapefiles
  python manage.py import_shapefiles --path "C:\\...\\16.02.2026"
  python manage.py import_shapefiles --skip-roads
"""
from pathlib import Path

import shapefile
from django.core.management.base import BaseCommand

from lands.boundary_data import BUKHARA_REGION
from lands.models import CityBoundary, LandCategory, PublicLand

# Shapefile nomi → (category_code, default_name_prefix)
LAYER_MAP = [
    ('MAKTABLAR_43', 'maktab', 'Maktab'),
    ('BOZORLAR_10', 'bozor', 'Bozor'),
    ('ISTROXAT_MAYDONLAR_16', 'istirohat', 'Istirohat maydoni'),
    ('QABRISTON_21', 'qabriston', 'Qabriston'),
    ('STADION_2', 'stadion', 'Stadion'),
    ('KUTUBXONA_1', 'kutubxona', 'Kutubxona'),
    ('gis_osm_pofw_a_maschit_Clip', 'masjid', 'Masjid'),
    ('gis_osm_pois_a_ExportFeature3', 'sport', 'Sport markazi'),
]

ROADS_SHP = 'gis_osm_roads__ExportFe_Clip'
BOUNDARY_SHP = 'Bukhara_area'

CATEGORIES = [
    # code, name_uz, name_ru, geometry_type, color, order
    ('yollar', "Yo'llar va ko'chalar", 'Дороги и улицы', 'LineString', '#9b59b6', 1),
    ('istirohat', 'Istirohat maydonlari', 'Зоны отдыха', 'Polygon', '#27ae60', 2),
    ('qabriston', 'Qabristonlar', 'Кладбища', 'Polygon', '#7f8c8d', 3),
    ('stadion', 'Stadionlar', 'Стадионы', 'Polygon', '#e67e22', 4),
    ('kutubxona', 'Kutubxonalar', 'Библиотеки', 'Point', '#3498db', 5),
    ('bozor', 'Bozorlar', 'Рынки', 'Polygon', '#8e2430', 6),
    ('sport', 'Sport markazlari', 'Спортивные центры', 'Polygon', '#1abc9c', 7),
    ('maktab', 'Maktablar', 'Школы', 'Polygon', '#c0392b', 8),
    ('masjid', 'Masjidlar', 'Мечети', 'Polygon', '#2c3e50', 9),
    ('park', 'Parklar va yashil hududlar', 'Парки и зелёные зоны', 'Polygon', '#2ecc71', 10),
]


def shape_to_geojson(shape):
    """pyshp shape → GeoJSON geometry (Polygon / MultiPolygon / LineString / MultiLineString)."""
    parts = list(shape.parts) + [len(shape.points)]
    rings = []
    for i in range(len(parts) - 1):
        ring = [[float(x), float(y)] for x, y in shape.points[parts[i]:parts[i + 1]]]
        if ring:
            rings.append(ring)

    st = shape.shapeType
    # POLYLINE = 3, POLYGON = 5
    if st in (shapefile.POLYLINE, shapefile.POLYLINEM, shapefile.POLYLINEZ, 3):
        if len(rings) == 1:
            return {'type': 'LineString', 'coordinates': rings[0]}
        return {'type': 'MultiLineString', 'coordinates': rings}

    # Polygon: first ring exterior, others holes — for MultiPolygon we treat each part
    # with orientation; ArcGIS often exports single-part or multi exterior rings.
    if len(rings) == 1:
        return {'type': 'Polygon', 'coordinates': rings}
    # Multiple rings without hole metadata → MultiPolygon of single-ring polygons
    return {'type': 'MultiPolygon', 'coordinates': [[ring] for ring in rings]}


def read_records(shp_path):
    reader = shapefile.Reader(str(shp_path), encoding='utf-8')
    fields = [f[0] for f in reader.fields[1:]]
    for sr in reader.iterShapeRecords():
        props = dict(zip(fields, sr.record))
        yield props, shape_to_geojson(sr.shape)


class Command(BaseCommand):
    help = '16.02.2026 shapefile laridan Buxoro GIS ma\'lumotlarini import qilish'

    def add_arguments(self, parser):
        parser.add_argument(
            '--path',
            default=r'C:\Users\asus\Downloads\Telegram Desktop\16.02.2026\16.02.2026',
            help='Shapefile papkasi yo\'li',
        )
        parser.add_argument('--skip-roads', action='store_true', help="Yo'llarni o'tkazib yuborish")
        parser.add_argument('--clear', action='store_true', help='Import oldidan demo/eski obyektlarni tozalash')

    def handle(self, *args, **options):
        root = Path(options['path'])
        if not root.exists():
            self.stderr.write(self.style.ERROR(f'Papka topilmadi: {root}'))
            return

        cat_objs = self.ensure_categories()
        if options['clear']:
            deleted, _ = PublicLand.objects.all().delete()
            self.stdout.write(f'Obyektlar tozalandi: {deleted}')

        self.import_boundary(root)
        self.import_region_boundary()

        total = 0
        for shp_name, cat_code, prefix in LAYER_MAP:
            path = root / f'{shp_name}.shp'
            if not path.exists():
                self.stdout.write(self.style.WARNING(f'Yo\'q: {shp_name}.shp'))
                continue
            n = self.import_layer(path, cat_objs[cat_code], prefix)
            total += n
            self.stdout.write(self.style.SUCCESS(f'{shp_name}: {n} obyekt'))

        # Sport markazlari POI Clip dan (agar ExportFeature3 bo'sh bo'lsa)
        if PublicLand.objects.filter(category=cat_objs['sport']).count() == 0:
            poi = root / 'gis_osm_pois_a_ExportFe_Clip.shp'
            if poi.exists():
                n = self.import_poi_by_fclass(poi, cat_objs['sport'], ['sports_centre'], 'Sport markazi')
                total += n
                self.stdout.write(self.style.SUCCESS(f'sports_centre: {n}'))

        # Parklar
        poi = root / 'gis_osm_pois_a_ExportFe_Clip.shp'
        if poi.exists():
            n = self.import_poi_by_fclass(poi, cat_objs['park'], ['park'], 'Park')
            total += n
            self.stdout.write(self.style.SUCCESS(f'park: {n}'))

        if not options['skip_roads']:
            roads = root / f'{ROADS_SHP}.shp'
            if roads.exists():
                n = self.import_roads(roads, cat_objs['yollar'])
                total += n
                self.stdout.write(self.style.SUCCESS(f'{ROADS_SHP}: {n} yo\'l'))

        self.stdout.write(self.style.SUCCESS(f'Jami import: {total} obyekt'))

    def ensure_categories(self):
        objs = {}
        for code, name_uz, name_ru, geom_type, color, order in CATEGORIES:
            obj, _ = LandCategory.objects.update_or_create(
                code=code,
                defaults={
                    'name_uz': name_uz,
                    'name_ru': name_ru,
                    'geometry_type': geom_type,
                    'color': color,
                    'order': order,
                    'is_active': True,
                },
            )
            objs[code] = obj
        return objs

    def import_boundary(self, root):
        """Shahar chegarasi — OSM/import_bukhara_city orqali alohida yuklanadi."""
        path = root / f'{BOUNDARY_SHP}.shp'
        if path.exists():
            self.stdout.write(self.style.WARNING(
                'Bukhara_area.shp o\'tkazib yuborildi — '
                'shahar chegarasi uchun: python manage.py import_bukhara_city'
            ))
        return

    def import_region_boundary(self):
        CityBoundary.objects.update_or_create(
            code='bukhara_region',
            monitoring_year=2026,
            defaults={
                'name': 'Buxoro viloyati',
                'boundary_type': CityBoundary.BoundaryType.REGION,
                'geometry': BUKHARA_REGION,
                'color': '#e74c3c',
                'weight': 3,
                'dash_array': '12 8',
                'fill_opacity': 0.02,
                'order': 1,
                'is_visible': True,
            },
        )
        self.stdout.write(self.style.SUCCESS('Viloyat chegarasi yuklandi'))

    def import_layer(self, path, category, prefix):
        count = 0
        # Avval shu kategoriya importini tozalash (qayta import uchun)
        PublicLand.objects.filter(category=category, description__startswith='[SHP]').delete()
        for i, (props, geom) in enumerate(read_records(path), start=1):
            raw_name = (props.get('name') or '').strip()
            name = raw_name if raw_name else f'{prefix} #{i}'
            osm_id = props.get('osm_id')
            PublicLand.objects.create(
                category=category,
                name=name[:255],
                cadastral_number=str(osm_id) if osm_id else '',
                address='Buxoro shahri',
                description=f'[SHP] {path.stem} | fclass={props.get("fclass", "")}',
                geometry=geom,
                status=PublicLand.Status.ACTIVE,
                is_active=True,
            )
            count += 1
        return count

    def import_poi_by_fclass(self, path, category, fclasses, prefix):
        PublicLand.objects.filter(category=category, description__startswith='[SHP]').delete()
        count = 0
        for i, (props, geom) in enumerate(read_records(path), start=1):
            if props.get('fclass') not in fclasses:
                continue
            count += 1
            raw_name = (props.get('name') or '').strip()
            name = raw_name if raw_name else f'{prefix} #{count}'
            osm_id = props.get('osm_id')
            PublicLand.objects.create(
                category=category,
                name=name[:255],
                cadastral_number=str(osm_id) if osm_id else '',
                address='Buxoro shahri',
                description=f'[SHP] {path.stem} | fclass={props.get("fclass", "")}',
                geometry=geom,
                status=PublicLand.Status.ACTIVE,
                is_active=True,
            )
        return count

    def import_roads(self, path, category):
        PublicLand.objects.filter(category=category, description__startswith='[SHP]').delete()
        count = 0
        # Asosiy ko'cha tarmog'i (service/footway og'ir — o'tkazib yuboriladi)
        priority = {
            'motorway', 'trunk', 'primary', 'secondary', 'tertiary',
            'residential', 'unclassified', 'trunk_link', 'primary_link', 'secondary_link',
        }
        for i, (props, geom) in enumerate(read_records(path), start=1):
            fclass = props.get('fclass') or ''
            if fclass not in priority:
                continue
            raw_name = (props.get('name') or '').strip()
            name = raw_name if raw_name else f"{fclass or 'yo\'l'} #{i}"
            osm_id = props.get('osm_id')
            PublicLand.objects.create(
                category=category,
                name=name[:255],
                cadastral_number=str(osm_id) if osm_id else '',
                address='Buxoro shahri',
                description=f'[SHP] {path.stem} | fclass={fclass}',
                geometry=geom,
                status=PublicLand.Status.ACTIVE,
                is_active=True,
            )
            count += 1
        return count
