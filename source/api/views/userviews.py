import rest_framework

from rest_framework import serializers
from rest_framework.decorators import action, permission_classes
from rest_framework.permissions import IsAuthenticated

import api.models
import api.utilities

from api.models import User, USER_THUMBNAIL_SIZE
from .attributeserializermixin import AttributeSerializerMixin
from .assetviewsetmixin import AssetViewSetMixin
from .itemviewsetmixin import ItemViewSetMixin
from .jobviews import JobViewSetMixin

import hashlib
import urllib
from libgravatar import Gravatar

##
## UserSerializer
##


class UserSerializer(AttributeSerializerMixin, serializers.ModelSerializer):
    """ Serializer for User profile model """

    class Meta:
        model = User
        exclude = ("attributes", "password", "user_permissions", "groups")

    def to_representation(self, item):
        """ Add link to job target as a related link. """
        data = super().to_representation(item)

        # do not show internal id, just use email
        data["id"] = item.email

        # add gravatar profile image
        # https://libgravatar.readthedocs.io/en/latest/
        gravatar = Gravatar(item.email)
        data["attributes"]["photos"] = [
            {
                "value": gravatar.get_image(size=USER_THUMBNAIL_SIZE, default="mm", use_ssl=True, filetype_extension=True),
                "width": USER_THUMBNAIL_SIZE,
                "height": USER_THUMBNAIL_SIZE,
                "type": "thumbnail",
            }
        ]
        return data


##
## UserViewSet - list, detail, post, update and run user profiles
##


class UserViewSet(ItemViewSetMixin, JobViewSetMixin, rest_framework.viewsets.ModelViewSet):
    """ A user profile """

    item_class = api.models.User
    serializer_class = UserSerializer
    lookup_field = "email"

    def get_queryset(self):
        """ A user MUST be authenticated and only has access to objects he or his workspaces own. """
        assert not self.request.user.is_anonymous
        if self.request.user.is_superuser:
            return User.objects.all()
        return User.objects.filter(email=self.request.user.email)

    @permission_classes((IsAuthenticated,))
    @action(methods=["get"], detail=False, url_name="me", url_path="me")
    def me(self, request):
        """ Returns profile of logged in user """
        assert request.user.email
        self.kwargs["email"] = request.user.email
        return self.retrieve(self, request)
