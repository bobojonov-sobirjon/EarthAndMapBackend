"""
Sug'orish obyektlariga kanal / ariq tipini belgilash
(import description yoki nom bo'yicha).

  python manage.py tag_water_classes
"""
from django.core.management.base import BaseCommand
from django.db.models import Q

from lands.models import PublicLand


class Command(BaseCommand):
    help = "suv obyektlariga road_class=kanal|ariq belgilash"

    def handle(self, *args, **options):
        qs = PublicLand.objects.filter(category__code='suv', is_active=True)
        kanal = qs.filter(
            Q(description__icontains='Kanal') | Q(description__icontains='kanal')
        ).exclude(
            Q(description__icontains='Ariq') | Q(description__icontains='ariq')
        )
        ariq = qs.filter(
            Q(description__icontains='Ariq') | Q(description__icontains='ariq')
        )
        n1 = kanal.exclude(road_class='kanal').update(road_class='kanal')
        n2 = ariq.exclude(road_class='ariq').update(road_class='ariq')
        # Nom bo'yicha qolganlar
        rest = qs.filter(road_class='')
        n3 = rest.filter(
            Q(name__icontains='kanal') | Q(name__icontains='Канал') | Q(name__icontains='канал')
        ).update(road_class='kanal')
        n4 = rest.filter(
            Q(name__icontains='ariq') | Q(name__icontains='арык') | Q(name__icontains='ариқ')
        ).update(road_class='ariq')
        left = qs.filter(road_class='').count()
        self.stdout.write(self.style.SUCCESS(
            f'kanal={n1 + n3}, ariq={n2 + n4}, still_empty={left}'
        ))
