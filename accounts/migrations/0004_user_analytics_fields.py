from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0003_alter_user_role'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='job_title',
            field=models.CharField(blank=True, max_length=120, verbose_name='Должность'),
        ),
        migrations.AddField(
            model_name='user',
            name='sector',
            field=models.CharField(blank=True, max_length=80, verbose_name='Сектор'),
        ),
        migrations.AddField(
            model_name='user',
            name='district',
            field=models.CharField(blank=True, max_length=120, verbose_name='Район / город'),
        ),
        migrations.AddField(
            model_name='user',
            name='purpose',
            field=models.CharField(blank=True, max_length=80, verbose_name='Цель использования'),
        ),
        migrations.AddField(
            model_name='user',
            name='interest_layers',
            field=models.CharField(blank=True, max_length=255, verbose_name='Интерес к слоям'),
        ),
        migrations.AddField(
            model_name='user',
            name='comment',
            field=models.TextField(blank=True, verbose_name='Комментарий'),
        ),
    ]
