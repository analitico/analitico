# Generated by Django 2.1.5 on 2019-01-17 15:46

import api.models.call
import api.models.dataset
import api.models.items
import api.models.model
import api.models.recipe
import api.models.token
import api.models.training
import api.models.usermanager
import api.models.workspace
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import jsonfield.fields


class Migration(migrations.Migration):

    initial = True

    dependencies = [("auth", "0009_alter_user_last_name_max_length")]

    operations = [
        migrations.CreateModel(
            name="User",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("password", models.CharField(max_length=128, verbose_name="password")),
                ("last_login", models.DateTimeField(blank=True, null=True, verbose_name="last login")),
                (
                    "is_superuser",
                    models.BooleanField(
                        default=False,
                        help_text="Designates that this user has all permissions without explicitly assigning them.",
                        verbose_name="superuser status",
                    ),
                ),
                ("first_name", models.CharField(blank=True, max_length=30, verbose_name="first name")),
                ("last_name", models.CharField(blank=True, max_length=150, verbose_name="last name")),
                (
                    "is_staff",
                    models.BooleanField(
                        default=False,
                        help_text="Designates whether the user can log into this admin site.",
                        verbose_name="staff status",
                    ),
                ),
                (
                    "is_active",
                    models.BooleanField(
                        default=True,
                        help_text="Designates whether this user should be treated as active. Unselect this instead of deleting accounts.",
                        verbose_name="active",
                    ),
                ),
                ("date_joined", models.DateTimeField(default=django.utils.timezone.now, verbose_name="date joined")),
                ("email", models.EmailField(max_length=254, unique=True, verbose_name="email address")),
                ("attributes", jsonfield.fields.JSONField(blank=True, null=True, verbose_name="Attributes")),
                (
                    "groups",
                    models.ManyToManyField(
                        blank=True,
                        help_text="The groups this user belongs to. A user will get all permissions granted to each of their groups.",
                        related_name="user_set",
                        related_query_name="user",
                        to="auth.Group",
                        verbose_name="groups",
                    ),
                ),
                (
                    "user_permissions",
                    models.ManyToManyField(
                        blank=True,
                        help_text="Specific permissions for this user.",
                        related_name="user_set",
                        related_query_name="user",
                        to="auth.Permission",
                        verbose_name="user permissions",
                    ),
                ),
            ],
            options={"verbose_name": "user", "verbose_name_plural": "users", "abstract": False},
            managers=[("objects", api.models.usermanager.UserManager())],
        ),
        migrations.CreateModel(
            name="Call",
            fields=[
                ("id", models.SlugField(default=api.models.call.generate_api_id, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Created")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="Updated")),
                ("attributes", jsonfield.fields.JSONField(blank=True, null=True, verbose_name="Attributes")),
            ],
            options={"verbose_name": "call", "db_table": "api_call"},
            bases=(api.models.items.ItemMixin, models.Model),
        ),
        migrations.CreateModel(
            name="Dataset",
            fields=[
                (
                    "id",
                    models.SlugField(
                        default=api.models.dataset.generate_dataset_id,
                        primary_key=True,
                        serialize=False,
                        verbose_name="Id",
                    ),
                ),
                ("title", models.TextField(blank=True, verbose_name="Title")),
                ("description", models.TextField(blank=True, verbose_name="Description")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Created")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="Updated")),
                ("attributes", jsonfield.fields.JSONField(blank=True, null=True, verbose_name="Attributes")),
            ],
            bases=(api.models.items.ItemMixin, models.Model),
        ),
        migrations.CreateModel(
            name="Model",
            fields=[
                (
                    "id",
                    models.SlugField(
                        default=api.models.model.generate_model_id, primary_key=True, serialize=False, verbose_name="Id"
                    ),
                ),
                ("title", models.TextField(blank=True, verbose_name="Title")),
                ("description", models.TextField(blank=True, verbose_name="Description")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Created")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="Updated")),
                ("attributes", jsonfield.fields.JSONField(blank=True, null=True, verbose_name="Attributes")),
            ],
            bases=(api.models.items.ItemMixin, models.Model),
        ),
        migrations.CreateModel(
            name="Project",
            fields=[
                ("id", models.SlugField(max_length=64, primary_key=True, serialize=False)),
                ("settings", jsonfield.fields.JSONField(blank=True, null=True)),
                ("training_id", models.SlugField(blank=True)),
                ("notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "group",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to="auth.Group",
                        verbose_name="Group that has access to this project",
                    ),
                ),
                (
                    "owner",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Owner of this project",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="Recipe",
            fields=[
                (
                    "id",
                    models.SlugField(
                        default=api.models.recipe.generate_recipe_id,
                        primary_key=True,
                        serialize=False,
                        verbose_name="Id",
                    ),
                ),
                ("title", models.TextField(blank=True, verbose_name="Title")),
                ("description", models.TextField(blank=True, verbose_name="Description")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Created")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="Updated")),
                ("attributes", jsonfield.fields.JSONField(blank=True, null=True, verbose_name="Attributes")),
            ],
            bases=(api.models.items.ItemMixin, models.Model),
        ),
        migrations.CreateModel(
            name="Token",
            fields=[
                (
                    "id",
                    models.SlugField(
                        default=api.models.token.generate_token_id, max_length=32, primary_key=True, serialize=False
                    ),
                ),
                ("name", models.SlugField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Created")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="Updated")),
                ("attributes", jsonfield.fields.JSONField(blank=True, null=True)),
                (
                    "user",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="User",
                    ),
                ),
            ],
            options={"ordering": ("created_at",)},
        ),
        migrations.CreateModel(
            name="Training",
            fields=[
                (
                    "id",
                    models.SlugField(
                        default=api.models.training.generate_training_id, primary_key=True, serialize=False
                    ),
                ),
                ("status", models.SlugField(blank=True, default="Created")),
                ("settings", jsonfield.fields.JSONField(blank=True, null=True, verbose_name="Settings")),
                ("results", jsonfield.fields.JSONField(blank=True, null=True, verbose_name="Results")),
                ("notes", models.TextField(blank=True, verbose_name="Notes")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Created")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="Updated")),
                (
                    "project",
                    models.ForeignKey(
                        default=None,
                        on_delete=django.db.models.deletion.CASCADE,
                        to="api.Project",
                        verbose_name="Project",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="Workspace",
            fields=[
                (
                    "id",
                    models.SlugField(
                        default=api.models.workspace.generate_workspace_id,
                        primary_key=True,
                        serialize=False,
                        verbose_name="Id",
                    ),
                ),
                ("title", models.TextField(blank=True, verbose_name="Title")),
                ("description", models.TextField(blank=True, verbose_name="Description")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Created")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="Updated")),
                ("attributes", jsonfield.fields.JSONField(blank=True, null=True, verbose_name="Attributes")),
                (
                    "group",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to="auth.Group",
                        verbose_name="Group",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="User",
                    ),
                ),
            ],
            bases=(api.models.items.ItemMixin, models.Model),
        ),
        migrations.AddField(
            model_name="recipe",
            name="workspace",
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="api.Workspace"),
        ),
        migrations.AddField(
            model_name="model",
            name="workspace",
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="api.Workspace"),
        ),
        migrations.AddField(
            model_name="dataset",
            name="workspace",
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="api.Workspace"),
        ),
        migrations.AddField(
            model_name="call",
            name="token",
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to="api.Token"
            ),
        ),
        migrations.AddField(
            model_name="call",
            name="workspace",
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="api.Workspace"),
        ),
    ]
