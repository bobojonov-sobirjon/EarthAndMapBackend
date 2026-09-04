"""Mavjud urbanizatsiya gektar qiymatlarini tuzatish (m² → ga: /10000)."""
from django.core.management.base import BaseCommand

from lands.models import UrbanizationRasterSet, UrbanizationVectorYear
from lands.urbanization_vector import normalize_ha_value


class Command(BaseCommand):
    help = 'Urbanizatsiya urban/non-urban ga qiymatlarini 10 000 ga bo‘lib tuzatish'

    def add_arguments(self, parser):
        parser.add_argument('--year', type=int, help='Faqat bitta yil')
        parser.add_argument('--dry-run', action='store_true')

    def handle(self, *args, **options):
        year = options.get('year')
        dry = options.get('dry_run')

        vec_qs = UrbanizationVectorYear.objects.all().order_by('year')
        rast_qs = UrbanizationRasterSet.objects.all().order_by('year')
        if year:
            vec_qs = vec_qs.filter(year=year)
            rast_qs = rast_qs.filter(year=year)

        fixed = 0
        for obj in list(vec_qs) + list(rast_qs):
            old_u = obj.urban_area_ha
            old_n = obj.non_urban_area_ha
            new_u = normalize_ha_value(old_u)
            new_n = normalize_ha_value(old_n)
            if new_u == old_u and new_n == old_n:
                continue
            label = obj.__class__.__name__
            self.stdout.write(
                f'{label} {obj.year}: urban {old_u} → {new_u}, non-urban {old_n} → {new_n}',
            )
            if not dry:
                obj.urban_area_ha = new_u
                obj.non_urban_area_ha = new_n
                obj.save(update_fields=['urban_area_ha', 'non_urban_area_ha', 'updated_at'])
            fixed += 1

        if fixed == 0:
            self.stdout.write(self.style.WARNING('Tuzatish kerak bo‘lgan yozuv yo‘q'))
        else:
            mode = 'DRY-RUN' if dry else 'SAVED'
            self.stdout.write(self.style.SUCCESS(f'{mode}: {fixed} yozuv'))
