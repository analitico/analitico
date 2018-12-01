
# Register models so they can be shown in admin site

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.utils.translation import ugettext_lazy as _

from .models import User
from .models import Project
from .models import Training
from .models import ApiCall
from .models import Token

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


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    pass

@admin.register(Training)
class TrainingAdmin(admin.ModelAdmin):
    pass

@admin.register(ApiCall)
class ApiCallAdmin(admin.ModelAdmin):
    list_display = ('id', 'token', 'created_at')   
    ordering = ('created_at',) 

# @admin.register(Token)
# class TokenAdmin(admin.ModelAdmin):
#    pass
