import django.contrib.auth
import rest_framework
import urllib.parse
import datetime
import dateutil.parser
import ast
import time

from django.utils import timezone
from django.contrib.auth import models
from django.urls import reverse
from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.decorators import action, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny

import api.models
import api.utilities
import api.notifications

try:
    from allauth.account import app_settings as allauth_settings
    from allauth.utils import email_address_exists
    from allauth.account.adapter import get_adapter
except ImportError:
    raise ImportError("allauth needs to be added to INSTALLED_APPS.")

from analitico import AnaliticoException, logger
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


class UserViewSet(ItemViewSetMixin, rest_framework.viewsets.ModelViewSet):
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
        user = User.objects.create_user(email, password)
        user.is_staff = False
        user.is_superuser = False
        user.first_name = data["attributes"].pop("first_name", None)
        user.last_name = data["attributes"].pop("last_name", None)
        user.attributes = data["attributes"]
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

    ##
    ## Password Reset
    ##

    @action(
        methods=["post"],
        detail=False,
        url_name="password-reset",
        url_path="password/reset/(?P<email>.*)",
        permission_classes=[AllowAny],
    )
    def password_reset(self, request, email):
        try:
            user = api.models.User.objects.get(email=email)

            # token has user's email and expiration in 24 hours from now
            # why use timezone.now and not datetime.now?
            # https://tommikaikkonen.github.io/timezones/
            expiration = (timezone.now() + datetime.timedelta(hours=24)).isoformat()
            token = api.utilities.get_signed_secret(str({user.email: expiration}))

            url = request.build_absolute_uri(f"/app/users/password/update?token={urllib.parse.quote(token)}")
            url = url.replace("http://", "https://")
            api.notifications.email_send_template(user, "password-reset.yaml", url=url)

        except api.models.User.DoesNotExist:
            # attemps to send email to non existing users are slowed down, no specific reply
            url = reverse("api:user-password-reset", args=(email,))
            logger.warning(f"{url} was called for a non existent email")
            time.sleep(5)

        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        methods=["post"],
        detail=False,
        url_name="password-update",
        url_path="password/update",
        permission_classes=[AllowAny],
    )
    def password_update(self, request):
        data = request.data["data"]

        # token is a signed dictionary with { email: expiration }
        token = ast.literal_eval(api.utilities.get_unsigned_secret(data["token"]))

        # retrieve user's email from signed token, check link expiration
        email = next(iter(token))
        expiration = dateutil.parser.parse(token[email])
        if timezone.now() > expiration:
            msg = "The password reset link expired, please get a new reset email."
            raise AnaliticoException(msg, status_code=status.HTTP_400_BAD_REQUEST)

        # update user's password
        user = api.models.User.objects.get(email=email)
        user.set_password(data["password"])
        user.save()

        return Response(status=status.HTTP_204_NO_CONTENT)
