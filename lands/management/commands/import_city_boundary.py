"""
Bitta Buxoro shahri chegarasi SHP/GeoJSON import.

  python manage.py import_city_boundary --file buxoro_shahar_2026.shp
  python manage.py import_city_boundary --file buxoro_shahar_2022.shp --year 2022
"""
from pathlib import Path

from django.core.management.base import BaseCommand

from lands.bundle_import import classify_stem
from lands.import_utils import dissolve_city_geometry, iter_geojson_features, read_shapefile
from lands.models import CityBoundary


class Command(BaseCommand):
    help = 'Buxoro shahri chegarasini yil bo\'yicha import qilish'

    def add_arguments(self, parser):
        parser.add_argument('--file', type=str, required=True, help='.shp yoki .geojson fayl')
        parser.add_argument('--year', type=int, help='Yil (fayl nomidan olinadi, masalan buxoro_shahar_2026)')

    def handle(self, *args, **options):
        path = Path(options['file'])
        if not path.exists():
            self.stderr.write(self.style.ERROR(f'Fayl topilmadi: {path}'))
            return

        info = classify_stem(path.stem)
        if info.get('kind') != 'boundary':
            self.stderr.write(self.style.ERROR(
                f'Bu fayl shahar chegarasi emas: {path.name}. Nom: buxoro_shahar_YYYY',
            ))
            return

        year = options.get('year') or info.get('year')
        if not year:
            self.stderr.write(self.style.ERROR('Yil aniqlanmadi. --year 2026 qo\'shing'))
            return

        suffix = path.suffix.lower()
        if suffix == '.shp':
            records = list(read_shapefile(path))
            geoms = [g for _, g in records if g]
        elif suffix in ('.geojson', '.json'):
            data = path.read_text(encoding='utf-8')
            import json
            geoms = [g for _, g in iter_geojson_features(json.loads(data)) if g]
        else:
            self.stderr.write(self.style.ERROR('Faqat .shp, .geojson, .json'))
            return

        if not geoms:
            self.stderr.write(self.style.ERROR('Geometriya topilmadi'))
            return

        geom = dissolve_city_geometry(geoms) if len(geoms) > 1 else geoms[0]
        if not geom:
            self.stderr.write(self.style.ERROR('Chegara yig\'ilmadi'))
            return

        obj, created = CityBoundary.objects.update_or_create(
            code=info.get('code') or 'bukhara_city',
            monitoring_year=int(year),
            defaults={
                'name': f'Buxoro shahri ({year})',
                'name_ru': f'Город Бухара ({year})',
                'name_en': f'Bukhara city ({year})',
                'boundary_type': CityBoundary.BoundaryType.CITY,
                'geometry': geom,
                'color': '#ff6b00',
                'weight': 4,
                'dash_array': '',
                'fill_opacity': 0,
                'order': 2,
                'is_visible': True,
            },
        )
        action = 'yaratildi' if created else 'yangilandi'
        self.stdout.write(self.style.SUCCESS(
            f'{path.name} → {obj.code} @ {year} {action} ({geom.get("type")})',
        ))
