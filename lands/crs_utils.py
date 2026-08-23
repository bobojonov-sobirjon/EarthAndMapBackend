"""Shapefile metr/UTM koordinatalarini WGS84 (lon/lat) ga o'tkazish."""
from __future__ import annotations

from pathlib import Path

BUKHARA_LON = (63.2, 65.6)
BUKHARA_LAT = (39.2, 40.6)

# O'zbekiston / Buxoro uchun tez-tez uchraydigan tizimlar
GUESS_EPSG = (
    32640,  # WGS84 UTM 40N (Buxoro shu zonada)
    32641,
    28411,  # Pulkovo 1942 / GK zone 11
    28440,
    3857,   # Web Mercator
    7684,
)


def _walk_xy(coords, fn):
    if not coords:
        return coords
    if isinstance(coords[0], (int, float)):
        x, y = float(coords[0]), float(coords[1])
        nx, ny = fn(x, y)
        return [nx, ny, *coords[2:]]
    return [_walk_xy(c, fn) for c in coords]


def sample_xy(geom):
    coords = (geom or {}).get('coordinates')
    while coords and not isinstance(coords[0], (int, float)):
        coords = coords[0]
    if coords and len(coords) >= 2:
        return float(coords[0]), float(coords[1])
    return None


def looks_wgs84(geom) -> bool:
    xy = sample_xy(geom)
    if not xy:
        return False
    x, y = xy
    return -180 <= x <= 180 and -90 <= y <= 90


def in_bukhara(lon, lat) -> bool:
    return BUKHARA_LON[0] <= lon <= BUKHARA_LON[1] and BUKHARA_LAT[0] <= lat <= BUKHARA_LAT[1]


def _transformer(src):
    from pyproj import Transformer
    return Transformer.from_crs(src, 4326, always_xy=True)


def _transform_geom(geom, transformer):
    if not geom or not geom.get('coordinates'):
        return geom
    def fn(x, y):
        lon, lat = transformer.transform(x, y)
        return float(lon), float(lat)
    return {**geom, 'coordinates': _walk_xy(geom['coordinates'], fn)}


def crs_from_prj(prj_path: Path | None):
    if not prj_path or not Path(prj_path).exists():
        return None
    text = Path(prj_path).read_text(encoding='utf-8', errors='ignore').strip()
    if not text:
        return None
    from pyproj import CRS
    try:
        return CRS.from_wkt(text)
    except Exception:
        try:
            return CRS.from_string(text)
        except Exception:
            return None


def to_wgs84(geom, prj_path: Path | None = None):
    """GeoJSON geometry ni EPSG:4326 ga keltiradi. .prj yoki avtomatik taxmin."""
    if not geom:
        return geom

    src = crs_from_prj(prj_path)
    xy = sample_xy(geom)

    if src is not None:
        if src.is_geographic and looks_wgs84(geom):
            return geom
        try:
            out = _transform_geom(geom, _transformer(src))
            if looks_wgs84(out):
                return out
        except Exception:
            pass

    if looks_wgs84(geom):
        return geom

    if not xy:
        return geom

    from pyproj import CRS
    for epsg in GUESS_EPSG:
        try:
            t = _transformer(CRS.from_epsg(epsg))
            lon, lat = t.transform(xy[0], xy[1])
            if in_bukhara(lon, lat):
                return _transform_geom(geom, t)
        except Exception:
            continue
    return geom
