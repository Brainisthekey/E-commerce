# Generated by Django 2.2 on 2021-07-22 09:15

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0002_auto_20210720_2246'),
    ]

    operations = [
        migrations.AddField(
            model_name='item',
            name='slug',
            field=models.SlugField(default='test-product'),
            preserve_default=False,
        ),
    ]
