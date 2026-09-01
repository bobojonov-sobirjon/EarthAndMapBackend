"""Mavjud urbanizatsiya GeoTIFF lar uchun PNG preview qayta yaratish."""
from django.core.management.base import BaseCommand

from lands.models import UrbanizationRasterSet
from lands.urbanization_bundle import _apply_raster_previews
from lands.urbanization_raster import HAS_RASTERIO


class Command(BaseCommand):
    help = 'Urbanizatsiya raster preview (PNG) va bounds ni qayta hisoblaydi'

    def handle(self, *args, **options):
        if not HAS_RASTERIO:
            self.stderr.write(self.style.ERROR(
                'rasterio topilmadi. Avval: pip install rasterio',
            ))
            return

        qs = UrbanizationRasterSet.objects.all().order_by('year')
        if not qs.exists():
            self.stdout.write('Raster yozuvlari yo\'q.')
            return

        for obj in qs:
            _apply_raster_previews(obj)
            obj.refresh_from_db()
            ok = bool(obj.classified_preview or obj.rgb_preview)
            self.stdout.write(
                f'{obj.year}: preview={"OK" if ok else "FAIL"} '
                f'bounds={obj.classified_bounds or obj.rgb_bounds}',
            )
