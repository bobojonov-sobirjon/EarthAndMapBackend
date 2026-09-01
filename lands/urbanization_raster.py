"""GeoTIFF → web preview va Leaflet bounds."""
from __future__ import annotations

import io
from pathlib import Path

from PIL import Image

try:
    import numpy as np
    import rasterio
    from rasterio.warp import transform_bounds
    HAS_RASTERIO = True
except ImportError:  # pragma: no cover
    HAS_RASTERIO = False
    np = None

# Buxoro shahri taxminiy bbox (WGS84)
DEFAULT_LEAFLET_BOUNDS = [[39.728, 64.352], [39.802, 64.528]]

MAX_PREVIEW = 2400

# Landsat tabiiy rangli kompozit — yil bo'yicha band tanlash
LANDSAT_5_TM_YEARS = frozenset({2000, 2010})
LANDSAT_8_OLI_YEARS = frozenset({2015, 2020, 2025})

LANDSAT_5_TM_RGB = (3, 2, 1)   # Red=3, Green=2, Blue=1
LANDSAT_8_OLI_RGB = (4, 3, 2)  # Red=4, Green=3, Blue=2


def landsat_rgb_band_indices(year: int | None) -> tuple[int, int, int]:
    """Yil uchun Landsat RGB band indekslari (1-based)."""
    if year in LANDSAT_5_TM_YEARS:
        return LANDSAT_5_TM_RGB
    if year in LANDSAT_8_OLI_YEARS:
        return LANDSAT_8_OLI_RGB
    return LANDSAT_8_OLI_RGB


def landsat_rgb_label(year: int | None) -> str:
    if year in LANDSAT_5_TM_YEARS:
        return 'Landsat 5 TM RGB (3-2-1)'
    if year in LANDSAT_8_OLI_YEARS:
        return 'Landsat 8 OLI RGB (4-3-2)'
    return 'Landsat 8 OLI RGB (4-3-2)'


def landsat_sensor_name(year: int | None) -> str:
    if year in LANDSAT_5_TM_YEARS:
        return 'Landsat 5 TM'
    if year in LANDSAT_8_OLI_YEARS:
        return 'Landsat 8 OLI'
    return 'Landsat 8 OLI'


def leaflet_bounds_from_path(path: str | Path) -> list:
    path = Path(path)
    if not HAS_RASTERIO or not path.exists():
        return DEFAULT_LEAFLET_BOUNDS
    try:
        with rasterio.open(path) as src:
            if src.crs:
                west, south, east, north = transform_bounds(src.crs, 'EPSG:4326', *src.bounds)
            else:
                west, south, east, north = src.bounds
            return [[float(south), float(west)], [float(north), float(east)]]
    except Exception:
        return DEFAULT_LEAFLET_BOUNDS


def _resize(img: Image.Image) -> Image.Image:
    w, h = img.size
    if max(w, h) <= MAX_PREVIEW:
        return img
    scale = MAX_PREVIEW / max(w, h)
    return img.resize((max(1, int(w * scale)), max(1, int(h * scale))), Image.Resampling.LANCZOS)


def _crop_to_content(img: Image.Image, threshold: int = 42, white_bg: bool = False) -> Image.Image:
    """Qora yoki oq marginlarni kesish."""
    arr = np.asarray(img)
    if arr.ndim != 3:
        return img
    if white_bg:
        mask = (arr[:, :, 0] < 248) | (arr[:, :, 1] < 248) | (arr[:, :, 2] < 248)
    else:
        mask = (arr[:, :, 0] > threshold) | (arr[:, :, 1] > threshold) | (arr[:, :, 2] > threshold)
    if not mask.any():
        return img
    rows = np.where(mask.any(axis=1))[0]
    cols = np.where(mask.any(axis=0))[0]
    pad = 2
    top = max(0, int(rows[0]) - pad)
    bottom = min(arr.shape[0], int(rows[-1]) + pad + 1)
    left = max(0, int(cols[0]) - pad)
    right = min(arr.shape[1], int(cols[-1]) + pad + 1)
    return img.crop((left, top, right, bottom))


def _finalize_preview(img: Image.Image, white_bg: bool = False) -> bytes:
    img = _crop_to_content(img, white_bg=white_bg)
    img = _resize(img)
    buf = io.BytesIO()
    img.save(buf, format='PNG', optimize=True)
    return buf.getvalue()


