
from rest_framework import pagination
from rest_framework.response import Response
from collections import OrderedDict, namedtuple

import rest_framework.renderers
import rest_framework_json_api.renderers


class JSONRenderer(rest_framework.renderers.JSONRenderer):

    def render(self, data, accepted_media_type=None, renderer_context=None):
        # change 'results' to 'data' to be more json:api-ish
        if not 'error' in data:
            data = {
                'data': data
            }
        return super().render(data, accepted_media_type, renderer_context)
