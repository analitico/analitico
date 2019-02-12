# Generated by Django 2.1.5 on 2019-02-09 11:11

import api.models.endpoint
import api.models.items
from django.db import migrations, models
import django.db.models.deletion
import jsonfield.fields


class Migration(migrations.Migration):

    dependencies = [("api", "0004_auto_20190201_1524")]

    operations = [
        migrations.CreateModel(
            name="Endpoint",
            fields=[
                (
                    "id",
                    models.SlugField(
                        default=api.models.endpoint.generate_endpoint_id, primary_key=True, serialize=False
                    ),
                ),
                ("title", models.TextField(blank=True)),
                ("description", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("attributes", jsonfield.fields.JSONField(blank=True, null=True)),
                ("workspace", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="api.Workspace")),
            ],
            bases=(api.models.items.ItemMixin, api.models.items.ItemAssetsMixin, models.Model),
        )
    ]