"""Shapefile / GeoJSON → GeoJSON geometry helpers."""
import json
import tempfile
import zipfile
from pathlib import Path

import shapefile

from .crs_utils import to_wgs84


POLYLINE_TYPES = {
    shapefile.POLYLINE, shapefile.POLYLINEM, shapefile.POLYLINEZ,
    3, 13, 23,
}


def close_ring(ring):
    if not ring or len(ring) < 3:
        return ring
    a, b = ring[0], ring[-1]
    if a[0] != b[0] or a[1] != b[1]:
        return ring + [ring[0]]
    return ring


def ring_is_closed(ring):
    if not ring or len(ring) < 4:
        return False
    a, b = ring[0], ring[-1]
    return a[0] == b[0] and a[1] == b[1]


def closed_lines_to_polygon(geom):
    """Yopilgan chiziqlarni polygon qiladi — GeoData Viewer kabi to‘ldirish uchun."""
    if not geom:
        return geom
    gtype = geom.get('type')
    if gtype == 'LineString':
        ring = close_ring(list(geom.get('coordinates') or []))
        if ring_is_closed(ring) and len(ring) >= 4:
            return {'type': 'Polygon', 'coordinates': [ring]}
        return geom
    if gtype == 'MultiLineString':
        polys = []
        leftover = []
        for raw in geom.get('coordinates') or []:
            ring = close_ring(list(raw or []))
            if ring_is_closed(ring) and len(ring) >= 4:
                polys.append([ring])
            elif ring:
                leftover.append(ring)
        if polys and not leftover:
            if len(polys) == 1:
                return {'type': 'Polygon', 'coordinates': polys[0]}
            return {'type': 'MultiPolygon', 'coordinates': polys}
        return geom
    if gtype == 'Polygon':
        rings = [close_ring(list(r)) for r in (geom.get('coordinates') or []) if r]
        return {'type': 'Polygon', 'coordinates': rings} if rings else geom
    if gtype == 'MultiPolygon':
        coords = []
        for poly in geom.get('coordinates') or []:
            rings = [close_ring(list(r)) for r in (poly or []) if r]
            if rings:
                coords.append(rings)
        return {'type': 'MultiPolygon', 'coordinates': coords} if coords else geom
    return geom


def dissolve_city_geometry(geoms):
    """Barcha uchastkalarni bitta yopiq shahar chegarasiga birlashtiradi."""
    cleaned = []
    for g in geoms:
        if not g:
            continue
        cleaned.append(closed_lines_to_polygon(g) or g)
    if not cleaned:
        return None
    try:
        from shapely.geometry import mapping, shape
        from shapely.ops import polygonize, unary_union

        parts = []
        line_parts = []
        for g in cleaned:
            gtype = g.get('type')
            try:
                sh = shape(g)
            except Exception:
                continue
            if sh.is_empty:
                continue
            if not sh.is_valid:
                sh = sh.buffer(0)
            if sh.is_empty:
                continue
            if gtype in ('LineString', 'MultiLineString'):
                line_parts.append(sh)
            elif gtype in ('Polygon', 'MultiPolygon'):
                parts.append(sh)
        if line_parts:
            try:
                parts.extend(list(polygonize(unary_union(line_parts))))
            except Exception:
                pass
        if not parts:
            return merge_geometries(cleaned)
        united = unary_union(parts)
        # Uchastkalar orasidagi mayda teshiklarni yopish (~15–20 m)
        united = united.buffer(0.00016).buffer(-0.0001)
        if united.is_empty:
            return merge_geometries(cleaned)
        return mapping(united)
    except Exception:
        return merge_geometries(cleaned)


def as_line_geometry(geom):
    """Yo'l / ariq kategoriya: poligon bo'lsa ham kontur chiziq sifatida."""
    if not geom:
        return geom
    gtype = geom.get('type')
    if gtype in ('LineString', 'MultiLineString'):
        return geom
    if gtype == 'Polygon':
        rings = geom.get('coordinates') or []
        if len(rings) == 1:
            return {'type': 'LineString', 'coordinates': rings[0]}
        return {'type': 'MultiLineString', 'coordinates': rings}
    if gtype == 'MultiPolygon':
        lines = []
        for poly in geom.get('coordinates') or []:
            for ring in poly:
                if ring:
                    lines.append(ring)
        if len(lines) == 1:
            return {'type': 'LineString', 'coordinates': lines[0]}
        return {'type': 'MultiLineString', 'coordinates': lines}
    return geom


