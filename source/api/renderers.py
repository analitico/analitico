from collections import OrderedDict
from rest_framework import renderers

# You should apply these renderers ONLY to the APIs that need them.
# In particulare you should NOT apply the HTML renderer system wide
# otherwise most calls from browsers will be rendered as html instead
# of json which is very annoying and impractical.


class NotebookRenderer(renderers.JSONRenderer):
    """ Renders Jupyter notebooks """

    media_type = "application/x-ipynb+json"
    format = "ipynb"


class HTMLRenderer(renderers.StaticHTMLRenderer):
    """ Renders HTML as is """

    pass


class JSONRenderer(renderers.JSONRenderer):
    def render(self, data, accepted_media_type=None, renderer_context=None):
        # change results to { 'data': results } to be more json:api-ish

        # this method is used on the server to render response sent back from APIs
        # it is also used by self.client in unit test to send posts to APIs

        # supported scenarios:
        # - test is sending a single object (dictionary)
        # - test is sending multiple objects (array)
        # - response is sending single object

        # an empty list is also valid response
        if data or isinstance(data, list):

            if isinstance(data, dict):
                if "error" not in data:

                    # in json:api when "data" is present it is the only entry
                    is_jsonapi_data = "data" in data and (key in ("data", "meta", "links") for key in data.keys())
                    if not is_jsonapi_data:
                        data = OrderedDict({"data": data})

            if isinstance(data, list):
                data = OrderedDict({"data": data})

        return super().render(data, accepted_media_type, renderer_context)
