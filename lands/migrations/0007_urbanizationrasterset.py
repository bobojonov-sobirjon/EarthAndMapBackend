from django.core.files.base import ContentFile
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('lands', '0006_cityboundary_monitoring_year'),
    ]

    operations = [
        migrations.CreateModel(
            name='UrbanizationRasterSet',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('year', models.PositiveIntegerField(unique=True, verbose_name='Yil')),
                ('title', models.CharField(blank=True, max_length=255, verbose_name='Sarlavha')),
                ('rgb_tif', models.FileField(upload_to='urbanization/rgb/', verbose_name='RGB GeoTIFF')),
                ('classified_tif', models.FileField(upload_to='urbanization/classified/', verbose_name='Klassifikatsiya GeoTIFF')),
                ('rgb_preview', models.ImageField(blank=True, upload_to='urbanization/previews/', verbose_name='RGB preview')),
                ('classified_preview', models.ImageField(blank=True, upload_to='urbanization/previews/', verbose_name='Klassifikatsiya preview')),
                ('rgb_bounds', models.JSONField(blank=True, default=list, verbose_name='RGB bounds')),
                ('classified_bounds', models.JSONField(blank=True, default=list, verbose_name='Klassifikatsiya bounds')),
                ('rgb_label', models.CharField(default='Landsat 7 ETM+ RGB', max_length=120, verbose_name='RGB yorliq')),
                ('classified_label', models.CharField(default='Urban extraction (ISO Cluster)', max_length=120, verbose_name='Klassifikatsiya yorliq')),
                ('urban_area_ha', models.FloatField(blank=True, null=True, verbose_name='Urban maydon (ga)')),
                ('non_urban_area_ha', models.FloatField(blank=True, null=True, verbose_name='Non-urban maydon (ga)')),
                ('note', models.TextField(blank=True, verbose_name='Izoh')),
                ('is_visible', models.BooleanField(default=True, verbose_name="Ko'rinadi")),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Urbanizatsiya xaritasi',
                'verbose_name_plural': 'Urbanizatsiya xaritalari',
                'ordering': ['-year'],
            },
        ),
    ]