def shape_to_geojson(shape):
    parts = list(shape.parts) + [len(shape.points)]
    rings = []
    for i in range(len(parts) - 1):
        ring = [[float(x), float(y)] for x, y in shape.points[parts[i]:parts[i + 1]]]
        if ring:
            rings.append(ring)

    rings = [close_ring(r) for r in rings]
    st = shape.shapeType
    if st in POLYLINE_TYPES:
        closed = all(ring_is_closed(r) for r in rings) and rings
        if closed:
            if len(rings) == 1:
                return {'type': 'Polygon', 'coordinates': rings}
            return {'type': 'MultiPolygon', 'coordinates': [[r] for r in rings]}
        if len(rings) == 1:
            return {'type': 'LineString', 'coordinates': rings[0]}
        return {'type': 'MultiLineString', 'coordinates': rings}

    if len(rings) == 1:
        return {'type': 'Polygon', 'coordinates': rings}
    return {'type': 'MultiPolygon', 'coordinates': [[ring] for ring in rings]}


def read_shapefile(shp_path):
    last_err = None
    for enc in ('utf-8', 'cp1251', 'latin-1'):
        reader = None
        try:
            reader = shapefile.Reader(str(shp_path), encoding=enc)
            fields = [f[0] for f in reader.fields[1:]]
            rows = []
            for sr in reader.iterShapeRecords():
                props = dict(zip(fields, sr.record))
                rows.append((props, to_wgs84(shape_to_geojson(sr.shape), Path(shp_path).with_suffix('.prj'))))
            return rows
        except Exception as exc:
            last_err = exc
            continue
        finally:
            if reader is not None:
                try:
                    reader.close()
                except Exception:
                    pass
    raise last_err or RuntimeError('shapefile read failed')


def find_shp(folder: Path):
    files = [p for p in folder.rglob('*.shp') if '__macosx' not in str(p).lower()]
    return files[0] if files else None


def iter_geojson_features(data):
    if not data:
        return
    if data.get('type') == 'FeatureCollection':
        for feat in data.get('features') or []:
            geom = feat.get('geometry')
            if geom:
                yield feat.get('properties') or {}, geom
        return
    if data.get('type') == 'Feature' and data.get('geometry'):
        yield data.get('properties') or {}, data['geometry']
        return
    if data.get('type') in (
        'Point', 'MultiPoint', 'LineString', 'MultiLineString',
        'Polygon', 'MultiPolygon',
    ):
        yield {}, data


def pick_name(props, prefix, index):
    for key in ('name', 'NAME', 'Name', 'nomi', 'title', 'TITLE'):
        val = props.get(key)
        if val and str(val).strip():
            return str(val).strip()[:255]
    return f'{prefix} #{index}'


def extract_zip_safe(data: bytes, dest: Path):
    zpath = dest / 'upload.zip'
    zpath.write_bytes(data)
    with zipfile.ZipFile(zpath) as zf:
        dest_res = dest.resolve()
        for info in zf.infolist():
            out = (dest / info.filename).resolve()
            if not str(out).startswith(str(dest_res)):
                continue
            zf.extract(info, dest)


def merge_geometries(geoms):
    if not geoms:
        return None
    if len(geoms) == 1:
        return geoms[0]
    poly_ok = all(g.get('type') in ('Polygon', 'MultiPolygon') for g in geoms)
    line_ok = all(g.get('type') in ('LineString', 'MultiLineString') for g in geoms)
    if poly_ok:
        coords = []
        for g in geoms:
            if g['type'] == 'Polygon':
                coords.append(g['coordinates'])
            else:
                coords.extend(g['coordinates'])
        return {'type': 'MultiPolygon', 'coordinates': coords}
    if line_ok:
        coords = []
        for g in geoms:
            if g['type'] == 'LineString':
                coords.append(g['coordinates'])
            else:
                coords.extend(g['coordinates'])
        return {'type': 'MultiLineString', 'coordinates': coords}
    return geoms[0]


def geometry_from_upload(uploaded):
    """Django UploadedFile → (geometry, source_name, feature_count)."""
    source_name = uploaded.name
    suffix = Path(uploaded.name).suffix.lower()
    records = []

    if suffix in ('.geojson', '.json'):
        data = json.loads(uploaded.read().decode('utf-8'))
        records = list(iter_geojson_features(data))
    elif suffix in ('.zip', '.shp'):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            tmp_path = Path(tmp)
            if suffix == '.zip':
                extract_zip_safe(uploaded.read(), tmp_path)
            else:
                (tmp_path / uploaded.name).write_bytes(uploaded.read())
            shp = find_shp(tmp_path)
            if not shp:
                raise ValueError('ZIP ichida .shp + .shx + .dbf kerak')
            records = list(read_shapefile(shp))
            source_name = shp.name
    else:
        raise ValueError('Ruxsat: .zip (shapefile), .shp yoki .geojson')

    geoms = [g for _, g in records if g]
    if not geoms:
        raise ValueError('Faylda geometriya yo‘q')
    return merge_geometries(geoms), source_name, len(geoms)
