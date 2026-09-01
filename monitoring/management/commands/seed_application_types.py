from django.core.management.base import BaseCommand
from django.db import connection

from monitoring.models import ApplicationOnSite, ApplicationSubmission, ApplicationType

# Rasmiy gov.uz murojaat sahifalari
DEFAULT_TYPES = [
    (
        'Kadastr agentligi',
        'https://gov.uz/oz/kadastr',
        'Yer uchastkasi, yer chegarasi, noqonuniy egallash, kadastr, umumiy foydalanishdagi yerlar, '
        'yer maydonidan foydalanish qonuniyligi, devor bilan o\'rab olish, qirg\'oq yer',
    ),
    (
        'Ekologiya va iqlim o\'zgarishi milliy qo\'mitasi',
        'https://gov.uz/oz/eco/feedback',
        'Daraxt kesilishi, istirohat bog va park, yashil hudud va qoplama, chiqindi tashlash, '
        'maishiy va qurilish chiqindilari, ekologik va sanitariya zarar, yer va suv ifloslanishi',
    ),
    (
        'Qurilish va uy-joy kommunal xo\'jaligi vazirligi',
        'https://gov.uz/oz/mc/pages/fuqarolar-murojaati-uchun',
        'Noqonuniy qurilish, shaharsozlik, jamoat hududida qurilish, kommunal va obodonlashtirish, '
        'qurilish ishlari, kanal qirg\'og\'ida qurilish',
    ),
    (
        'Suv xo\'jaligi vazirligi',
        'https://gov.uz/oz/suvchi',
        'Ariq, kanal, sug\'orish tarmoqlari, suv obyektlari, kanal hududiga ta\'sir, '
        'suv oqimi, erkin oqim, to\'sqinlik, qirg\'oq qismidagi kanal',
    ),
]


def _reset_sequences():
    """SQLite: ID larni 1 dan boshlash."""
    tables = [
        'monitoring_applicationsubmission',
        'monitoring_applicationonsite',
        'monitoring_applicationtype',
    ]
    with connection.cursor() as cursor:
        for table in tables:
            cursor.execute('DELETE FROM sqlite_sequence WHERE name=%s', [table])


class Command(BaseCommand):
    help = 'ApplicationType va ApplicationOnSite (gov.uz murojaat sahifalari)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Barcha yozuvlarni o\'chirib, ID larni 1 dan qayta boshlash',
        )

    def handle(self, *args, **options):
        if options['reset']:
            ApplicationSubmission.objects.all().delete()
            ApplicationOnSite.objects.all().delete()
            ApplicationType.objects.all().delete()
            _reset_sequences()
            self.stdout.write('Eski yozuvlar o\'chirildi, ID tartibi qayta boshlandi.')

        created_sites = 0
        for name, url, description in DEFAULT_TYPES:
            app_type, type_created = ApplicationType.objects.get_or_create(
                name=name,
                defaults={
                    'description': description,
                    'is_active': True,
                },
            )
            if not type_created:
                app_type.description = description
                app_type.is_active = True
                app_type.save(update_fields=['description', 'is_active'])

            site, site_created = ApplicationOnSite.objects.get_or_create(
                application_type=app_type,
                site_url=url,
                defaults={'is_active': True},
            )
            if site_created:
                created_sites += 1
            ApplicationOnSite.objects.filter(application_type=app_type).exclude(id=site.id).delete()

        # Faol ro'yxatda bo'lmagan qolganlarini o'chirish
        keep_names = {row[0] for row in DEFAULT_TYPES}
        removed, _ = ApplicationType.objects.exclude(name__in=keep_names).delete()

        self.stdout.write(self.style.SUCCESS(
            f'Done. Faol turlar: {ApplicationType.objects.filter(is_active=True).count()}, '
            f'yangi saytlar: {created_sites}, o\'chirilgan: {removed}',
        ))
