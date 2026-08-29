"""
Buxoro shahri MFY (mahalla) chegaralarini import qilish.

Manbalar (ketma-ket):
  1. --file  (.geojson / .json / .zip shapefile)
  2. NGIS MAHALLA_UZKAD_DB16 (rasmiy MFY chegaralari) — DEFAULT
  3. NGIS kadastr (yer uchastkalari → MFY bo'yicha birlashtirish)
  4. Overpass API (agar polygon topilsa)

Foydalanish:
  python manage.py import_bukhara_mfy
  python manage.py import_bukhara_mfy --file path/to/mfy.geojson
  python manage.py import_bukhara_mfy --skip-mahalla
"""
import json
import re
import urllib.parse
import urllib.request
from collections import defaultdict
from pathlib import Path

from django.core.management.base import BaseCommand
from shapely.geometry import Polygon, mapping
from shapely.ops import unary_union
from shapely.validation import make_valid

from lands.import_utils import iter_geojson_features, read_shapefile
from lands.models import Mahalla

CADASTRE_QUERY_URL = 'https://db.ngis.uz/db/rest/services/TURAR_UZKAD_DB16/MapServer/0/query'
MAHALLA_QUERY_URL = 'https://db.ngis.uz/db/rest/services/UZKAD/MAHALLA_UZKAD_DB16/FeatureServer/0/query'
MAHALLA_WHERE = "district_name = 'Buxoro shahar'"
CADASTRE_WHERE = "district_name = 'Buxoro shahar'"
BBOX = '39.65,64.25,39.85,64.65'


def slugify(name: str) -> str:
    s = name.lower().strip()
    s = re.sub(r"[''`]", '', s)
    s = re.sub(r'[^a-z0-9]+', '-', s)
    return s.strip('-')[:50] or 'mfy'


def pick_name(props: dict) -> str | None:
    for key in ('name_uz', 'name:uz', 'name', 'NAME', 'name_ru', 'MFY', 'mfy', 'mahalla_name'):
        val = (props.get(key) or '').strip()
        if val:
            return val
    return None


def esri_rings_to_polygon(rings):
    if not rings or not rings[0] or len(rings[0]) < 4:
        return None
    exterior = [(float(x), float(y)) for x, y in rings[0]]
    holes = [[(float(x), float(y)) for x, y in ring] for ring in rings[1:] if ring]
    try:
        poly = Polygon(exterior, holes)
        if not poly.is_valid:
            poly = make_valid(poly)
        if poly.is_empty:
            return None
        return poly
    except Exception:
        return None


def mahalla_query(offset=0, page_size=1000, count_only=False):
    params = {
        'f': 'json',
        'where': MAHALLA_WHERE,
        'outFields': 'mahalla_name,mahalla_code,district_name',
        'returnGeometry': 'false' if count_only else 'true',
        'outSR': '4326',
    }
    if count_only:
        params['returnCountOnly'] = 'true'
    else:
        params['resultOffset'] = offset
        params['resultRecordCount'] = page_size
    data = urllib.parse.urlencode(params).encode()
    req = urllib.request.Request(
        MAHALLA_QUERY_URL,
        data=data,
        method='POST',
        headers={
            'User-Agent': 'BuxoroGIS/1.0',
            'Content-Type': 'application/x-www-form-urlencoded',
        },
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read())


def fetch_mahalla_features(log=print):
    """NGIS rasmiy MAHALLA_UZKAD_DB16 — open.ngis.uz dagi aniq MFY chegaralari."""
    total_payload = mahalla_query(count_only=True)
    total = int(total_payload.get('count') or 0)
    if total <= 0:
        if total_payload.get('error'):
            raise RuntimeError(total_payload['error'].get('message', 'MAHALLA query xato'))
        return []

    log(f'NGIS MAHALLA: {total} ta MFY yuklanmoqda...')
    page_size = 500
    offset = 0
    features = []
    fetched = 0

    while fetched < total:
        payload = mahalla_query(offset, page_size)
        batch = payload.get('features') or []
        if not batch:
            break
        for item in batch:
            attrs = item.get('attributes') or {}
            name = (attrs.get('mahalla_name') or '').strip()
            if not name:
                continue
            poly = esri_rings_to_polygon((item.get('geometry') or {}).get('rings'))
            if poly is None:
                continue
            code = slugify(name)
            features.append({
                'type': 'Feature',
                'geometry': mapping(poly),
                'properties': {
                    'name': name,
                    'code': code,
                    'mahalla_code': attrs.get('mahalla_code'),
                    'source': 'ngis_mahalla',
                },
            })
        fetched += len(batch)
        log(f'  {min(fetched, total)}/{total}')
        offset += len(batch)
        if len(batch) < page_size:
            break

    log(f'NGIS MAHALLA: {len(features)} ta rasmiy MFY chegarasi')
    return features


