"""
Urbanizatsiya klassifikatsiya shapefile import.

  python manage.py import_urbanization_shp --file Urbanization_2010.zip
  python manage.py import_urbanization_shp --file Urbanization_2010.shp --year 2010
"""
from pathlib import Path

from django.core.management.base import BaseCommand

from lands.models import UrbanizationVectorYear
from lands.urbanization_vector import import_urbanization_shapefile, save_vector_year


class Command(BaseCommand):
    help = 'Urbanizatsiya shapefile import (0=non-urban, 1=urban)'

    def add_arguments(self, parser):
        parser.add_argument('--file', type=str, required=True, help='.shp yoki .zip')
        parser.add_argument('--year', type=int, help='Yil (masalan Urbanization_2010)')

    def handle(self, *args, **options):
        path = Path(options['file'])
        if not path.exists():
            self.stderr.write(self.style.ERROR(f'Fayl topilmadi: {path}'))
            return

        try:
            payload = import_urbanization_shapefile(path, options.get('year'))
            obj = save_vector_year(UrbanizationVectorYear, payload)
        except Exception as exc:
            self.stderr.write(self.style.ERROR(str(exc)))
            return

        self.stdout.write(self.style.SUCCESS(
            f'Urban {obj.year}: {obj.feature_count} ob\'ekt, '
            f'urban={obj.urban_area_ha} ga, non-urban={obj.non_urban_area_ha} ga '
            f'(maydon: {obj.class_field})',
        ))
