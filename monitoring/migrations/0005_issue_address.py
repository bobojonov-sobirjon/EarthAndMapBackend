from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('monitoring', '0004_issue_i18n'),
    ]

    operations = [
        migrations.AddField(
            model_name='issue',
            name='address',
            field=models.CharField(blank=True, max_length=400, verbose_name='Адрес'),
        ),
    ]
