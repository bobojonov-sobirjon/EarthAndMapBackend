"""Пакетный импорт ZIP с несколькими shapefile-группами."""
from __future__ import annotations

import re
from pathlib import Path

from .import_utils import as_line_geometry, dissolve_city_geometry, pick_name, read_shapefile
from .models import CityBoundary, LandCategory, PublicLand
from .registry_utils import PublicIdSeq

CAT_META = {
    'istirohat': {
        'name_uz': "Istirohat bog'lari",
        'name_ru': 'Парки и рекреация',
        'name_en': 'Parks and recreation',
        'geometry_type': LandCategory.GeometryType.POLYGON,
        'color': '#27ae60',
        'prefix': 'Парк',
        'order': 2,
    },
    'qabriston': {
        'name_uz': 'Qabristonlar',
        'name_ru': 'Кладбища',
        'name_en': 'Cemeteries',
        'geometry_type': LandCategory.GeometryType.POLYGON,
        'color': '#95a5a6',
        'prefix': 'Кладбище',
        'order': 4,
    },
    'suv': {
        'name_uz': "Sug'orish tarmoqlari",
        'name_ru': 'Оросительные сети',
        'name_en': 'Irrigation networks',
        'geometry_type': LandCategory.GeometryType.LINE,
        'color': '#3498db',
        'prefix': 'Канал',
        'order': 3,
    },
    'yollar': {
        'name_uz': "Avtomobil yo'llari",
        'name_ru': 'Автомобильные дороги',
        'name_en': 'Roads',
        'geometry_type': LandCategory.GeometryType.LINE,
        'color': '#e67e22',
        'prefix': 'Дорога',
        'order': 1,
    },
}


def find_all_shp(folder: Path):
    files = []
    for p in folder.rglob('*.shp'):
        if '__macosx' in str(p).lower():
            continue
        files.append(p)
    return files


def classify_stem(stem: str):
    raw = stem.strip()
    s = raw.lower().replace(' ', '_').replace('-', '_')
    year = None
    ym = re.search(r'(19|20)\d{2}$', s)
    if ym:
        year = int(ym.group(0))
        s = re.sub(r'_?(19|20)\d{2}$', '', s).rstrip('_')

    if re.search(r'buxoro_shahar|bukhara_city|bukhara_area|shahar_chegar', s):
        return {
            'kind': 'boundary',
            'year': year,
            'code': 'bukhara_city',
            'name': 'Город Бухара',
            'stem': raw,
        }

    road_class = ''
    cat = None
    if re.search(r'piyoda', s):
        cat, road_class = 'yollar', 'piyoda'
    elif re.search(r'(^|_)iii(_|$)|mahalliy', s) and 'daraj' in s:
        cat, road_class = 'yollar', 'mahalliy'
    elif re.search(r'(^|_)ii(_|$)|shahar_tuman', s) and 'daraj' in s:
        cat, road_class = 'yollar', 'shahar'
    elif re.search(r'(^|_)i(_|$)|magistral', s) and 'daraj' in s:
        cat, road_class = 'yollar', 'magistral'
    elif re.search(r'yol|yo.?l|road|kocha|ko.?cha', s):
        cat = 'yollar'
    elif re.search(r'qabriston', s):
        cat = 'qabriston'
    elif re.search(r'kanal|suv|sug.?or|ariq', s):
        cat = 'suv'
    elif re.search(r'ist.?rohat|bog.?lar|park|rekreas', s):
        cat = 'istirohat'

    if not cat:
        slug = re.sub(r'[^a-z0-9_]+', '_', s)[:50].strip('_') or 'import'
        cat = slug

    meta = CAT_META.get(cat, {
        'name_uz': raw.replace('_', ' '),
        'name_ru': raw.replace('_', ' '),
        'name_en': raw.replace('_', ' '),
        'geometry_type': LandCategory.GeometryType.POLYGON,
        'color': '#3388ff',
        'prefix': 'Объект',
        'order': 20,
    })
    return {
        'kind': 'layer',
        'year': year,
        'code': cat,
        'road_class': road_class,
        'stem': raw,
        **meta,
    }


