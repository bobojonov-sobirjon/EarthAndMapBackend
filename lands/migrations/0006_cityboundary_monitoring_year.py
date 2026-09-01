from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('lands', '0005_i18n_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='cityboundary',
            name='monitoring_year',
            field=models.PositiveSmallIntegerField(db_index=True, default=2026, verbose_name='Monitoring yili'),
        ),
        migrations.AlterField(
            model_name='cityboundary',
            name='code',
            field=models.SlugField(default='bukhara_city', max_length=50, verbose_name='Код'),
        ),
        migrations.AddConstraint(
            model_name='cityboundary',
            constraint=models.UniqueConstraint(
                fields=('code', 'monitoring_year'),
                name='lands_cityboundary_code_year_uniq',
            ),
        ),
    ]
