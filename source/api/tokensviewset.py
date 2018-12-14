
# TokenSerializer and TokenViewSet for token APIs
# pylint: disable=no-member

from django.shortcuts import get_object_or_404

from rest_framework import exceptions
from rest_framework import status
from rest_framework import serializers
from rest_framework import viewsets
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
    """ List, detail, create, update and delete API authorization tokens. """

    def _tokens(self, request):
        """ Returns only tokens belonging to the authenticated user """
        return Token.objects.filter(user=request.user)

    def _token(self, request, pk):
        """ Returns a specific token (as long as it belongs to authenticated user) """
        return get_object_or_404(self._tokens(request), pk=pk)

    # inherited

    def get_permissions(self):
        """ The user needs to be authenticated in order to manage his own tokens """
        return [IsAuthenticated()]

    def list(self, request):
        """ Returns tokens belonging to the authenticated user """
        serializer = TokenSerializer(self._tokens(request), many=True)
        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        """ Returns a specific token by key """
        serializer = TokenSerializer(self._token(request, pk))
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

    def update(self, request, pk=None):
        """ Update token (note that key and user cannot be changed) """
        return self.partial_update(request, pk)

    def partial_update(self, request, pk=None):
        """ Partial updates field by field """
        token = self._token(request, pk)
        token.name = request.data.get('name')
        token.save()        
        serializer = TokenSerializer(token)
        return Response(serializer.data)

    def destroy(self, request, pk=None):
        token = self._token(request, pk)
        token.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
