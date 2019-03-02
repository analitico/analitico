from collections import OrderedDict
from rest_framework import serializers
from rest_framework import viewsets
from rest_framework.response import Response

from api.factory import factory


class PluginSerializer(serializers.Serializer):
    """ Serializer doesn't actually serialize a plugin but rather its IPlugin.Meta information """

    def to_representation(self, item):
        data = OrderedDict({"type": "analitico/plugin"})
        for attr in ("name", "title", "description", "inputs", "outputs", "algorithm"):
            value = getattr(item.Meta, attr, None)
            if value:
                data[attr] = value
        return data


##
## PluginViewSet - list available plugins
##


class PluginViewSet(viewsets.ViewSet):
    """ List available plugins """

    def list(self, request):
        plugins = factory.get_plugins().values()
        serializer = PluginSerializer(plugins, many=True)
        return Response(serializer.data)
