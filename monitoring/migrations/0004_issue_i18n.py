from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('monitoring', '0003_alter_issue_options_issue_geometry_and_more'),
    ]

    operations = [
        migrations.AddField(model_name='issue', name='title_ru', field=models.CharField(blank=True, max_length=255, verbose_name='Заголовок (RU)')),
        migrations.AddField(model_name='issue', name='title_en', field=models.CharField(blank=True, max_length=255, verbose_name='Заголовок (EN)')),
        migrations.AddField(model_name='issue', name='description_ru', field=models.TextField(blank=True, verbose_name='Описание (RU)')),
        migrations.AddField(model_name='issue', name='description_en', field=models.TextField(blank=True, verbose_name='Описание (EN)')),
    ]
