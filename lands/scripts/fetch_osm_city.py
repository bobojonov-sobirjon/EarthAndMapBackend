"""OSM dan Buxoro shahri chegarasini olish (relation 13070474)."""
import json
import urllib.parse
import urllib.request
from pathlib import Path

RELATION_ID = 13070474
OUT = Path(__file__).resolve().parents[1] / "data" / "bukhara_city.geojson"


def fetch_elements():
    query = f"""
[out:json][timeout:120];
relation({RELATION_ID});
(._;>;);
out geom;
"""
    data = urllib.parse.urlencode({"data": query}).encode()
    req = urllib.request.Request(
        "https://overpass-api.de/api/interpreter",
        data=data,
        method="POST",
        headers={"User-Agent": "BuxoroGIS/1.0"},
    )
    with urllib.request.urlopen(req, timeout=130) as resp:
        return json.loads(resp.read()).get("elements") or []


def build_geometry(elements):
    from shapely.geometry import LineString, mapping
    from shapely.ops import polygonize, unary_union

    by_id = {(el["type"], el["id"]): el for el in elements if "id" in el}
    relation = by_id.get(("relation", RELATION_ID))
    if not relation:
        raise RuntimeError("Buxoro shahri relation topilmadi")

    lines = []
    for m in relation.get("members") or []:
        if m.get("type") != "way" or m.get("role") not in ("outer", ""):
            continue
        way = by_id.get(("way", m["ref"]))
        if not way or not way.get("geometry"):
            continue
        coords = [(n["lon"], n["lat"]) for n in way["geometry"]]
        if len(coords) >= 2:
            lines.append(LineString(coords))

    if not lines:
        raise RuntimeError("Tashqi chiziqlar topilmadi")

    polys = list(polygonize(unary_union(lines)))
    if not polys:
        raise RuntimeError("Polygon yig'ilmadi")

    united = unary_union(polys)
    if united.is_empty:
        raise RuntimeError("Bo'sh geometriya")
    return mapping(united), relation.get("tags") or {}


def flatten_coords(geom):
    coords = []
    gtype = geom.get("type")
    if gtype == "Polygon":
        for ring in geom.get("coordinates") or []:
            coords.extend(ring)
    elif gtype == "MultiPolygon":
        for poly in geom.get("coordinates") or []:
            for ring in poly:
                coords.extend(ring)
    return coords


def main():
    elements = fetch_elements()
    geom, tags = build_geometry(elements)
    fc = {
        "type": "FeatureCollection",
        "features": [{
            "type": "Feature",
            "properties": {
                "name": tags.get("name:uz") or tags.get("name") or "Buxoro shahri",
                "code": "bukhara_city",
                "boundary_type": "city",
                "source": "osm",
                "osm_relation": RELATION_ID,
            },
            "geometry": geom,
        }],
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(fc, ensure_ascii=False, indent=2), encoding="utf-8")

    flat = flatten_coords(geom)
    lngs = [c[0] for c in flat]
    lats = [c[1] for c in flat]
    print(f"Saved {OUT}")
    print(f"Type: {geom['type']}, points: {len(flat)}")
    print(f"Bounds: {min(lngs):.5f},{min(lats):.5f} - {max(lngs):.5f},{max(lats):.5f}")


if __name__ == "__main__":
    main()
