
# TokenSerializer and TokenViewSet for token APIs
# pylint: disable=no-member

from django.shortcuts import get_object_or_404
from django.utils.translation import gettext as _

from rest_framework import serializers
from rest_framework import status
from rest_framework import viewsets
from rest_framework import exceptions
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from api.models import Token

# Django ViewSet
# 

# Django Serializers
# https://www.django-rest-framework.org/api-guide/serializers/

class TokenSerializer(serializers.ModelSerializer):
    """ Serializer for API authorization tokens. """

    class Meta:
        model = Token
        fields = ('id', 'name', 'email', 'created_at')

    # Use this method for the custom field
    def _user(self):
        request = getattr(self.context, 'request', None)
        if request:
            return request.user

    def validate_key(self, value):
        """ Check that token starts with tok_ """
        if value[:4] != 'tok_':
            raise serializers.ValidationError(_('Token key should start with tok_'))
        return value

    def create(self, validated_data):
        """ Create and return a new Token instance, given the validated data """
        return Token.objects.create(**validated_data)


class TokenViewSet(viewsets.ModelViewSet):
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
            token = Token(pk=serializer.validated_data['id'])
            if 'name' in serializer.validated_data:
                token.name = serializer.validated_data['name']
            token.user = request.user
            token.save()
            serializer = TokenSerializer(token)
            return Response(serializer.data, status=201)
        raise exceptions.ValidationError(serializer.errors)
