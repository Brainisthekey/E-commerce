# Generated by Django 2.2 on 2021-07-25 08:13

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0008_auto_20210725_0959"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="orderdevilevered",
            name="item_title",
        ),
        migrations.AddField(
            model_name="orderdevilevered",
            name="item_title",
            field=models.ManyToManyField(to="core.Item"),
        ),
    ]
