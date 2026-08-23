from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0004_user_analytics_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='region',
            field=models.CharField(blank=True, max_length=120, verbose_name='Область'),
        ),
    ]
