"""Shapefile / GeoJSON → GeoJSON geometry helpers."""
from pathlib import Path

import shapefile


def shape_to_geojson(shape):
    parts = list(shape.parts) + [len(shape.points)]
    rings = []
    for i in range(len(parts) - 1):
        ring = [[float(x), float(y)] for x, y in shape.points[parts[i]:parts[i + 1]]]
        if ring:
            rings.append(ring)

    st = shape.shapeType
    if st in (shapefile.POLYLINE, shapefile.POLYLINEM, shapefile.POLYLINEZ, 3):
        if len(rings) == 1:
            return {'type': 'LineString', 'coordinates': rings[0]}
        return {'type': 'MultiLineString', 'coordinates': rings}

    if len(rings) == 1:
        return {'type': 'Polygon', 'coordinates': rings}
    return {'type': 'MultiPolygon', 'coordinates': [[ring] for ring in rings]}


def read_shapefile(shp_path):
    reader = shapefile.Reader(str(shp_path), encoding='utf-8')
    fields = [f[0] for f in reader.fields[1:]]
    for sr in reader.iterShapeRecords():
        props = dict(zip(fields, sr.record))
        yield props, shape_to_geojson(sr.shape)


def find_shp(folder: Path):
    files = list(folder.rglob('*.shp'))
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
