from django.core.management.base import BaseCommand

from accounts.models import User
from lands.models import CityBoundary, LandCategory, PublicLand


class Command(BaseCommand):
    help = 'Buxoro GIS uchun boshlang\'ich ma\'lumotlarni yuklash'

    def handle(self, *args, **options):
        self.stdout.write('Kategoriyalar yaratilmoqda...')

        categories = [
            # code, name_uz, name_ru, geom, color, order
            ('yollar', "Yo'llar va ko'chalar", 'Дороги и улицы', 'LineString', '#9b59b6', 1),
            ('istirohat', 'Istirohat maydonlari', 'Зоны отдыха', 'Polygon', '#27ae60', 2),
            ('qabriston', 'Qabristonlar', 'Кладбища', 'Polygon', '#7f8c8d', 3),
            ('stadion', 'Stadionlar', 'Стадионы', 'Polygon', '#e67e22', 4),
            ('kutubxona', 'Kutubxonalar', 'Библиотеки', 'Point', '#3498db', 5),
            ('bozor', 'Bozorlar', 'Рынки', 'Polygon', '#8e2430', 6),
            ('sport', 'Sport markazlari', 'Спортивные центры', 'Polygon', '#1abc9c', 7),
            ('maktab', 'Maktablar', 'Школы', 'Polygon', '#c0392b', 8),
            ('masjid', 'Masjidlar', 'Мечети', 'Polygon', '#2c3e50', 9),
            ('park', 'Parklar va yashil hududlar', 'Парки и зелёные зоны', 'Polygon', '#2ecc71', 10),
        ]

        cat_objs = {}
        for code, name_uz, name_ru, geom_type, color, order in categories:
            obj, _ = LandCategory.objects.update_or_create(
                code=code,
                defaults={
                    'name_uz': name_uz,
                    'name_ru': name_ru,
                    'geometry_type': geom_type,
                    'color': color,
                    'order': order,
                    'is_active': True,
                },
            )
            cat_objs[code] = obj

        self.stdout.write('Shahar chegarasi yaratilmoqda...')
        CityBoundary.objects.all().delete()
        CityBoundary.objects.create(
            name='Buxoro shahri',
            geometry={
                'type': 'Polygon',
                'coordinates': [[
                    [64.35, 39.73], [64.52, 39.73], [64.52, 39.80],
                    [64.35, 39.80], [64.35, 39.73],
                ]],
            },
        )

        self.stdout.write('Namuna obyektlar yaratilmoqda...')
        PublicLand.objects.filter(name__startswith='[Demo]').delete()

        def poly(coords):
            return {'type': 'Polygon', 'coordinates': [coords + [coords[0]]]}

        def line(coords):
            return {'type': 'LineString', 'coordinates': coords}

        def point(lng, lat):
            return {'type': 'Point', 'coordinates': [lng, lat]}

        samples = [
            ('maktab', '[Demo] 1-son maktab', poly([
                [64.42, 39.77], [64.425, 39.77], [64.425, 39.772], [64.42, 39.772],
            ]), 'active'),
            ('maktab', '[Demo] 15-son maktab', poly([
                [64.44, 39.76], [64.445, 39.76], [64.445, 39.762], [64.44, 39.762],
            ]), 'active'),
            ('masjid', '[Demo] Po-i-Kalyan masjidi', poly([
                [64.415, 39.775], [64.418, 39.775], [64.418, 39.777], [64.415, 39.777],
            ]), 'active'),
            ('masjid', '[Demo] Magok-i-Attari masjidi', poly([
                [64.420, 39.773], [64.423, 39.773], [64.423, 39.775], [64.420, 39.775],
            ]), 'active'),
            ('park', '[Demo] Bog\'i Naqshband', poly([
                [64.408, 39.768], [64.415, 39.768], [64.415, 39.772], [64.408, 39.772],
            ]), 'active'),
            ('istirohat', '[Demo] Mustaqillik maydoni', poly([
                [64.430, 39.769], [64.438, 39.769], [64.438, 39.773], [64.430, 39.773],
            ]), 'active'),
            ('bozor', '[Demo] Eski shahar bozori', poly([
                [64.418, 39.774], [64.422, 39.774], [64.422, 39.776], [64.418, 39.776],
            ]), 'active'),
            ('stadion', '[Demo] Buxoro stadioni', poly([
                [64.450, 39.765], [64.458, 39.765], [64.458, 39.770], [64.450, 39.770],
            ]), 'active'),
            ('sport', '[Demo] Sport majmuasi', poly([
                [64.448, 39.763], [64.452, 39.763], [64.452, 39.766], [64.448, 39.766],
            ]), 'active'),
            ('kutubxona', '[Demo] Viloyat kutubxonasi', point(64.435, 39.771), 'active'),
            ('yollar', '[Demo] Mustaqillik ko\'chasi', line([
                [64.42, 39.77], [64.43, 39.77], [64.44, 39.769], [64.45, 39.768],
            ]), 'active'),
            ('yollar', '[Demo] Navoiy ko\'chasi', line([
                [64.41, 39.775], [64.42, 39.774], [64.43, 39.773], [64.44, 39.772],
            ]), 'active'),
        ]

        for code, name, geom, status in samples:
            PublicLand.objects.create(
                category=cat_objs[code],
                name=name,
                geometry=geom,
                status=status,
                address='Buxoro shahri',
                description='Demo ma\'lumot — seed_data buyrug\'i orqali yaratilgan',
            )

        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser(
                username='admin',
                email='admin@buxorogis.uz',
                password='admin123',
                role=User.Role.ADMIN,
            )
            self.stdout.write(self.style.SUCCESS('Admin: admin / admin123'))

        self.stdout.write(self.style.SUCCESS('Boshlang\'ich ma\'lumotlar muvaffaqiyatli yuklandi!'))
