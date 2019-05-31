import rest_framework

from rest_framework import serializers
from rest_framework.decorators import action, permission_classes
from rest_framework.permissions import IsAuthenticated

import api.models
import api.utilities

from api.models import User, USER_THUMBNAIL_SIZE
from .attributeserializermixin import AttributeSerializerMixin
from .itemviewsetmixin import ItemViewSetMixin
from .jobviews import JobViewSetMixin
from .logviews import LogViewSetMixin

from libgravatar import Gravatar

##
## UserSerializer
##


class UserSerializer(AttributeSerializerMixin, serializers.ModelSerializer):
    """ Serializer for User profile model """

    id = serializers.EmailField(source="email")

    class Meta:
        model = User
        exclude = ("attributes", "email", "password", "user_permissions", "groups")
        lookup_field = "email"

    def to_representation(self, item):
        """ Add link to job target as a related link. """
        data = super().to_representation(item)

        # add gravatar profile image
        # https://libgravatar.readthedocs.io/en/latest/
        gravatar = Gravatar(item.email)
        data["attributes"]["photos"] = [
            {
                "value": gravatar.get_image(
                    size=USER_THUMBNAIL_SIZE, default="mm", use_ssl=True, filetype_extension=True
                ),
                "width": USER_THUMBNAIL_SIZE,
                "height": USER_THUMBNAIL_SIZE,
                "type": "thumbnail",
            }
        ]
        return data


##
## UserViewSet - list, detail, post, update and run user profiles
##


class UserViewSet(ItemViewSetMixin, JobViewSetMixin, LogViewSetMixin, rest_framework.viewsets.ModelViewSet):
    """ A user profile """

    item_class = api.models.User
    serializer_class = UserSerializer
    lookup_field = "email"

    # Normally regex would look up a slug-like id, in this case we use
    # the email address so we need a special regex, eg: https://emailregex.com/
    lookup_value_regex = r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+"

    def get_queryset(self):
        """ A user MUST be authenticated and only has access to his own user object (unless superuser) """
        assert self.request.user.is_authenticated
        if self.request.user.is_superuser:
            return User.objects.all().order_by("email")
        return User.objects.filter(email=self.request.user.email).order_by("email")

    @permission_classes((IsAuthenticated,))
    @action(methods=["get"], detail=False, url_name="me", url_path="me")
    def me(self, request):
        """ Returns profile of logged in user """
        assert request.user.email
        self.kwargs["email"] = request.user.email
        return self.retrieve(self, request)
