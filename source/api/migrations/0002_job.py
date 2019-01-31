# Generated by Django 2.1.5 on 2019-01-31 08:44

import api.models.items
import api.models.job
from django.db import migrations, models
import django.db.models.deletion
import jsonfield.fields


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Job',
            fields=[
                ('id', models.SlugField(default=api.models.job.generate_job_id, primary_key=True, serialize=False)),
                ('title', models.TextField(blank=True)),
                ('description', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='created')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='updated')),
                ('attributes', jsonfield.fields.JSONField(blank=True, null=True)),
                ('status', models.SlugField(blank=True, default='created')),
                ('workspace', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='api.Workspace')),
            ],
            bases=(api.models.items.ItemsMixin, models.Model),
        ),
    ]
