"""
Утилиты реестра: публичные ID (PARK-001, ROAD-I-001) и единицы измерения.
"""
from django.db.models import Max

CATEGORY_ID_PREFIX = {
    'park': 'PARK',
    'istirohat': 'PARK',
    'maydon': 'SQR',
    'xiyobon': 'BLV',
    'qabriston': 'CEM',
    'yollar': 'ROAD',
    'suv': 'WTR',
    'maktab': 'SCH',
    'masjid': 'MSJ',
    'bozor': 'MKT',
    'stadion': 'STD',
    'sport': 'SPT',
    'kutubxona': 'LIB',
}

ROAD_CLASS_PREFIX = {
    'magistral': 'ROAD-I',
    'shahar': 'ROAD-II',
    'mahalliy': 'ROAD-III',
    'piyoda': 'ROAD-P',
}


def next_public_id(category_code, road_class=''):
    from lands.models import PublicLand

    if category_code == 'yollar' and road_class in ROAD_CLASS_PREFIX:
        prefix = ROAD_CLASS_PREFIX[road_class]
    else:
        prefix = CATEGORY_ID_PREFIX.get(category_code, 'OBJ')

    existing = (
        PublicLand.objects.filter(public_id__startswith=f'{prefix}-')
        .aggregate(m=Max('public_id'))
    )
    last = existing.get('m')
    if last:
        try:
            num = int(str(last).rsplit('-', 1)[-1])
        except ValueError:
            num = PublicLand.objects.filter(public_id__startswith=f'{prefix}-').count()
    else:
        num = 0
    return f'{prefix}-{num + 1:03d}'


def sqm_to_ha(sqm):
    if sqm is None:
        return 0.0
    return round(float(sqm) / 10000.0, 4)


def m_to_km(meters):
    if meters is None:
        return 0.0
    return round(float(meters) / 1000.0, 3)
