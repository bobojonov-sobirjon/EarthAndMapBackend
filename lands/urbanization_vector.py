"""Shapefile → GeoJSON import for urbanization classification layers."""
import json
import re
import tempfile
from pathlib import Path

from django.core.files.base import ContentFile

from .geo_utils import geodesic_area_sqm
from .import_utils import extract_zip_safe, find_shp, read_shapefile
from .registry_utils import sqm_to_ha

CLASS_FIELD_CANDIDATES = [
    'gridcode', 'GRIDCODE', 'GridCode', 'grid_code',
    'class', 'CLASS', 'Class', 'Value', 'VALUE', 'value',
    'urban', 'URBAN', 'class_id', 'classification', 'CLASSIFICATION', 'DN', 'dn',
]

AREA_FIELD_CANDIDATES = [
    'AREA_HA', 'Area_Ha', 'area_ha', 'HECTARES', 'Hectares', 'hectares', 'GA', 'ga',
    'AREA', 'Area', 'area', 'SHAPE_AREA', 'Shape_Area', 'shape_area', 'Shape_Area_1',
    'AREA_M2', 'Area_m2', 'area_m2', 'SQUARE_M', 'SqM', 'sqm', 'AREA_SQM',
]

URBAN_VECTOR_YEARS = [2000, 2010, 2015, 2020, 2025]


def _normalize_class(val):
    if val is None:
        return None
    try:
        return int(float(val))
    except (TypeError, ValueError):
        return val


def detect_class_field(records: list) -> str | None:
    if not records:
        return None
    sample = records[:200]
    for name in CLASS_FIELD_CANDIDATES:
        vals = [_normalize_class(props.get(name)) for props, _ in sample]
        if vals and all(v in (0, 1) for v in vals if v is not None):
            return name
    fields = list(sample[0][0].keys())
    for name in fields:
        vals = [_normalize_class(props.get(name)) for props, _ in sample]
        if vals and all(v in (0, 1) for v in vals if v is not None):
            return name
    return None


