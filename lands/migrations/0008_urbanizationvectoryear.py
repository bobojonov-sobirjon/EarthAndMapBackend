from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('lands', '0007_urbanizationrasterset'),
    ]

    operations = [
        migrations.CreateModel(
            name='UrbanizationVectorYear',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('year', models.PositiveIntegerField(unique=True, verbose_name='Yil')),
                ('geojson', models.FileField(blank=True, upload_to='urbanization/vector/', verbose_name='GeoJSON')),
                ('class_field', models.CharField(default='class', max_length=64, verbose_name='Klass maydoni')),
                ('feature_count', models.PositiveIntegerField(default=0, verbose_name="Ob'ektlar soni")),
                ('urban_area_ha', models.FloatField(blank=True, null=True, verbose_name='Urban maydon (ga)')),
                ('non_urban_area_ha', models.FloatField(blank=True, null=True, verbose_name='Non-urban maydon (ga)')),
                ('bounds', models.JSONField(blank=True, default=list, verbose_name='Bounds')),
                ('source_name', models.CharField(blank=True, max_length=255, verbose_name='Manba fayl')),
                ('note', models.TextField(blank=True, verbose_name='Izoh')),
                ('is_visible', models.BooleanField(default=True, verbose_name="Ko'rinadi")),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Urbanizatsiya vektor qatlami',
                'verbose_name_plural': 'Urbanizatsiya vektor qatlamlari',
                'ordering': ['-year'],
            },
        ),
    ]
