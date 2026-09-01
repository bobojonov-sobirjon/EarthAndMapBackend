"""Urbanizatsiya ZIP: ichida GeoTIFF (RGB + klassifikatsiya) va shapefile."""
from __future__ import annotations

import tempfile
from pathlib import Path

from django.core.files import File

from .import_utils import extract_zip_safe, find_shp
from .models import UrbanizationRasterSet, UrbanizationVectorYear
from .urbanization_raster import landsat_rgb_label, landsat_sensor_name

RGB_HINTS = ('rgb', 'natural', 'color', 'composite', 'landsat', 'true')
CLASS_HINTS = ('class', 'cluster', 'iso', 'extraction', 'classification', 'urban', 'cls')


def _apply_raster_previews(obj: UrbanizationRasterSet) -> None:
    from django.core.files.base import ContentFile

    from .urbanization_raster import HAS_RASTERIO, process_uploaded_tif

    if not HAS_RASTERIO:
        import logging
        logging.getLogger(__name__).warning(
            'rasterio o\'rnatilmagan — GeoTIFF preview yaratilmaydi. pip install rasterio',
        )
        return

    changed = []
    rgb_source = obj.rgb_tif or obj.classified_tif
    if rgb_source:
        meta = process_uploaded_tif(rgb_source.path, mode='rgb', year=obj.year)
        obj.rgb_bounds = meta['bounds']
        obj.rgb_label = landsat_rgb_label(obj.year)
        changed.extend(['rgb_bounds', 'rgb_label'])
        if meta.get('preview_png'):
            obj.rgb_preview.save(
                f'urban_rgb_{obj.year}.png',
                ContentFile(meta['preview_png']),
                save=False,
            )
            changed.append('rgb_preview')
    if obj.classified_tif:
        meta = process_uploaded_tif(obj.classified_tif.path, mode='classified', year=obj.year)
        obj.classified_bounds = meta['bounds']
        changed.append('classified_bounds')
        if meta.get('preview_png'):
            obj.classified_preview.save(
                f'urban_cls_{obj.year}.png',
                ContentFile(meta['preview_png']),
                save=False,
            )
            changed.append('classified_preview')
    if changed:
        obj.save(update_fields=changed + ['updated_at'])


def _list_tifs(root: Path) -> list[Path]:
    out: list[Path] = []
    seen: set[Path] = set()
    for p in root.rglob('*'):
        if '__macosx' in str(p).lower() or not p.is_file():
            continue
        low = p.suffix.lower()
        if low in ('.tif', '.tiff'):
            key = p.resolve()
            if key not in seen:
                out.append(p)
                seen.add(key)
        elif low == '.tfw':
            for candidate in (
                p.parent / p.stem,
                p.with_suffix('.tif'),
                p.with_suffix('.tiff'),
            ):
                if candidate.is_file():
                    key = candidate.resolve()
                    if key not in seen:
                        out.append(candidate)
                        seen.add(key)
                        break
    return sorted(out, key=lambda x: x.name.lower())


def _resolve_uploaded_tif(data: bytes, name: str, dest_root: Path) -> Path | None:
    """Bitta .tif yoki ZIP ichidagi GeoTIFF (tfw/aux bilan)."""
    suffix = Path(name).suffix.lower()
    if suffix == '.zip':
        extract_zip_safe(data, dest_root)
        tifs = _list_tifs(dest_root)
        if not tifs:
            return None
        _, cls = classify_tifs(tifs)
        return cls or tifs[0]

    dest = dest_root / name
    dest.write_bytes(data)
    if dest.suffix.lower() in ('.tif', '.tiff') and dest.is_file():
        return dest
    tifs = _list_tifs(dest_root)
    return tifs[0] if tifs else None


def _score(name: str, hints: tuple[str, ...]) -> int:
    low = name.lower()
    return sum(1 for h in hints if h in low)


def classify_tifs(tifs: list[Path]) -> tuple[Path | None, Path | None]:
    if not tifs:
        return None, None
    if len(tifs) == 1:
        tif = tifs[0]
        try:
            from .urbanization_raster import HAS_RASTERIO
            if HAS_RASTERIO:
                import rasterio
                with rasterio.open(tif) as src:
                    if src.count >= 3:
                        return tif, None
        except Exception:
            pass
        return None, tif

    scored_rgb = [(p, _score(p.stem, RGB_HINTS) - _score(p.stem, CLASS_HINTS)) for p in tifs]
    scored_cls = [(p, _score(p.stem, CLASS_HINTS) - _score(p.stem, RGB_HINTS)) for p in tifs]

    rgb = max(scored_rgb, key=lambda x: x[1])[0]
    cls = max(scored_cls, key=lambda x: x[1])[0]
    if rgb == cls:
        rgb, cls = tifs[0], tifs[1]
    return rgb, cls


