"""GeoJSON geometriya hisob-kitoblari (GDALsiz)."""
import math
from typing import Any


def _ring_area_sqm(coords: list) -> float:
    """Shoelace formulasi — WGS84 koordinatalar uchun taxminiy maydon (m²)."""
    if len(coords) < 3:
        return 0.0
    avg_lat = sum(c[1] for c in coords) / len(coords)
    lat_rad = math.radians(avg_lat)
    m_per_deg_lat = 111320.0
    m_per_deg_lng = 111320.0 * math.cos(lat_rad)

    area = 0.0
    n = len(coords)
    for i in range(n):
        j = (i + 1) % n
        x1, y1 = coords[i][0] * m_per_deg_lng, coords[i][1] * m_per_deg_lat
        x2, y2 = coords[j][0] * m_per_deg_lng, coords[j][1] * m_per_deg_lat
        area += x1 * y2 - x2 * y1
    return abs(area) / 2.0


def _line_length_m(coords: list) -> float:
    total = 0.0
    for i in range(len(coords) - 1):
        lng1, lat1 = coords[i]
        lng2, lat2 = coords[i + 1]
        lat_rad = math.radians((lat1 + lat2) / 2)
        dx = (lng2 - lng1) * 111320.0 * math.cos(lat_rad)
        dy = (lat2 - lat1) * 111320.0
        total += math.sqrt(dx * dx + dy * dy)
    return total


def geometry_metrics(geometry: dict[str, Any]) -> tuple[float | None, float | None]:
    """Poligon uchun maydon (m²), chiziq uchun uzunlik (m) qaytaradi."""
    if not geometry:
        return None, None

    gtype = geometry.get('type')
    coords = geometry.get('coordinates')
    if not coords:
        return None, None

    if gtype == 'Polygon':
        return round(_ring_area_sqm(coords[0]), 2), None
    if gtype == 'MultiPolygon':
        area = sum(_ring_area_sqm(poly[0]) for poly in coords)
        return round(area, 2), None
    if gtype == 'LineString':
        return None, round(_line_length_m(coords), 2)
    if gtype == 'MultiLineString':
        length = sum(_line_length_m(line) for line in coords)
        return None, round(length, 2)
    if gtype == 'Point':
        return None, None
    return None, None


def geodesic_area_sqm(geometry: dict[str, Any] | None) -> float:
    """WGS84 geodezik maydon (m²) — shapely + pyproj."""
    if not geometry:
        return 0.0
    try:
        from shapely.geometry import shape
        from pyproj import Geod

        sh = shape(geometry)
        if sh.is_empty:
            return 0.0
        if not sh.is_valid:
            sh = sh.buffer(0)
        geod = Geod(ellps='WGS84')
        if sh.geom_type == 'Polygon':
            area, _ = geod.geometry_area_perimeter(sh)
            return abs(float(area))
        if sh.geom_type == 'MultiPolygon':
            total = 0.0
            for poly in sh.geoms:
                area, _ = geod.geometry_area_perimeter(poly)
                total += abs(float(area))
            return total
    except Exception:
        sqm, _ = geometry_metrics(geometry)
        return float(sqm or 0.0)
    sqm, _ = geometry_metrics(geometry)
    return float(sqm or 0.0)


def geometry_centroid(geom: dict[str, Any] | None) -> list[float] | None:
    """GeoJSON geometriya markaz nuqtasi [lng, lat]."""
    if not geom:
        return None
    gtype = geom.get('type')
    if gtype == 'Point':
        c = geom.get('coordinates') or []
        return [float(c[0]), float(c[1])] if len(c) >= 2 else None
    if gtype == 'Polygon':
        rings = geom.get('coordinates') or []
        ring = rings[0] if rings else []
    elif gtype == 'MultiPolygon':
        polys = geom.get('coordinates') or []
        ring = polys[0][0] if polys and polys[0] else []
    else:
        return None
    if len(ring) < 3:
        return None
    lng = sum(p[0] for p in ring) / len(ring)
    lat = sum(p[1] for p in ring) / len(ring)
    return [float(lng), float(lat)]


def to_feature(land) -> dict:
    """PublicLand obyektini GeoJSON Feature ga aylantirish."""
    from .registry_utils import m_to_km, sqm_to_ha

    return {
        'type': 'Feature',
        'id': land.id,
        'geometry': land.geometry,
        'properties': {
            'id': land.id,
            'public_id': getattr(land, 'public_id', None),
            'name': land.name,
            'name_ru': getattr(land, 'name_ru', ''),
            'name_en': getattr(land, 'name_en', ''),
            'category': land.category_id,
            'category_name': land.category.name_uz,
            'category_name_ru': land.category.name_ru,
            'category_name_en': getattr(land.category, 'name_en', ''),
            'category_color': land.category.color,
            'category_code': land.category.code,
            'cadastral_number': land.cadastral_number,
            'address': land.address,
            'address_ru': getattr(land, 'address_ru', ''),
            'address_en': getattr(land, 'address_en', ''),
            'mahalla': getattr(land, 'mahalla', ''),
            'description': land.description,
            'description_ru': getattr(land, 'description_ru', ''),
            'description_en': getattr(land, 'description_en', ''),
            'area_sqm': land.area_sqm,
            'area_ha': sqm_to_ha(land.area_sqm),
            'length_m': land.length_m,
            'length_km': m_to_km(land.length_m),
            'status': land.status,
            'condition': getattr(land, 'condition', ''),
            'road_class': getattr(land, 'road_class', ''),
            'monitoring_year': getattr(land, 'monitoring_year', 2026),
            'responsible_org': land.responsible_org,
            'data_source': getattr(land, 'data_source', ''),
            'acquisition_date': str(land.acquisition_date) if land.acquisition_date else None,
            'created_at': land.created_at.isoformat(),
            'updated_at': land.updated_at.isoformat(),
            'is_active': land.is_active,
        },
    }


def to_feature_collection(lands) -> dict:
    return {
        'type': 'FeatureCollection',
        'features': [to_feature(land) for land in lands],
    }
