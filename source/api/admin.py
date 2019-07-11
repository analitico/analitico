# Register models so they can be shown in admin site

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.utils.translation import ugettext_lazy as _

from .models import User, Token
from .models import Workspace, Dataset, Recipe, Job, Model, Endpoint, Notebook, Role, Drive

# TODO customize admin site
# https://stackoverflow.com/questions/4938491/django-admin-change-header-django-administration-text/24983231#24983231
admin.site.site_header = "Analitico.ai"


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    """Define admin model for custom User model with no email field."""

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (_("Personal info"), {"fields": ("first_name", "last_name")}),
        (_("Permissions"), {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        (_("Attributes"), {"fields": ("attributes",)}),
        (_("Important dates"), {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = ((None, {"classes": ("wide",), "fields": ("email", "password1", "password2")}),)
    list_display = ("email", "first_name", "last_name", "is_staff")
    search_fields = ("email", "first_name", "last_name")
    ordering = ("email",)


@admin.register(Token)
class TokenAdmin(admin.ModelAdmin):
    list_display = ("id", "email", "name", "created_at")
    ordering = ("name", "-created_at")


@admin.register(Workspace)
class WorkspaceAdmin(admin.ModelAdmin):
    fields = ("id", "user", "group", "title", "description", "attributes")
    list_display = ("id", "user", "group", "title", "description", "notes", "created_at", "updated_at")
    search_fields = ("id", "user", "group", "title", "description", "attributes")
    ordering = ("-updated_at",)


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    fields = ("id", "workspace", "user", "roles", "permissions", "attributes")
    list_display = ("id", "workspace", "user", "roles", "permissions", "created_at", "updated_at")
    search_fields = ("id", "workspace", "user", "roles", "permissions", "attributes")
    ordering = ("-updated_at",)


@admin.register(Dataset)
class DatasetAdmin(admin.ModelAdmin):
    fields = ("id", "workspace", "title", "description", "attributes", "notebook")
    list_display = ("id", "workspace", "title", "description", "notes", "created_at", "updated_at")
    search_fields = ("id", "title", "description", "attributes", "notebook")
    ordering = ("-updated_at",)


@admin.register(Notebook)
class NotebookAdmin(admin.ModelAdmin):
    fields = ("id", "workspace", "title", "description", "attributes", "notebook")
    list_display = ("id", "workspace", "title", "description", "created_at", "updated_at")
    search_fields = ("id", "title", "description", "attributes")
    ordering = ("-updated_at",)


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    fields = ("id", "workspace", "title", "description", "attributes", "notebook")
    list_display = ("id", "workspace", "title", "description", "notes", "created_at", "updated_at")
    search_fields = ("id", "title", "description", "attributes", "notebook")
    ordering = ("-updated_at",)


@admin.register(Model)
class ModelAdmin(admin.ModelAdmin):
    fields = ("id", "workspace", "title", "description", "attributes", "notebook")
    list_display = ("id", "workspace", "title", "description", "notes", "created_at", "updated_at")
    search_fields = ("id", "title", "description", "attributes", "notebook")
    ordering = ("-updated_at",)


@admin.register(Endpoint)
class EndpointAdmin(admin.ModelAdmin):
    fields = ("id", "workspace", "title", "description", "attributes")
    list_display = ("id", "workspace", "title", "description", "notes", "created_at", "updated_at")
    search_fields = ("id", "title", "description", "attributes")
    ordering = ("-updated_at",)

@admin.register(Drive)
class DriveAdmin(admin.ModelAdmin):
    fields = ("id", "title", "attributes")
    list_display = ("id", "workspace", "title", "created_at", "updated_at")
    search_fields = ("id", "title", "attributes")
    ordering = ("-updated_at",)


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    fields = ("id", "workspace", "title", "description", "action", "item_id", "status", "attributes")
    list_display = (
        "id",
        "workspace",
        "action",
        "item_id",
        "status",
        "title",
        "description",
        "notes",
        "created_at",
        "updated_at",
    )
    search_fields = ("id", "title", "description", "attributes", "status", "action")
    ordering = ("-updated_at",)
