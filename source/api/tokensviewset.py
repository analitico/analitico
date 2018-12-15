
# TokenSerializer and TokenViewSet for token APIs
# pylint: disable=no-member

from django.shortcuts import get_object_or_404

from rest_framework import serializers
from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from api.models import Token


class TokenSerializer(serializers.Serializer):
    """ Serializer for API authorization tokens. """
    key = serializers.SlugField()
    name = serializers.SlugField()
    
    # Email address of token's owner
    email = serializers.EmailField()
    """ Email address of token owner """

    created_at = serializers.DateTimeField()
    """ Token creation timestamp. """


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

    def partial_update(self, request, pk=None):
        token = get_object_or_404(self.get_queryset(), pk=pk)
        token.name = request.data.get('name')
        token.save()        
        serializer = TokenSerializer(token)
        return Response(serializer.data)

    def update(self, request, pk=None):
        return self.partial_update(request, pk)