def _finalize_map_overlay(img: Image.Image) -> bytes:
    """Xarita overlay: kesmasdan, shaffof nodata — bounds bilan mos."""
    img = _resize(img)
    buf = io.BytesIO()
    img.save(buf, format='PNG', optimize=True)
    return buf.getvalue()


def _rgba_from_rgb_valid(rgb: 'np.ndarray', valid: 'np.ndarray') -> Image.Image:
    alpha = np.where(valid, 255, 0).astype(np.uint8)
    rgba = np.dstack([rgb[:, :, 0], rgb[:, :, 1], rgb[:, :, 2], alpha])
    return Image.fromarray(rgba, mode='RGBA')


def _normalize_band(arr):
    arr = np.asarray(arr, dtype=np.float32)
    finite = arr[np.isfinite(arr)]
    if finite.size == 0:
        return np.zeros(arr.shape, dtype=np.uint8)
    lo, hi = np.percentile(finite, [2, 98])
    if hi <= lo:
        hi = lo + 1
    scaled = (arr - lo) / (hi - lo)
    scaled = np.clip(scaled, 0, 1)
    return (scaled * 255).astype(np.uint8)


def _looks_like_classification(band: 'np.ndarray', nodata) -> bool:
    """Bitta band klassifikatsiya (0/1 gridcode) yoki emas."""
    work = band.astype(np.float64)
    if nodata is not None and not (isinstance(nodata, float) and np.isnan(nodata)):
        work = np.where(band == nodata, np.nan, work)
    finite = work[np.isfinite(work)]
    if finite.size == 0:
        return False
    uniq = np.unique(finite)
    if len(uniq) > 16:
        return False
    ints = {int(round(v)) for v in uniq}
    return ints <= {0, 1, 2} or max(ints) <= 2


def _rgb_valid_mask(*bands, nodata) -> 'np.ndarray':
    """Tadqiqot hududi tashqarisidagi 0/nodata piksellarni shaffof qilish."""
    stacked = np.stack([np.asarray(b, dtype=np.float64) for b in bands], axis=0)
    valid = np.any(stacked != 0, axis=0)
    if nodata is not None and not (isinstance(nodata, float) and np.isnan(nodata)):
        valid &= ~np.any(stacked == nodata, axis=0)
    return valid


def preview_rgb_png(tif_path: str | Path, year: int | None = None) -> bytes | None:
    """Tabiiy rangli kompozit: Landsat 5 TM 3-2-1, Landsat 8 OLI 4-3-2."""
    if not HAS_RASTERIO:
        return None
    r_idx, g_idx, b_idx = landsat_rgb_band_indices(year)
    try:
        with rasterio.open(tif_path) as src:
            count = src.count
            nodata = src.nodata
            if count >= max(r_idx, g_idx, b_idx):
                raw_r = src.read(r_idx)
                raw_g = src.read(g_idx)
                raw_b = src.read(b_idx)
                r = _normalize_band(raw_r)
                g = _normalize_band(raw_g)
                b = _normalize_band(raw_b)
                valid = _rgb_valid_mask(raw_r, raw_g, raw_b, nodata=nodata)
            elif count >= 3:
                raw_r = src.read(1)
                raw_g = src.read(2)
                raw_b = src.read(3)
                r = _normalize_band(raw_r)
                g = _normalize_band(raw_g)
                b = _normalize_band(raw_b)
                valid = _rgb_valid_mask(raw_r, raw_g, raw_b, nodata=nodata)
            else:
                raw = src.read(1)
                band = _normalize_band(raw)
                rgb = np.dstack([band, band, band])
                valid = _rgb_valid_mask(raw, nodata=nodata)
                img = _rgba_from_rgb_valid(rgb, valid)
                buf = io.BytesIO()
                buf.write(_finalize_map_overlay(img))
                return buf.getvalue()

            rgb = np.dstack([r, g, b])
            img = _rgba_from_rgb_valid(rgb, valid)
            buf = io.BytesIO()
            buf.write(_finalize_map_overlay(img))
            return buf.getvalue()
    except Exception:
        return None


def _class_mask(band: 'np.ndarray', nodata) -> 'np.ndarray':
    mask = np.zeros(band.shape, dtype=bool)
    if nodata is not None and not (isinstance(nodata, float) and np.isnan(nodata)):
        mask |= band == nodata
    return mask


