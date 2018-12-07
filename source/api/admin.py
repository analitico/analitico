
# Register models so they can be shown in admin site

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.utils.translation import ugettext_lazy as _

from .models import User
from .models import Token
from .models import Call

from .models import Project
from .models import Training

# TODO customize admin site
# https://stackoverflow.com/questions/4938491/django-admin-change-header-django-administration-text/24983231#24983231
admin.site.site_header = 'Analitico.ai'

@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    """Define admin model for custom User model with no email field."""

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        (_('Personal info'), {'fields': ('first_name', 'last_name')}),
        (_('Permissions'), {'fields': ('is_active', 'is_staff', 'is_superuser',
                                       'groups', 'user_permissions')}),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2'),
        }),
    )
    list_display = ('email', 'first_name', 'last_name', 'is_staff')
    search_fields = ('email', 'first_name', 'last_name')
    ordering = ('email',)


@admin.register(Token)
class TokenAdmin(admin.ModelAdmin):
    list_display = ('key', 'user', 'name', 'created_at')
    ordering = ('user', 'name', 'created_at') 


@admin.register(Call)
class ApiCallAdmin(admin.ModelAdmin):
    list_display = ('id', 'token', 'created_at')   
    ordering = ('created_at',) 


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    pass


@admin.register(Training)
class TrainingAdmin(admin.ModelAdmin):
    list_display = ('id', 'project_id', 'status', 'is_active', 'records', 'rmse', 'created_at')
    ordering = ('created_at',) 
