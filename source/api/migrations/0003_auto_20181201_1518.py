# Generated by Django 2.1.3 on 2018-12-01 14:18

import api.models.call
import api.models.token
import api.models.training
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import jsonfield.fields


class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0009_alter_user_last_name_max_length'),
        ('api', '0002_auto_20181201_1451'),
    ]

    operations = [
        migrations.CreateModel(
            name='Call',
            fields=[
                ('id', models.SlugField(default=api.models.call.generate_api_id, primary_key=True, serialize=False)),
                ('url', models.URLField(blank=True)),
                ('method', models.CharField(blank=True, choices=[('GET', 'GET'), ('POST', 'POST'), ('PUT', 'PUT'), ('PATCH', 'PATCH'), ('OPTIONS', 'OPTIONS'), ('HEAD', 'HEAD')], max_length=16)),
                ('data', jsonfield.fields.JSONField(blank=True, null=True, verbose_name='Request received')),
                ('results', jsonfield.fields.JSONField(blank=True, null=True, verbose_name='Response sent')),
                ('status', models.IntegerField(default=200)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'call',
                'db_table': 'api_call',
            },
        ),
        migrations.CreateModel(
            name='Project',
            fields=[
                ('id', models.SlugField(max_length=64, primary_key=True, serialize=False)),
                ('settings', jsonfield.fields.JSONField(blank=True, null=True)),
                ('training_id', models.SlugField(blank=True)),
                ('notes', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('group', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='auth.Group', verbose_name='Group that has access to this project')),
                ('owner', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL, verbose_name='Owner of this project')),
            ],
        ),
        migrations.CreateModel(
            name='Training',
            fields=[
                ('id', models.SlugField(default=api.models.training.generate_training_id, primary_key=True, serialize=False)),
                ('scores', jsonfield.fields.JSONField(blank=True, null=True, verbose_name='Training scores and information')),
                ('notes', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('project', models.ForeignKey(default=None, on_delete=django.db.models.deletion.CASCADE, to='api.Project', verbose_name='Project that was trained')),
            ],
        ),
        migrations.AlterField(
            model_name='token',
            name='key',
            field=models.SlugField(default=api.models.token.generate_token_id, max_length=32, primary_key=True, serialize=False, verbose_name='Key'),
        ),
        migrations.AlterField(
            model_name='token',
            name='user',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL, verbose_name='User'),
        ),
        migrations.AddField(
            model_name='call',
            name='token',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='api.Token', verbose_name='Token used to authorize call'),
        ),
    ]