def ensure_category(info):
    cat, created = LandCategory.objects.get_or_create(
        code=info['code'][:50],
        defaults={
            'name_uz': info['name_uz'][:200],
            'name_ru': (info.get('name_ru') or '')[:200],
            'name_en': (info.get('name_en') or '')[:200],
            'geometry_type': info.get('geometry_type') or LandCategory.GeometryType.POLYGON,
            'color': info.get('color') or '#3388ff',
            'is_active': True,
            'order': info.get('order') or 20,
        },
    )
    return cat, created


def import_one_shp(shp_path: Path, *, year_fallback, replace, user):
    info = classify_stem(shp_path.stem)
    year = info.get('year') or year_fallback or 2026
    try:
        records = list(read_shapefile(shp_path))
    except Exception as exc:
        return {
            'stem': shp_path.stem,
            'ok': False,
            'error': f'Не прочитан shapefile: {exc}',
        }

    if info['kind'] == 'boundary':
        if not records:
            return {'stem': shp_path.stem, 'ok': False, 'error': 'Пустая граница'}
        props, _first = records[0]
        geom = dissolve_city_geometry([g for _, g in records if g])
        if not geom:
            return {'stem': shp_path.stem, 'ok': False, 'error': 'Пустая граница'}
        obj, _ = CityBoundary.objects.update_or_create(
            code=info['code'],
            defaults={
                'name': pick_name(props, info.get('name') or 'Граница', 1),
                'name_ru': 'Город Бухара',
                'boundary_type': CityBoundary.BoundaryType.CITY,
                'geometry': geom,
                'is_visible': True,
                'fill_opacity': 0.22,
            },
        )
        return {
            'stem': shp_path.stem,
            'ok': True,
            'kind': 'boundary',
            'code': obj.code,
            'count': len(records),
            'year': year,
        }

    category, cat_created = ensure_category(info)
    if replace:
        qs = PublicLand.objects.filter(category=category, monitoring_year=year)
        if info.get('road_class'):
            qs = qs.filter(road_class=info['road_class'])
        qs.delete()

    created = 0
    prefix = info.get('prefix') or 'Объект'
    ids = PublicIdSeq(category.code, info.get('road_class') or '')
    for i, (props, geom) in enumerate(records, start=1):
        if not geom:
            continue
        if category.geometry_type == LandCategory.GeometryType.LINE:
            geom = as_line_geometry(geom)
        PublicLand.objects.create(
            category=category,
            public_id=ids.next(),
            name=pick_name(props, prefix, i),
            cadastral_number=str(props.get('osm_id') or props.get('id') or '')[:100],
            address='Buxoro shahri',
            description=f'[IMPORT] {shp_path.name} | {year}',
            geometry=geom,
            status=PublicLand.Status.ACTIVE,
            is_active=True,
            monitoring_year=year,
            road_class=info.get('road_class') or '',
            created_by=user if getattr(user, 'is_authenticated', False) else None,
        )
        created += 1

    return {
        'stem': shp_path.stem,
        'ok': True,
        'kind': 'layer',
        'category': category.code,
        'category_created': cat_created,
        'road_class': info.get('road_class') or None,
        'count': created,
        'year': year,
        'color': category.color,
    }


def import_bundle(folder: Path, *, year_fallback=2026, replace=False, user=None):
    shps = find_all_shp(folder)
    if not shps:
        return None
    layers = []
    total = 0
    for shp in sorted(shps, key=lambda p: p.stem.lower()):
        try:
            row = import_one_shp(shp, year_fallback=year_fallback, replace=replace, user=user)
        except Exception as exc:
            row = {'stem': shp.stem, 'ok': False, 'error': str(exc)}
        layers.append(row)
        if row.get('ok'):
            total += int(row.get('count') or 0)
    return {'imported': total, 'layers': layers, 'files': len(shps)}
