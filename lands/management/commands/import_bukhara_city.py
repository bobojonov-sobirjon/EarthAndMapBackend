"""
Buxoro shahri administrativ chegarasini OSM yoki GeoJSON dan yuklash.

  python manage.py import_bukhara_city
  python manage.py import_bukhara_city --file lands/data/bukhara_city.geojson
  python manage.py import_bukhara_city --fetch-osm
"""
import json
import subprocess
import sys
from pathlib import Path

from django.core.management.base import BaseCommand

from lands.import_utils import dissolve_city_geometry, iter_geojson_features
from lands.models import CityBoundary

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
DEFAULT_FILE = DATA_DIR / "bukhara_city.geojson"
FETCH_SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "fetch_osm_city.py"


class Command(BaseCommand):
    help = "Buxoro shahri chegarasini (OSM / GeoJSON) bazaga yuklash"

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            type=str,
            default=str(DEFAULT_FILE),
            help="GeoJSON fayl (default: lands/data/bukhara_city.geojson)",
        )
        parser.add_argument(
            "--fetch-osm",
            action="store_true",
            help="Import oldin OSM dan yangi chegara yuklab olish",
        )

    def handle(self, *args, **options):
        path = Path(options["file"])
        if options["fetch_osm"] or not path.exists():
            self.stdout.write("OSM dan Buxoro shahri chegarasi yuklanmoqda...")
            rc = subprocess.call([sys.executable, str(FETCH_SCRIPT)])
            if rc != 0:
                self.stderr.write(self.style.ERROR("OSM chegarasi yuklanmadi"))
                return

        if not path.exists():
            self.stderr.write(self.style.ERROR(f"Fayl topilmadi: {path}"))
            return

        data = json.loads(path.read_text(encoding="utf-8"))
        geoms = [g for _, g in iter_geojson_features(data) if g]
        if not geoms:
            self.stderr.write(self.style.ERROR("GeoJSON da geometriya yo'q"))
            return

        geom = dissolve_city_geometry(geoms) if len(geoms) > 1 else geoms[0]
        if not geom:
            self.stderr.write(self.style.ERROR("Chegara yig'ilmadi"))
            return

        obj, created = CityBoundary.objects.update_or_create(
            code="bukhara_city",
            defaults={
                "name": "Buxoro shahri",
                "name_ru": "Город Бухара",
                "name_en": "Bukhara city",
                "boundary_type": CityBoundary.BoundaryType.CITY,
                "geometry": geom,
                "color": "#ff6b00",
                "weight": 4,
                "dash_array": "",
                "fill_opacity": 0,
                "order": 2,
                "is_visible": True,
            },
        )
        action = "yaratildi" if created else "yangilandi"
        self.stdout.write(self.style.SUCCESS(
            f"Buxoro shahri chegarasi {action} ({geom.get('type')}, {path.name})"
        ))
