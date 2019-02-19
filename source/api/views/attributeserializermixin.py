# ItemSerializer and ItemViewSet for item APIs
# pylint: disable=no-member

import os

from django.utils.text import slugify
from django.http.response import StreamingHttpResponse
from django.utils.http import parse_http_date_safe, http_date
from django.utils.timezone import now
from django.urls import reverse

import rest_framework
import rest_framework.viewsets

from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action, permission_classes
from rest_framework.exceptions import NotFound, MethodNotAllowed, APIException
from rest_framework.parsers import JSONParser, FileUploadParser, MultiPartParser
from rest_framework import status

import analitico
from analitico import TYPE_PREFIX
from api.factory import ModelsFactory
from api.models import ItemMixin, Job, User
from analitico.utilities import logger

# Django Serializers
# https://www.django-rest-framework.org/api-guide/serializers/
# Django ViewSet
# https://www.django-rest-framework.org/api-guide/viewsets/
# Examples of url patterns:
# https://simpleisbetterthancomplex.com/references/2016/10/10/url-patterns.html


class AttributeSerializerMixin:
    """
    A serializer for a generic model which is used to store different kinds of objects. All of them
    have a few fields in common while the rest of the payload is stored in 'json', a dictionary.
    This allows easy extension without having to refactor the SQL storage continuosly and introduce
    new migrations and releases. Also different versions can coexist and ignore extra data.
    """

    def get_item_url(self, item):
        """ Returns absolute url to given item using the same endpoint the request came in through """
        assert isinstance(item, ItemMixin)

        item_id = item.id
        if isinstance(item, User):
            item_id = item.email

        url = reverse("api:" + item.type + "-detail", args=(item_id,))
        request = self.context.get("request")
        if request:
            url = request.build_absolute_uri(url)
            url = url.replace("http://", "https://")
        return url

    def get_item_id_url(self, item_id):
        """ Returns absolute url to given item (by id) using the same endpoint the request came in through """
        assert isinstance(item_id, str)
        item = ModelsFactory.from_id(item_id)
        return self.get_item_url(item) if item else None, item.type

    def get_item_asset_url(self, item, asset_class, asset_id):
        """ Returns absolute url to given item's asset """
        try:
            # TODO debug reverse and see why it breaks
            # url = reverse("api:" + item.type + "-asset-detail", args=(item.id, asset_class, asset_id))
            url = "/api/{}s/{}/{}/{}".format(item.type, item.id, asset_class, asset_id)
            request = self.context.get("request")
            if request:
                url = request.build_absolute_uri(url)
                url = url.replace("http://", "https://")
            return url
        except Exception as exc:
            raise exc

    def to_representation(self, item):
        """ Serialize object to dictionary, extracts all json key to main level """
        data = super().to_representation(item)

        # rename workspace -> workspace_id for consistency
        workspace_id = data.pop("workspace", None)
        if workspace_id:
            data["workspace_id"] = workspace_id

        reformatted = {"type": TYPE_PREFIX + item.type, "id": data.pop("id"), "attributes": data}

        # add link to self
        reformatted["links"] = {"self": self.get_item_url(item)}

        # add additional attributes from json dict
        if item.attributes:
            for key, value in item.attributes.items():
                # skip nulls
                if value:
                    data[key] = item.attributes[key]
                    if key.endswith("_id"):
                        # Hypermedia As The Engine Of Application State:
                        # if the attributes ends with _id it is (likely) a reference
                        # to a connected item, like a recipe_id for a model or a
                        # model_id for an endpoint, etc. we implement HATEAOS by
                        # introducing automatic links to all related items endpoints
                        try:
                            item_url, _ = self.get_item_id_url(value)
                            if item_url:
                                reformatted["links"][key[:-3]] = item_url
                        except Exception as exc:
                            message = "AttributeSerializerMixin.to_representation - error building link for " + value
                            logger.warning(message, exc_info=exc)
                            pass

        # add links to /assets and /data
        for asset_class in ("assets", "data"):
            if asset_class in data:
                for asset in data[asset_class]:
                    asset["url"] = self.get_item_asset_url(item, asset_class, asset["id"])
        return reformatted

    def to_internal_value(self, data):
        """ Convert dictionary to internal representation (all unknown fields go into json) """
        # If this payload is in json:api format it will have a 'data'
        # element which contains the actual payload. If in json format
        # it will just have a regular dictionary with the data directly in it
        if "data" in data:
            data = data["data"]

        if "type" in data:
            assert data["type"].startswith(TYPE_PREFIX)
            data["type"] = data["type"][len(TYPE_PREFIX) :]

        # works with input in json:api style (attributes) or flat json
        attributes = data.pop("attributes") if "attributes" in data else data.copy()

        # rename workspace_id -> workspace for consistency
        workspace_id = attributes.pop("workspace_id", None)
        if workspace_id:
            attributes["workspace"] = workspace_id

        for (key, _) in self.fields.fields.items():
            if key in attributes:
                data[key] = attributes.pop(key)

        # Perform the data validation, eg:
        # if not blabla:
        #    raise serializers.ValidationError({
        #        'blabla': 'This field is required.'
        #    })
        # Use regular serializer for everything but the json contents which go as-is
        validated = super().to_internal_value(data)
        validated["attributes"] = attributes
        # Return the validated values which will be available as `.validated_data`.
        return validated
