# Generated by Django 2.1.3 on 2018-12-02 09:51

from django.db import migrations, models
import django.db.models.deletion
import jsonfield.fields


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0003_auto_20181201_1518'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='training',
            name='scores',
        ),
        migrations.AddField(
            model_name='training',
            name='results',
            field=jsonfield.fields.JSONField(blank=True, null=True, verbose_name='Results'),
        ),
        migrations.AlterField(
            model_name='call',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, verbose_name='Created'),
        ),
        migrations.AlterField(
            model_name='call',
            name='token',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='api.Token', verbose_name='Token'),
        ),
        migrations.AlterField(
            model_name='call',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, verbose_name='Updated'),
        ),
        migrations.AlterField(
            model_name='training',
            name='project',
            field=models.ForeignKey(default=None, on_delete=django.db.models.deletion.CASCADE, to='api.Project', verbose_name='Project'),
        ),
    ]