# Hisobot ranglari (2-rasm: och yashil + och pushti)
THEMATIC_PINK = (232, 180, 210)
THEMATIC_GREEN = (154, 220, 140)
THEMATIC_WHITE = (255, 255, 255)


def _pick_classification_band(src) -> 'np.ndarray':
    """Ko'p bandli TIF: eng kam noyob qiymatli band (klassifikatsiya)."""
    best = None
    best_score = 10**9
    for i in range(1, src.count + 1):
        band = np.asarray(src.read(i))
        valid = band > 0
        if not valid.any():
            continue
        n_unique = len(np.unique(band[valid]))
        if n_unique < best_score:
            best_score = n_unique
            best = band
    if best is not None:
        return best
    return np.asarray(src.read(1))


def _paint_classified_thematic_rgb(band: 'np.ndarray', nodata) -> 'np.ndarray':
    """ISO Cluster: 0 = oq (tashqari), ichida pushti/yashil."""
    work = band.astype(np.float64)
    if nodata is not None and not (isinstance(nodata, float) and np.isnan(nodata)):
        work = np.where(band == nodata, np.nan, work)

    rgb = np.full((*band.shape, 3), 255, dtype=np.uint8)
    inside = np.isfinite(work) & (work > 0)
    if not inside.any():
        return rgb

    pink = np.array(THEMATIC_PINK, dtype=np.uint8)
    green = np.array(THEMATIC_GREEN, dtype=np.uint8)

    rounded = np.round(work[inside])
    int_vals = {int(v) for v in np.unique(rounded)}

    if int_vals <= {1}:
        rgb[inside] = green
    elif int_vals <= {0, 1}:
        cls = np.round(work)
        rgb[(cls == 0) & inside] = pink
        rgb[(cls == 1) & inside] = green
    else:
        vals = work[inside]
        threshold = np.percentile(vals, 32)
        rgb[inside & (work <= threshold)] = pink
        rgb[inside & (work > threshold)] = green

    return rgb


def _paint_gridcode_rgb(band: 'np.ndarray', nodata) -> 'np.ndarray':
    """Shapefile preview: gridcode 0 = sariq, 1 = ko'k."""
    mask = _class_mask(band, nodata)
    work = np.where(mask, np.nan, band.astype(np.float64))
    finite = work[np.isfinite(work)]
    rgb = np.full((*band.shape, 3), 30, dtype=np.uint8)

    if finite.size == 0:
        return rgb

    rounded = np.round(work)
    int_vals = {int(v) for v in np.unique(rounded[np.isfinite(rounded)])}

    if int_vals <= {0, 1}:
        cls = np.round(work)
        rgb[(cls == 0) & np.isfinite(cls)] = [250, 204, 21]
        rgb[(cls == 1) & np.isfinite(cls)] = [59, 130, 246]
    elif int_vals <= {0, 1, 2} and 0 in int_vals:
        cls = np.round(work)
        rgb[(cls == 0) & np.isfinite(cls)] = [250, 204, 21]
        rgb[(cls == 1) & np.isfinite(cls)] = [59, 130, 246]
        rgb[(cls == 2) & np.isfinite(cls)] = [250, 204, 21]
    else:
        rgb[(work == 0) & np.isfinite(work)] = [250, 204, 21]
        rgb[(work != 0) & np.isfinite(work)] = [59, 130, 246]

    return rgb


def preview_classified_png(tif_path: str | Path, year: int | None = None) -> bytes | None:
    """Klassifikatsiya: pushti/yashil thematic map (ISO Cluster)."""
    if not HAS_RASTERIO:
        return None
    try:
        with rasterio.open(tif_path) as src:
            band = _pick_classification_band(src)
            rgb = _paint_classified_thematic_rgb(band, src.nodata)
            buf = io.BytesIO()
            buf.write(_finalize_preview(Image.fromarray(rgb, mode='RGB'), white_bg=True))
            return buf.getvalue()
    except Exception:
        return None


def process_uploaded_tif(tif_path: str | Path, *, mode: str, year: int | None = None) -> dict:
    """Bounds + PNG preview (yil bo'yicha Landsat bandlari)."""
    path = Path(tif_path)
    bounds = leaflet_bounds_from_path(path)
    if mode == 'rgb':
        preview = preview_rgb_png(path, year=year)
    else:
        preview = preview_classified_png(path, year=year)
    return {'bounds': bounds, 'preview_png': preview}