def _parse_area_value(val) -> float | None:
    if val is None:
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def _area_field_unit(field_name: str, sample_vals: list[float]) -> str:
    """'ha' yoki 'sqm'."""
    low = field_name.lower()
    if 'ha' in low or 'hect' in low or low == 'ga':
        return 'ha'
    if 'm2' in low or 'sqm' in low or 'square_m' in low:
        return 'sqm'
    if not sample_vals:
        return 'sqm'
    med = sorted(sample_vals)[len(sample_vals) // 2]
    # Katta qiymatlar odatda m² (Shape_Area), kichik — ga
    if med > 5000:
        return 'sqm'
    if med < 500:
        return 'ha'
    return 'sqm'


def detect_area_field(records: list) -> tuple[str | None, str]:
    if not records:
        return None, 'sqm'
    sample = records[:500]
    fields = list(sample[0][0].keys())

    for name in AREA_FIELD_CANDIDATES:
        if name not in fields:
            continue
        vals = [_parse_area_value(props.get(name)) for props, _ in sample]
        nums = [v for v in vals if v is not None and v >= 0]
        if len(nums) >= max(1, len(sample) // 2):
            return name, _area_field_unit(name, nums)

    for name in fields:
        if name.lower() in ('class', 'id', 'fid', 'objectid', 'year'):
            continue
        vals = [_parse_area_value(props.get(name)) for props, _ in sample]
        nums = [v for v in vals if v is not None and v > 0]
        if len(nums) >= max(3, len(sample) // 3):
            low = name.lower()
            if 'area' in low or 'shape' in low or low in ('ga', 'hectares'):
                return name, _area_field_unit(name, nums)

    return None, 'sqm'


def _area_sqm_from_props(props: dict, area_field: str | None, unit: str) -> float:
    if not area_field:
        return 0.0
    val = _parse_area_value(props.get(area_field))
    if val is None or val < 0:
        return 0.0
    if unit == 'ha':
        return val * 10000.0
    return val


def compute_class_areas(records: list, class_field: str) -> tuple[float, float, str | None]:
    """
    Urban / non-urban maydon (m²).
    1) shapefile atributidagi maydon maydoni (AREA, Shape_Area, area_ha…)
    2) geodezik geometriya hisobi
    """
    area_field, unit = detect_area_field(records)
    urban_sqm = 0.0
    non_urban_sqm = 0.0
    attr_used = 0

    if area_field:
        for props, _geom in records:
            cls = _normalize_class(props.get(class_field))
            sqm = _area_sqm_from_props(props, area_field, unit)
            if sqm <= 0:
                continue
            attr_used += 1
            if cls == 1:
                urban_sqm += sqm
            elif cls == 0:
                non_urban_sqm += sqm

    if attr_used > 0 and (urban_sqm > 0 or non_urban_sqm > 0):
        return urban_sqm, non_urban_sqm, area_field

    for props, geom in records:
        if not geom:
            continue
        cls = _normalize_class(props.get(class_field))
        sqm = geodesic_area_sqm(geom)
        if sqm <= 0:
            continue
        if cls == 1:
            urban_sqm += sqm
        elif cls == 0:
            non_urban_sqm += sqm

    return urban_sqm, non_urban_sqm, area_field


def _bounds_from_features(features: list) -> list:
    min_lat, min_lon = 999, 999
    max_lat, max_lon = -999, -999

    def walk_coords(coords):
        nonlocal min_lat, min_lon, max_lat, max_lon
        if not coords:
            return
        if isinstance(coords[0], (int, float)):
            lon, lat = float(coords[0]), float(coords[1])
            min_lat = min(min_lat, lat)
            max_lat = max(max_lat, lat)
            min_lon = min(min_lon, lon)
            max_lon = max(max_lon, lon)
            return
        for c in coords:
            walk_coords(c)

    for feat in features:
        geom = feat.get('geometry') or {}
        walk_coords(geom.get('coordinates'))

    if min_lat > max_lat:
        return []
    return [[min_lat, min_lon], [max_lat, max_lon]]


def build_feature_collection(records: list, year: int, class_field: str) -> dict:
    area_field, area_unit = detect_area_field(records)
    urban_sqm, non_urban_sqm, used_area_field = compute_class_areas(records, class_field)
    features = []

    for props, geom in records:
        if not geom:
            continue
        cls = _normalize_class(props.get(class_field))

        clean_props = {}
        for key, val in props.items():
            if val is None:
                clean_props[key] = None
            elif isinstance(val, (str, int, float, bool)):
                clean_props[key] = val
            else:
                clean_props[key] = str(val)

        feat_sqm = _area_sqm_from_props(props, used_area_field, area_unit) if used_area_field else 0.0
        if feat_sqm <= 0:
            feat_sqm = geodesic_area_sqm(geom)
        if feat_sqm > 0:
            clean_props['area_sqm'] = round(feat_sqm, 2)
            clean_props['area_ha'] = round(sqm_to_ha(feat_sqm), 4)

        features.append({
            'type': 'Feature',
            'geometry': geom,
            'properties': clean_props,
        })

    return {
        'type': 'FeatureCollection',
        'features': features,
        'meta': {
            'year': year,
            'class_field': class_field,
            'area_field': used_area_field,
            'bounds': _bounds_from_features(features),
            'urban_area_ha': round(sqm_to_ha(urban_sqm), 2) if urban_sqm > 0 else None,
            'non_urban_area_ha': round(sqm_to_ha(non_urban_sqm), 2) if non_urban_sqm > 0 else None,
            'feature_count': len(features),
        },
    }


def year_from_stem(stem: str) -> int | None:
    m = re.search(r'(20\d{2})', stem)
    return int(m.group(1)) if m else None


def payload_from_shp_path(shp_path: Path, year: int) -> dict:
    records = list(read_shapefile(shp_path))
    if not records:
        raise ValueError('Shapefile bo\'sh')

    class_field = detect_class_field(records)
    if not class_field:
        raise ValueError('0/1 klassifikatsiya maydoni topilmadi (class, gridcode, value…)')

    fc = build_feature_collection(records, int(year), class_field)
    meta = fc['meta']
    if not meta['feature_count']:
        raise ValueError('Hech qanday geometriya import qilinmadi')

    return {
        'year': int(year),
        'class_field': class_field,
        'feature_count': meta['feature_count'],
        'urban_area_ha': meta['urban_area_ha'],
        'non_urban_area_ha': meta['non_urban_area_ha'],
        'bounds': meta['bounds'],
        'area_field': meta.get('area_field'),
        'geojson_bytes': json.dumps(fc, ensure_ascii=False).encode('utf-8'),
        'source_name': shp_path.name,
    }


def import_urbanization_shapefile(file_path: Path, year: int | None = None) -> dict:
    year = year or year_from_stem(file_path.stem)
    if not year:
        raise ValueError('Yil aniqlanmadi — fayl nomida yoki --year bilan ko\'rsating')

    suffix = file_path.suffix.lower()
    if suffix == '.zip':
        with tempfile.TemporaryDirectory() as tmp:
            extract_zip_safe(file_path.read_bytes(), Path(tmp))
            shp = find_shp(Path(tmp))
            if not shp:
                raise ValueError('ZIP ichida .shp topilmadi')
            return payload_from_shp_path(shp, int(year))
    if suffix == '.shp':
        return payload_from_shp_path(file_path, int(year))
    raise ValueError('Faqat .shp yoki .zip qabul qilinadi')


def save_vector_year(model_cls, payload: dict):
    obj, _ = model_cls.objects.update_or_create(
        year=payload['year'],
        defaults={
            'class_field': payload['class_field'],
            'feature_count': payload['feature_count'],
            'urban_area_ha': payload['urban_area_ha'],
            'non_urban_area_ha': payload['non_urban_area_ha'],
            'bounds': payload['bounds'],
            'source_name': payload['source_name'],
            'is_visible': True,
        },
    )
    obj.geojson.save(
        f'urban_vector_{payload["year"]}.geojson',
        ContentFile(payload['geojson_bytes']),
        save=False,
    )
    obj.save()
    return obj