def cadastre_query(offset=0, page_size=1000, count_only=False):
    params = {
        'f': 'json',
        'where': CADASTRE_WHERE,
        'outFields': 'mahalla_name,mahalla_code',
        'returnGeometry': 'false' if count_only else 'true',
        'outSR': '4326',
    }
    if count_only:
        params['returnCountOnly'] = 'true'
    else:
        params['resultOffset'] = offset
        params['resultRecordCount'] = page_size
    data = urllib.parse.urlencode(params).encode()
    req = urllib.request.Request(
        CADASTRE_QUERY_URL,
        data=data,
        method='POST',
        headers={
            'User-Agent': 'BuxoroGIS/1.0',
            'Content-Type': 'application/x-www-form-urlencoded',
        },
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read())


def fetch_cadastre_features(log=print):
    total_payload = cadastre_query(count_only=True)
    total = int(total_payload.get('count') or 0)
    if total <= 0:
        return []

    log(f'Kadastr: {total} ta yer uchastkasi yuklanmoqda...')
    page_size = 1000
    offset = 0
    groups = defaultdict(list)
    fetched = 0

    while fetched < total:
        payload = cadastre_query(offset, page_size)
        batch = payload.get('features') or []
        if not batch:
            break
        for item in batch:
            attrs = item.get('attributes') or {}
            name = (attrs.get('mahalla_name') or '').strip()
            if not name:
                continue
            poly = esri_rings_to_polygon((item.get('geometry') or {}).get('rings'))
            if poly is None:
                continue
            groups[name].append(poly)
        fetched += len(batch)
        log(f'  {min(fetched, total)}/{total}')
        offset += len(batch)
        if len(batch) < page_size:
            break

    features = []
    for name, polys in sorted(groups.items()):
        if not polys:
            continue
        merged = unary_union(polys)
        if merged.is_empty:
            continue
        merged = merged.simplify(0.00003, preserve_topology=True)
        if merged.geom_type == 'GeometryCollection':
            polys_clean = [g for g in merged.geoms if g.geom_type in ('Polygon', 'MultiPolygon')]
            if not polys_clean:
                continue
            merged = unary_union(polys_clean)
        features.append({
            'type': 'Feature',
            'geometry': mapping(merged),
            'properties': {
                'name': name,
                'code': slugify(name),
                'source': 'cadastre',
                'parcel_count': len(polys),
            },
        })

    log(f'Kadastr: {len(features)} ta aniq MFY chegarasi ({len(groups)} nom)')
    return features


def way_to_polygon(el):
    if el.get('type') != 'way':
        return None
    geom = el.get('geometry') or []
    if len(geom) < 3:
        return None
    ring = [[p['lon'], p['lat']] for p in geom]
    if ring[0] != ring[-1]:
        ring.append(ring[0])
    return {'type': 'Polygon', 'coordinates': [ring]}


def relation_to_multipolygon(el, elements_by_id):
    if el.get('type') != 'relation':
        return None
    polys = []
    for m in el.get('members') or []:
        if m.get('type') != 'way' or m.get('role') not in ('outer', ''):
            continue
        way = elements_by_id.get(('way', m['ref']))
        if not way:
            continue
        g = way_to_polygon(way)
        if g:
            polys.append(g['coordinates'])
    if not polys:
        return None
    if len(polys) == 1:
        return {'type': 'Polygon', 'coordinates': polys[0]}
    return {'type': 'MultiPolygon', 'coordinates': [[r] for r in polys]}


def fetch_overpass_features():
    query = f"""
[out:json][timeout:120];
(
  relation["boundary"="administrative"]["admin_level"~"9|10"]({BBOX});
  way["boundary"="administrative"]["admin_level"~"9|10"]({BBOX});
  relation["place"~"neighbourhood|suburb|quarter"]({BBOX});
  way["place"~"neighbourhood|suburb|quarter"]({BBOX});
);
out geom;
"""
    data = urllib.parse.urlencode({'data': query}).encode()
    req = urllib.request.Request(
        'https://overpass-api.de/api/interpreter',
        data=data,
        method='POST',
        headers={'User-Agent': 'BuxoroGIS/1.0'},
    )
    with urllib.request.urlopen(req, timeout=130) as resp:
        payload = json.loads(resp.read())
    elements = payload.get('elements') or []
    by_id = {(el['type'], el['id']): el for el in elements if 'id' in el}

    features = []
    seen = set()
    for el in elements:
        tags = el.get('tags') or {}
        name = tags.get('name:uz') or tags.get('name')
        if not name:
            continue
        key = name.strip().lower()
        if key in seen:
            continue
        geom = None
        if el['type'] == 'way':
            geom = way_to_polygon(el)
        elif el['type'] == 'relation':
            geom = relation_to_multipolygon(el, by_id)
        if not geom:
            continue
        seen.add(key)
        features.append({
            'type': 'Feature',
            'geometry': geom,
            'properties': {'name': name.strip(), 'code': slugify(name), 'source': 'overpass'},
        })
    return features


