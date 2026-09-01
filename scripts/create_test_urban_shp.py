"""Minimal Urbanization_2010 shapefile for local API tests."""
import shapefile as shp
from pathlib import Path

root = Path(__file__).resolve().parents[1] / 'test_data'
root.mkdir(exist_ok=True)
base = root / 'Urbanization_2010'

with shp.Writer(str(base)) as w:
    w.field('class', 'N')
    w.poly([[[64.40, 39.75], [64.42, 39.75], [64.42, 39.77], [64.40, 39.77], [64.40, 39.75]]])
    w.record(0)
    w.poly([[[64.43, 39.76], [64.45, 39.76], [64.45, 39.78], [64.43, 39.78], [64.43, 39.76]]])
    w.record(1)

(base.with_suffix('.prj')).write_text(
    'GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563]],'
    'PRIMEM["Greenwich",0],UNIT["degree",0.0174532925199433]]',
    encoding='ascii',
)
print('OK:', sorted(root.glob('Urbanization_2010*')))
