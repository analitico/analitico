# TokenSerializer and TokenViewSet for token APIs
# pylint: disable=no-member

from django.shortcuts import get_object_or_404
from django.utils.translation import gettext as _

from rest_framework import serializers
from rest_framework import status
from rest_framework import viewsets
from rest_framework import exceptions
from rest_framework import pagination
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from api.models import Token

import api.pagination
from .logviews import LogViewSetMixin

# Django ViewSet
# https://www.django-rest-framework.org/api-guide/viewsets/

# Django Serializers
# https://www.django-rest-framework.org/api-guide/serializers/


class TokenSerializer(serializers.ModelSerializer):
    """ Serializer for API authorization tokens. """

    class Meta:
        model = Token
        fields = ("id", "name", "user", "created_at")

    id = serializers.SlugField(help_text=_("Unique id."))
    name = serializers.SlugField(
        help_text=_("Name used to track token usage (eg: testing, mobile, web, server, etc)."), required=False
    )
    user = serializers.EmailField(
        source="user.email", help_text=_("User that owns the token."), required=False, read_only=True
    )
    created_at = serializers.DateTimeField(
        label=_("Created"), help_text=_("Date and time when token was created."), required=False, read_only=True
    )

    def validate_key(self, value):
        """ Check that token starts with tok_ """
        if value[:4] != "tok_":
            raise serializers.ValidationError(_("Token key should start with tok_"))
        return value

    def create(self, validated_data):
        """ Create and return a new Token instance, given the validated data """
        return Token.objects.create(**validated_data)


class TokenViewSet(LogViewSetMixin, viewsets.ModelViewSet):
    """ 
    List, detail, create, update and delete API auth tokens. 
    
    retrieve: Retrieve a specific API auth token.
    list: Retrieve a list of API auth tokens for the user.
    create: Create a new API auth token for the user.
    update: Modify a previously created API auth token (eg: change its name).
    partial_update: Modify a previously created API auth token (eg: change its name).
    delete: Delete an API auth token.
    """

    serializer_class = TokenSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if self.request.user.is_superuser:
            return Token.objects.all()
        return Token.objects.filter(user=self.request.user)

    def create(self, request):
        serializer = TokenSerializer(data=request.data)
        if serializer.is_valid():
            token = Token(pk=serializer.validated_data["id"])
            if "name" in serializer.validated_data:
                token.name = serializer.validated_data["name"]
            token.user = request.user
            token.save()
            serializer = TokenSerializer(token)
            return Response(serializer.data, status=201)
        raise exceptions.ValidationError(serializer.errors)
