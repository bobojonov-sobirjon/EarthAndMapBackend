"""
Утилиты реестра: публичные ID (PARK-001, ROAD-I-001) и единицы измерения.
"""
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

WATER_CLASS_PREFIX = {
    'kanal': 'WTR-K',
    'ariq': 'WTR-A',
}

PARK_CLASS_PREFIX = {
    'park': 'PARK',
    'xiyobon': 'BLV',
    'square': 'SQR',
}


def public_id_prefix(category_code, road_class=''):
    if category_code == 'yollar' and road_class in ROAD_CLASS_PREFIX:
        return ROAD_CLASS_PREFIX[road_class]
    if category_code == 'suv' and road_class in WATER_CLASS_PREFIX:
        return WATER_CLASS_PREFIX[road_class]
    if category_code in ('istirohat', 'park') and road_class in PARK_CLASS_PREFIX:
        return PARK_CLASS_PREFIX[road_class]
    return CATEGORY_ID_PREFIX.get(category_code, 'OBJ')


def max_public_id_num(prefix):
    from lands.models import PublicLand

    needle = f'{prefix}-'
    max_n = 0
    for pid in PublicLand.objects.filter(public_id__startswith=needle).values_list('public_id', flat=True):
        rest = str(pid)[len(needle):]
        if rest.isdigit():
            n = int(rest)
            if n > max_n:
                max_n = n
    return max_n


def next_public_id(category_code, road_class=''):
    prefix = public_id_prefix(category_code, road_class)
    return f'{prefix}-{max_public_id_num(prefix) + 1:03d}'


class PublicIdSeq:
    """Один запрос к БД, дальше счётчик в памяти — для пакетного импорта."""

    def __init__(self, category_code, road_class=''):
        self.prefix = public_id_prefix(category_code, road_class)
        self.n = max_public_id_num(self.prefix)

    def next(self):
        self.n += 1
        return f'{self.prefix}-{self.n:03d}'


def sqm_to_ha(sqm):
    if sqm is None:
        return 0.0
    return round(float(sqm) / 10000.0, 4)


def m_to_km(meters):
    if meters is None:
        return 0.0
    return round(float(meters) / 1000.0, 3)