def load_geojson_features(data):
    features = []
    for props, geom in iter_geojson_features(data):
        name = pick_name(props or {})
        if not name or not geom:
            continue
        code = (props or {}).get('code') or slugify(name)
        features.append({
            'type': 'Feature',
            'geometry': geom,
            'properties': {
                'name': name,
                'code': code,
                'source': (props or {}).get('source') or 'file',
            },
        })
    return features


def load_file_features(path: Path):
    suffix = path.suffix.lower()
    if suffix in ('.zip', '.shp'):
        records = list(read_shapefile(path))
        features = []
        for props, geom in records:
            name = pick_name(props or {})
            if not name or not geom:
                continue
            features.append({
                'type': 'Feature',
                'geometry': geom,
                'properties': {'name': name, 'code': slugify(name), 'source': 'file'},
            })
        return features
    if suffix in ('.geojson', '.json'):
        data = json.loads(path.read_text(encoding='utf-8'))
        return load_geojson_features(data)
    raise ValueError(f"Qo'llab-quvvatlanmaydi: {path.suffix}")


class Command(BaseCommand):
    help = 'Buxoro shahri MFY chegaralarini kadastrdan yuklash'

    def add_arguments(self, parser):
        parser.add_argument('--file', type=str, help='GeoJSON yoki shapefile (.zip/.shp)')
        parser.add_argument('--skip-mahalla', action='store_true', help='NGIS MAHALLA qatlamini o\'tkazib yuborish')
        parser.add_argument('--skip-cadastre', action='store_true', help='NGIS kadastr (uchastka) ni o\'tkazib yuborish')
        parser.add_argument('--skip-overpass', action='store_true', help='Overpass API ni o\'tkazib yuborish')

    def handle(self, *args, **options):
        features = []
        source = 'none'

        file_path = options.get('file')
        if file_path:
            path = Path(file_path)
            if not path.exists():
                self.stderr.write(self.style.ERROR(f'Fayl topilmadi: {path}'))
                return
            features = load_file_features(path)
            source = 'file'
            self.stdout.write(f'Fayldan {len(features)} MFY yuklandi')

        if not features and not options.get('skip_mahalla'):
            try:
                features = fetch_mahalla_features(log=self.stdout.write)
                if features:
                    source = 'ngis_mahalla'
            except Exception as exc:
                self.stdout.write(self.style.WARNING(f'NGIS MAHALLA xato: {exc}'))

        if not features and not options.get('skip_cadastre'):
            try:
                features = fetch_cadastre_features(log=self.stdout.write)
                if features:
                    source = 'cadastre'
            except Exception as exc:
                self.stdout.write(self.style.WARNING(f'Kadastr xato: {exc}'))

        if not features and not options.get('skip_overpass'):
            try:
                features = fetch_overpass_features()
                source = 'overpass'
                self.stdout.write(f'Overpass: {len(features)} polygon')
            except Exception as exc:
                self.stdout.write(self.style.WARNING(f'Overpass xato: {exc}'))

        if not features:
            self.stderr.write(self.style.ERROR(
                'MFY chegaralari topilmadi. Kadastr serveri ishlamayapti yoki rasmiy .shp/.geojson fayl kerak.',
            ))
            return

        if source == 'ngis_mahalla':
            self.stdout.write(self.style.SUCCESS(
                f'Rasmiy NGIS MFY chegaralari: {len(features)} ta',
            ))
        elif source == 'cadastre':
            self.stdout.write(self.style.SUCCESS(
                f'Aniq kadastr chegaralari: {len(features)} ta MFY',
            ))
        elif source != 'file':
            self.stdout.write(self.style.WARNING(
                'Ogohlantirish: bu taxminiy/yarim to\'liq ma\'lumot. Aniq chegaralar uchun kadastr yoki rasmiy shapefile ishlating.',
            ))

        active_codes = set()
        created = updated = 0
        for f in features:
            props = f.get('properties') or {}
            name = props.get('name')
            code = props.get('code') or slugify(name or '')
            if not name or not f.get('geometry'):
                continue
            active_codes.add(code)
            _, was_created = Mahalla.objects.update_or_create(
                code=code,
                defaults={
                    'name': name,
                    'geometry': f['geometry'],
                    'is_active': True,
                },
            )
            if was_created:
                created += 1
            else:
                updated += 1

        Mahalla.objects.exclude(code__in=active_codes).update(is_active=False)

        out_dir = Path(__file__).resolve().parents[2] / 'data'
        out_dir.mkdir(exist_ok=True)
        geo_path = out_dir / 'bukhara_mfy.geojson'
        geo_path.write_text(
            json.dumps({'type': 'FeatureCollection', 'features': features}, ensure_ascii=False),
            encoding='utf-8',
        )

        self.stdout.write(self.style.SUCCESS(
            f'Tayyor ({source}): faol {len(active_codes)}, yangi {created}, yangilangan {updated}. GeoJSON: {geo_path}',
        ))