def scan_urbanization_bundle(zip_bytes: bytes, year: int) -> dict:
    """ZIP tahlil — saqlamaydi, faqat shapefile atributlari va fayl ro'yxati."""
    warnings: list[str] = []
    urban_ha = None
    non_urban_ha = None
    feature_count = 0
    class_field = None
    area_field = None
    has_shp = False
    has_rgb_tif = False
    has_classified_tif = False
    shp_name = None

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        extract_zip_safe(zip_bytes, root)

        shp = find_shp(root)
        if shp:
            has_shp = True
            shp_name = shp.name
            payload = payload_from_shp_path(shp, year)
            urban_ha = payload['urban_area_ha']
            non_urban_ha = payload['non_urban_area_ha']
            feature_count = payload['feature_count']
            class_field = payload['class_field']
            area_field = payload.get('area_field')
        else:
            warnings.append('ZIP ichida shapefile (.shp) topilmadi')

        tifs = _list_tifs(root)
        rgb_path, cls_path = classify_tifs(tifs)
        has_rgb_tif = rgb_path is not None
        has_classified_tif = cls_path is not None
        if tifs and not (rgb_path and cls_path):
            warnings.append('GeoTIFF: RGB va klassifikatsiya (.tif) aniqlanmadi')

    return {
        'year': year,
        'urban_area_ha': urban_ha,
        'non_urban_area_ha': non_urban_ha,
        'feature_count': feature_count,
        'class_field': class_field,
        'area_field': area_field,
        'has_shapefile': has_shp,
        'shapefile_name': shp_name,
        'has_rgb_tif': has_rgb_tif,
        'has_classified_tif': has_classified_tif,
        'warnings': warnings,
    }


def process_urbanization_bundle(
    zip_bytes: bytes,
    year: int,
    *,
    note: str = '',
    urban_area_ha: float | None = None,
    non_urban_area_ha: float | None = None,
    source_name: str = 'bundle.zip',
) -> dict:
    """
  ZIP ichidan .tif/.tiff va .shp ajratadi.
  Shapefile atributlari (0/1) → vector qatlam + maydon (ga).
  GeoTIFF → raster preview (ixtiyoriy, ikkala TIF bo'lsa).
    """
    warnings: list[str] = []
    vector_obj = None
    raster_obj = None

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        extract_zip_safe(zip_bytes, root)

        shp = find_shp(root)
        if shp:
            payload = payload_from_shp_path(shp, year)
            payload['source_name'] = source_name
            vector_obj = save_vector_year(UrbanizationVectorYear, payload)
            if note:
                vector_obj.note = note
                vector_obj.save(update_fields=['note', 'updated_at'])
        else:
            warnings.append('ZIP ichida shapefile (.shp) topilmadi')

        tifs = _list_tifs(root)
        rgb_path, cls_path = classify_tifs(tifs)

        if cls_path or rgb_path:
            urban_ha = urban_area_ha
            non_urban_ha = non_urban_area_ha
            if vector_obj and urban_ha is None:
                urban_ha = vector_obj.urban_area_ha
            if vector_obj and non_urban_ha is None:
                non_urban_ha = vector_obj.non_urban_area_ha
            raster_obj = _save_raster_year(
                year, cls_path, rgb_path, vector_obj, note, urban_ha, non_urban_ha,
            )
        elif tifs:
            warnings.append('GeoTIFF: klassifikatsiya (.tif) aniqlanmadi')

    if not vector_obj and not raster_obj:
        detail = warnings[0] if warnings else 'ZIP ichida foydalaniladigan fayl topilmadi'
        raise ValueError(detail)

    return {
        'vector': vector_obj,
        'raster': raster_obj,
        'warnings': warnings,
    }


def _import_shapefile_bytes(data: bytes, name: str, year: int, note: str = '') -> UrbanizationVectorYear | None:
    suffix = Path(name).suffix.lower() or '.zip'
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(data)
        tmp_path = Path(tmp.name)
    try:
        from .urbanization_vector import import_urbanization_shapefile, save_vector_year
        payload = import_urbanization_shapefile(tmp_path, year)
        payload['source_name'] = name
        obj = save_vector_year(UrbanizationVectorYear, payload)
        if note:
            obj.note = note
            obj.save(update_fields=['note', 'updated_at'])
        return obj
    finally:
        try:
            tmp_path.unlink(missing_ok=True)
        except Exception:
            pass


