# Generated by Django 2.1.5 on 2019-05-19 15:03

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("api", "0014_auto_20190519_1432")]

    operations = [
        migrations.AlterField(model_name="role", name="permissions", field=models.TextField(blank=True, null=True)),
        migrations.AlterField(model_name="role", name="roles", field=models.TextField(blank=True, null=True)),
    ]