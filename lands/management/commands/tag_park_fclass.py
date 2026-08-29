"""
Istrohat_boglari SHP dan fclass bo'yicha road_class yangilash
(qayta to'liq import qilmasdan).

  python manage.py tag_park_fclass --shp "D:\\path\\Istrohat_boglari_2026.shp"
"""
from pathlib import Path

from django.core.management.base import BaseCommand

from lands.bundle_import import park_class_from_props
from lands.import_utils import pick_name, read_shapefile
from lands.models import PublicLand


class Command(BaseCommand):
    help = 'istirohat obyektlariga SHP fclass (park/xiyobon/square) belgilash'

    def add_arguments(self, parser):
        parser.add_argument('--shp', required=True, help='Istrohat_boglari_*.shp yo\'li')
        parser.add_argument('--year', type=int, default=2026)

    def handle(self, *args, **options):
        shp = Path(options['shp'])
        if not shp.exists():
            self.stderr.write(f'Topilmadi: {shp}')
            return
        year = options['year']
        qs = PublicLand.objects.filter(category__code__in=['istirohat', 'park'], is_active=True)
        if year:
            qs = qs.filter(monitoring_year=year)

        by_osm = {}
        by_name = {}
        for p in qs:
            if p.cadastral_number:
                by_osm[str(p.cadastral_number)] = p
            by_name[(p.name or '').strip().lower()] = p

        updated = 0
        counts = {}
        for i, (props, _geom) in enumerate(read_shapefile(shp), start=1):
            fc = park_class_from_props(props)
            if not fc:
                continue
            osm = str(props.get('osm_id') or props.get('id') or props.get('OBJECTID') or '')
            name = pick_name(props, 'Park', i).strip().lower()
            obj = by_osm.get(osm) if osm else None
            if not obj:
                obj = by_name.get(name)
            if not obj:
                continue
            if obj.road_class != fc:
                obj.road_class = fc
                if 'fclass=' not in (obj.description or ''):
                    obj.description = (obj.description or '') + f' | fclass={fc}'
                obj.save(update_fields=['road_class', 'description'])
                updated += 1
            counts[fc] = counts.get(fc, 0) + 1

        self.stdout.write(self.style.SUCCESS(f'updated={updated}, by_fclass={counts}'))