def _save_raster_year(
    year: int,
    classified_path: Path | None,
    rgb_path: Path | None,
    vector_obj: UrbanizationVectorYear | None,
    note: str,
    urban_area_ha: float | None,
    non_urban_area_ha: float | None,
) -> UrbanizationRasterSet | None:
    if not classified_path and not rgb_path:
        return None

    urban_ha = urban_area_ha
    non_urban_ha = non_urban_area_ha
    if vector_obj and urban_ha is None:
        urban_ha = vector_obj.urban_area_ha
    if vector_obj and non_urban_ha is None:
        non_urban_ha = vector_obj.non_urban_area_ha

    raster_obj, _ = UrbanizationRasterSet.objects.update_or_create(
        year=year,
        defaults={
            'title': f'{year}-yilda Buxoro shahar hududlari (Landsat + ISO Cluster)',
            'rgb_label': landsat_rgb_label(year),
            'classified_label': 'Urban extraction (ISO Cluster)',
            'urban_area_ha': urban_ha,
            'non_urban_area_ha': non_urban_ha,
            'note': note,
            'is_visible': True,
        },
    )
    if rgb_path:
        with open(rgb_path, 'rb') as fh:
            raster_obj.rgb_tif.save(f'urban_rgb_{year}.tif', File(fh), save=False)
    if classified_path:
        with open(classified_path, 'rb') as fh:
            raster_obj.classified_tif.save(f'urban_cls_{year}.tif', File(fh), save=False)
    raster_obj.save()
    _apply_raster_previews(raster_obj)
    return raster_obj


def process_urbanization_files(
    year: int,
    *,
    shapefile_bytes: bytes | None = None,
    shapefile_name: str = 'shapefile.zip',
    classified_tif_bytes: bytes | None = None,
    classified_tif_name: str = 'classified.tif',
    rgb_tif_bytes: bytes | None = None,
    rgb_tif_name: str = 'rgb.tif',
    note: str = '',
    urban_area_ha: float | None = None,
    non_urban_area_ha: float | None = None,
) -> dict:
    """Alohida shapefile + GeoTIFF yuklash."""
    warnings: list[str] = []
    vector_obj = None
    raster_obj = None

    if shapefile_bytes:
        vector_obj = _import_shapefile_bytes(shapefile_bytes, shapefile_name, year, note)
    else:
        warnings.append('Shapefile yuborilmadi')

    cls_path = None
    rgb_path = None
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        if classified_tif_bytes:
            cls_path = _resolve_uploaded_tif(
                classified_tif_bytes, classified_tif_name, root,
            )
            if not cls_path:
                warnings.append('ZIP ichida GeoTIFF (.tif) topilmadi')
        if rgb_tif_bytes:
            rgb_path = _resolve_uploaded_tif(rgb_tif_bytes, rgb_tif_name, root / 'rgb')
            if not rgb_path:
                warnings.append('RGB GeoTIFF topilmadi')

        if cls_path or rgb_path:
            raster_obj = _save_raster_year(
                year, cls_path, rgb_path, vector_obj, note,
                urban_area_ha, non_urban_area_ha,
            )
        elif not shapefile_bytes:
            warnings.append('GeoTIFF yuborilmadi')

    if not vector_obj and not raster_obj:
        raise ValueError(warnings[0] if warnings else 'Fayl topilmadi')

    return {'vector': vector_obj, 'raster': raster_obj, 'warnings': warnings}


def scan_urbanization_files(
    year: int,
    shapefile_bytes: bytes | None = None,
    shapefile_name: str = 'shapefile.zip',
    classified_tif_bytes: bytes | None = None,
    classified_tif_name: str = 'classified.tif',
) -> dict:
    warnings: list[str] = []
    urban_ha = None
    non_urban_ha = None
    feature_count = 0
    class_field = None
    area_field = None
    has_shp = False
    has_classified_tif = False
    shp_name = None
    cls_name = None

    if shapefile_bytes:
        suffix = Path(shapefile_name).suffix.lower() or '.zip'
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(shapefile_bytes)
            tmp_path = Path(tmp.name)
        try:
            from .urbanization_vector import import_urbanization_shapefile
            payload = import_urbanization_shapefile(tmp_path, year)
            has_shp = True
            shp_name = shapefile_name
            urban_ha = payload['urban_area_ha']
            non_urban_ha = payload['non_urban_area_ha']
            feature_count = payload['feature_count']
            class_field = payload['class_field']
            area_field = payload.get('area_field')
        except Exception as exc:
            warnings.append(str(exc))
        finally:
            try:
                tmp_path.unlink(missing_ok=True)
            except Exception:
                pass
    else:
        warnings.append('Shapefile tanlanmadi')

    if classified_tif_bytes:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cls_path = _resolve_uploaded_tif(
                classified_tif_bytes, classified_tif_name, root,
            )
            if cls_path:
                has_classified_tif = True
                cls_name = cls_path.name
            else:
                warnings.append('ZIP ichida GeoTIFF (.tif) topilmadi')
    else:
        warnings.append('Klassifikatsiya GeoTIFF tanlanmadi')

    return {
        'year': year,
        'urban_area_ha': urban_ha,
        'non_urban_area_ha': non_urban_ha,
        'feature_count': feature_count,
        'class_field': class_field,
        'area_field': area_field,
        'has_shapefile': has_shp,
        'shapefile_name': shp_name,
        'has_rgb_tif': False,
        'has_classified_tif': has_classified_tif,
        'classified_tif_name': cls_name,
        'warnings': warnings,
    }
