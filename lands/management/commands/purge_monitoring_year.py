"""
Monitoring yili bo'yicha ma'lumotlarni bazadan o'chirish.

  python manage.py purge_monitoring_year --year 2024 --yes
  python manage.py purge_monitoring_year --year 2024 --dry-run
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from lands.models import (
    CityBoundary,
    MonitoringRecord,
    ObjectVersion,
    PublicLand,
    UrbanizationLayer,
)


class Command(BaseCommand):
    help = "Berilgan monitoring yiliga tegishli obyektlar va chegaralarni o'chirish"

    def add_arguments(self, parser):
        parser.add_argument('--year', type=int, required=True, help='O\'chiriladigan yil (masalan: 2024)')
        parser.add_argument('--yes', action='store_true', help='Tasdiqlashsiz o\'chirish')
        parser.add_argument('--dry-run', action='store_true', help='Faqat hisob, o\'chirmaslik')

    def handle(self, *args, **options):
        year = int(options['year'])
        dry_run = options['dry_run']
        confirmed = options['yes']

        if year < 1900 or year > 2100:
            self.stderr.write(self.style.ERROR('Noto\'g\'ri yil'))
            return

        lands_qs = PublicLand.objects.filter(monitoring_year=year)
        boundaries_qs = CityBoundary.objects.filter(monitoring_year=year)
        versions_qs = ObjectVersion.objects.filter(year=year)
        records_qs = MonitoringRecord.objects.filter(year=year)
        urban_qs = UrbanizationLayer.objects.filter(year=year)

        counts = {
            'lands': lands_qs.count(),
            'boundaries': boundaries_qs.count(),
            'versions': versions_qs.count(),
            'monitoring_records': records_qs.count(),
            'urban_layers': urban_qs.count(),
        }
        total = sum(counts.values())

        self.stdout.write(f'Yil: {year}')
        for key, val in counts.items():
            self.stdout.write(f'  {key}: {val}')

        if total == 0:
            self.stdout.write(self.style.WARNING('O\'chiriladigan yozuv yo\'q'))
            return

        if dry_run:
            self.stdout.write(self.style.WARNING('Dry-run — hech narsa o\'chirilmadi'))
            return

        if not confirmed:
            self.stderr.write(self.style.ERROR(
                f'{total} ta yozuv o\'chadi. Davom etish uchun --yes qo\'shing.',
            ))
            return

        with transaction.atomic():
            deleted = {
                'versions': versions_qs.delete()[0],
                'monitoring_records': records_qs.delete()[0],
                'urban_layers': urban_qs.delete()[0],
                'lands': lands_qs.delete()[0],
                'boundaries': boundaries_qs.delete()[0],
            }

        self.stdout.write(self.style.SUCCESS(
            f'Tayyor: {year} yili uchun o\'chirildi — '
            + ', '.join(f'{k}={v}' for k, v in deleted.items()),
        ))
