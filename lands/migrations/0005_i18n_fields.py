from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('lands', '0004_mahalla_monitoringrecord_monitoringyear_and_more'),
    ]

    operations = [
        migrations.AddField(model_name='landcategory', name='name_en', field=models.CharField(blank=True, max_length=200, verbose_name='Название (EN)')),
        migrations.AddField(model_name='landcategory', name='description_ru', field=models.TextField(blank=True, verbose_name='Описание (RU)')),
        migrations.AddField(model_name='landcategory', name='description_en', field=models.TextField(blank=True, verbose_name='Описание (EN)')),
        migrations.AddField(model_name='cityboundary', name='name_ru', field=models.CharField(blank=True, max_length=100, verbose_name='Название (RU)')),
        migrations.AddField(model_name='cityboundary', name='name_en', field=models.CharField(blank=True, max_length=100, verbose_name='Название (EN)')),
        migrations.AddField(model_name='publicland', name='name_ru', field=models.CharField(blank=True, max_length=255, verbose_name='Название (RU)')),
        migrations.AddField(model_name='publicland', name='name_en', field=models.CharField(blank=True, max_length=255, verbose_name='Название (EN)')),
        migrations.AddField(model_name='publicland', name='address_ru', field=models.CharField(blank=True, max_length=500, verbose_name='Адрес (RU)')),
        migrations.AddField(model_name='publicland', name='address_en', field=models.CharField(blank=True, max_length=500, verbose_name='Адрес (EN)')),
        migrations.AddField(model_name='publicland', name='description_ru', field=models.TextField(blank=True, verbose_name='Описание (RU)')),
        migrations.AddField(model_name='publicland', name='description_en', field=models.TextField(blank=True, verbose_name='Описание (EN)')),
        migrations.AddField(model_name='urbanizationlayer', name='name_ru', field=models.CharField(blank=True, max_length=200, verbose_name='Название (RU)')),
        migrations.AddField(model_name='urbanizationlayer', name='name_en', field=models.CharField(blank=True, max_length=200, verbose_name='Название (EN)')),
        migrations.AddField(model_name='urbanizationlayer', name='note_ru', field=models.TextField(blank=True, verbose_name='Примечание (RU)')),
        migrations.AddField(model_name='urbanizationlayer', name='note_en', field=models.TextField(blank=True, verbose_name='Примечание (EN)')),
        migrations.AddField(model_name='systemnotice', name='title_ru', field=models.CharField(blank=True, max_length=200, verbose_name='Заголовок (RU)')),
        migrations.AddField(model_name='systemnotice', name='title_en', field=models.CharField(blank=True, max_length=200, verbose_name='Заголовок (EN)')),
        migrations.AddField(model_name='systemnotice', name='message_ru', field=models.TextField(blank=True, verbose_name='Текст (RU)')),
        migrations.AddField(model_name='systemnotice', name='message_en', field=models.TextField(blank=True, verbose_name='Текст (EN)')),
        migrations.AddField(model_name='mahalla', name='name_ru', field=models.CharField(blank=True, max_length=200, verbose_name='Название (RU)')),
        migrations.AddField(model_name='mahalla', name='name_en', field=models.CharField(blank=True, max_length=200, verbose_name='Название (EN)')),
        migrations.AddField(model_name='monitoringrecord', name='description_ru', field=models.TextField(blank=True, verbose_name='Описание (RU)')),
        migrations.AddField(model_name='monitoringrecord', name='description_en', field=models.TextField(blank=True, verbose_name='Описание (EN)')),
    ]
