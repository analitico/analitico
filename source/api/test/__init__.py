import django

django.setup()

from .utils import AnaliticoApiTestCase

from .test_api_dataset import DatasetTests
from .test_api_items import ItemsTests
from .test_api_ping import PingApiTests
from .test_api_swagger import SwaggerTests
from .test_api_website import WebsiteTests
from .test_api_recipe import RecipeTests
from .test_api_user import UserTests
from .test_api_plugin import PluginTests
from .test_api_filters import FiltersTests
from .test_api_notebooks import NotebooksTests
from .test_api_docker import DockerTests
from .test_api_k8 import K8Tests
from .test_api_slack import SlackTests
