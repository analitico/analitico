
# TokenSerializer and TokenViewSet for token APIs
# pylint: disable=no-member

from django.shortcuts import get_object_or_404

from rest_framework import viewsets
from rest_framework import serializers
from rest_framework import exceptions
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from api.models import Token


class TokenSerializer(serializers.Serializer):
    """ Serialize/deserialize tokens to json """
    key = serializers.SlugField()
    name = serializers.SlugField()
    email = serializers.EmailField()
    created_at = serializers.DateTimeField()


class TokenViewSet(viewsets.ViewSet):
    """ A ViewSet to list, detail, create, update and delete API auth tokens. """

    def get_permissions(self):
        """ The user needs to be authenticated in order to manage his own tokens """
        return [IsAuthenticated()]

    def list(self, request):
        """ Returns tokens belonging to the authenticated user """
        queryset = Token.objects.filter(user=request.user)
        serializer = TokenSerializer(queryset, many=True)
        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        """ Returns a specific token by key """
        queryset = Token.objects.filter(user=request.user)
        token = get_object_or_404(queryset, pk=pk)
        serializer = TokenSerializer(token)
        return Response(serializer.data)

    def create(self, validated_data):
        """ Create a token with the given key or a random key """
        token = Token()
        if 'key' in validated_data.data: 
            key = validated_data.data['key']
            if key[:4] != 'tok_':
                key = 'tok_' + key 
            if Token.objects.filter(pk=key).exists():
                raise exceptions.ValidationError({ 'key': 'A token with this key already exists (you could leave the key empty to generate a random key)' })
            token.key = key
        if 'name' in validated_data.data:
            token.name = validated_data.data['name']
        token.user = validated_data.user
        token.save()
        serializer = TokenSerializer(token)
        return Response(serializer.data)
