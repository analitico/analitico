
from django.db import models
from django.contrib.auth.models import Group
from django.utils.translation import ugettext_lazy as _

from .user import User
from .item import Item

def generate_permission_id():
    from django.utils.crypto import get_random_string
    return 'prm_' + get_random_string()

##
## Permission defines access and usage permissions for Item models 
##

class Permission(models.Model):
    """ A model to define access rights for an item and its children """

    # Item rights id
    id = models.SlugField(primary_key=True, default=generate_permission_id) 

    # Item to which these permissions apply (permissions also apply to his children)
    item = models.ForeignKey(Item, on_delete=models.CASCADE, verbose_name=_('Item'))

    # User that has these permissions
    user = models.ForeignKey(User, on_delete=models.SET_NULL, blank=True, null=True, verbose_name=_('User'))

    # Group that has these permissions
    group = models.ForeignKey(Group, on_delete=models.SET_NULL, blank=True, null=True, verbose_name=_('Group'))

    # Permissions, format TBD modeled around Linux permissions
    # https://access.redhat.com/documentation/en-US/Red_Hat_Enterprise_Linux/4/html/Step_by_Step_Guide/s1-navigating-ownership.html
    permissions = models.CharField(blank=True, max_length=64, verbose_name=_('Permissions'))

    # Time when created
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created'))

    # Time when last updated
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Updated'))

    def __str__(self):
        return self.id
