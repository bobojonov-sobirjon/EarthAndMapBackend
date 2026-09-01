"""Mavjud urbanizatsiya qatlamlari maydonini qayta hisoblash."""
import json

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand

from lands.models import UrbanizationVectorYear
from lands.urbanization_vector import build_feature_collection, detect_class_field


class Command(BaseCommand):
    help = 'Urbanizatsiya vector qatlamlari maydonini (ga) qayta hisoblash'

    def add_arguments(self, parser):
        parser.add_argument('--year', type=int, help='Faqat bitta yil')

    def handle(self, *args, **options):
        qs = UrbanizationVectorYear.objects.all().order_by('year')
        if options.get('year'):
            qs = qs.filter(year=options['year'])

        if not qs.exists():
            self.stderr.write(self.style.WARNING('Qatlamlar topilmadi'))
            return

        for obj in qs:
            if not obj.geojson:
                self.stderr.write(self.style.WARNING(f'{obj.year}: geojson yo\'q'))
                continue

            with obj.geojson.open('r') as fh:
                fc = json.load(fh)

            records = [
                (feat.get('properties') or {}, feat.get('geometry'))
                for feat in fc.get('features', [])
            ]
            if not records:
                self.stderr.write(self.style.WARNING(f'{obj.year}: feature yo\'q'))
                continue

            class_field = obj.class_field or detect_class_field(records)
            if not class_field:
                self.stderr.write(self.style.ERROR(f'{obj.year}: class maydon topilmadi'))
                continue

            rebuilt = build_feature_collection(records, obj.year, class_field)
            meta = rebuilt['meta']
            obj.class_field = class_field
            obj.feature_count = meta['feature_count']
            obj.urban_area_ha = meta['urban_area_ha']
            obj.non_urban_area_ha = meta['non_urban_area_ha']
            obj.bounds = meta['bounds']
            obj.geojson.save(
                f'urban_vector_{obj.year}.geojson',
                ContentFile(json.dumps(rebuilt, ensure_ascii=False).encode('utf-8')),
                save=False,
            )
            obj.save()

            self.stdout.write(self.style.SUCCESS(
                f'{obj.year}: urban={obj.urban_area_ha} ga, non-urban={obj.non_urban_area_ha} ga '
                f'(maydon: {meta.get("area_field") or "geodezik"})',
            ))
