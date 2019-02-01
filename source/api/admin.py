# Register models so they can be shown in admin site

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.utils.translation import ugettext_lazy as _

from .models import User, Token, Call, Project, Training
from .models import Workspace, Dataset, Recipe, Job

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


@admin.register(Call)
class ApiCallAdmin(admin.ModelAdmin):
    list_display = ("id", "token", "created_at")
    ordering = ("-created_at",)


# @admin.register(Training)
# class TrainingAdmin(admin.ModelAdmin):
#    list_display = ('id', 'project_id', 'status', 'is_active', 'records', 'rmse', 'created_at')
#    ordering = ('-updated_at',)

#
# Items
#


@admin.register(Workspace)
class WorkspaceAdmin(admin.ModelAdmin):
    fields = ("id", "user", "group", "title", "description", "attributes")
    list_display = ("id", "user", "group", "title", "description", "notes", "created_at", "updated_at", "attributes")
    search_fields = ("id", "user", "group", "title", "description", "attributes")
    ordering = ("-updated_at",)


@admin.register(Dataset)
class DatasetAdmin(admin.ModelAdmin):
    fields = ("id", "workspace", "title", "description", "attributes")
    list_display = ("id", "workspace", "title", "description", "notes", "created_at", "updated_at", "attributes")
    search_fields = ("id", "title", "description", "attributes")
    ordering = ("-updated_at",)


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    fields = ("id", "workspace", "title", "description", "attributes")
    list_display = ("id", "workspace", "title", "description", "notes", "created_at", "updated_at", "attributes")
    search_fields = ("id", "title", "description", "attributes")
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
        "attributes",
    )
    search_fields = ("id", "title", "description", "attributes")
    ordering = ("-updated_at",)
