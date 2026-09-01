"""Local smoke tests for urbanization vector API (hits running dev server)."""
import json
import sys
import urllib.request

BASE = 'http://127.0.0.1:8009/api'
errors = []


def get(path):
    with urllib.request.urlopen(BASE + path, timeout=10) as resp:
        return resp.status, json.loads(resp.read().decode())


try:
    code, data = get('/urbanization/')
    if code != 200:
        errors.append(f'urbanization: {code}')
    else:
        print('urbanization OK:', 'vector_years=', data.get('vector_years'))

    code, gj = get('/urbanization/geojson/?year=2010')
    if code != 200:
        errors.append(f'geojson: {code}')
    else:
        print('geojson OK:', 'features=', len(gj.get('features', [])), 'class_field=', gj.get('class_field'))

    code, vecs = get('/urbanization-vectors/')
    if code != 200:
        errors.append(f'vectors: {code}')
    else:
        rows = vecs.get('results', vecs)
        print('vectors OK:', len(rows), 'rows')
except Exception as exc:
    errors.append(str(exc))

if errors:
    print('FAILURES:')
    for e in errors:
        print(' -', e)
    sys.exit(1)

print('ALL LOCAL CHECKS PASSED')
