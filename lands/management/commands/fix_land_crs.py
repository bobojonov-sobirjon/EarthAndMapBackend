"""Noto'g'ri (metr/UTM) geometriyani WGS84 ga o'tkazish va maydonni qayta hisoblash."""
from django.core.management.base import BaseCommand

from lands.crs_utils import looks_wgs84, sample_xy, to_wgs84
from lands.models import PublicLand


class Command(BaseCommand):
    help = 'Projected shapefile koordinatalarini lon/lat ga tuzatadi'

    def handle(self, *args, **options):
        n = 0
        for land in PublicLand.objects.all().iterator():
            geom = land.geometry
            if not geom:
                continue
            if looks_wgs84(geom):
                xy = sample_xy(geom)
                if xy and 50 <= xy[0] <= 80 and 35 <= xy[1] <= 45:
                    continue
            fixed = to_wgs84(geom)
            if fixed is geom or fixed == geom:
                continue
            if not looks_wgs84(fixed):
                continue
            land.geometry = fixed
            land.save()
            n += 1
            self.stdout.write(f'  {land.public_id or land.id}')
        self.stdout.write(self.style.SUCCESS(f'Tuzatildi: {n}'))
