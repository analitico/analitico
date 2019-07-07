import django.contrib.auth

import rest_framework
from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.decorators import action, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny

import api.models
import api.utilities

try:
    from allauth.account import app_settings as allauth_settings
    from allauth.utils import email_address_exists
    from allauth.account.adapter import get_adapter
except ImportError:
    raise ImportError("allauth needs to be added to INSTALLED_APPS.")

from analitico import AnaliticoException
from api.models import User, USER_THUMBNAIL_SIZE
from .attributeserializermixin import AttributeSerializerMixin
from .itemviewsetmixin import ItemViewSetMixin
from .jobviews import JobViewSetMixin

from libgravatar import Gravatar

# Internal documentation
# https://github.com/analitico/analitico/wiki/Authentication

# Using the Django authentication system
# https://docs.djangoproject.com/en/2.2/topics/auth/default/

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

    def validate_email(self, email):
        email = get_adapter().clean_email(email)
        if allauth_settings.UNIQUE_EMAIL:
            if email and email_address_exists(email):
                raise serializers.ValidationError("A user is already registered with this e-mail address.")
        return email

    def validate_password1(self, password):
        return get_adapter().clean_password(password)

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


class UserViewSet(ItemViewSetMixin, JobViewSetMixin, rest_framework.viewsets.ModelViewSet):
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

    ##
    ## Sign in and Sign up can be used without authentication
    ##

    # Implementation is similar in scope to django-rest-auth:
    # https://github.com/Tivix/django-rest-auth

    @action(methods=["post"], detail=False, url_name="signup", url_path="signup", permission_classes=[AllowAny])
    def signup(self, request):
        """ Sign up and create a new user. """
        data = request.data["data"]

        # pop email
        email = data.pop("id", None)
        data["attributes"].pop("email", None)
        if not email:
            raise AnaliticoException("You need to provide a valid email address.", status=status.HTTP_400_BAD_REQUEST)
        if api.models.User.objects.filter(email=email).exists():
            raise AnaliticoException("A user already exists with this email.", status=status.HTTP_403_FORBIDDEN)

        # TODO use all auth authenticator for password rules, etc
        password = data["attributes"].pop("password")
        if not password or len(password) < 4:
            raise AnaliticoException("You need to provide a valid password.", status=status.HTTP_400_BAD_REQUEST)

        # create and return new user
        user = User(email=email, attributes=data["attributes"])
        user.set_password(password)  # will save salted and hashed
        user.save()
        return Response(self.serializer_class(user).data, status=status.HTTP_201_CREATED)

    @action(methods=["post"], detail=False, url_name="signin", url_path="signin", permission_classes=[IsAuthenticated])
    def signin(self, request):
        """ Sign in user to current session, returns user information. """
        user = request.user
        django.contrib.auth.login(request, user, "django.contrib.auth.backends.ModelBackend")
        return Response(self.serializer_class(user).data)

    @permission_classes((IsAuthenticated,))
    @action(methods=["post"], detail=False, url_name="signout", url_path="signout")
    def signout(self, request):
        """ Sign out user from current session. """
        django.contrib.auth.logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)
