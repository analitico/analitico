from .tokenviews import TokenSerializer, TokenViewSet
from .projectviews import ProjectSerializer, ProjectViewSet
from .trainingviews import TrainingViewSet

from .attributeserializermixin import AttributeSerializerMixin

from .workspaceviews import WorkspaceViewSet
from .datasetviews import DatasetViewSet
from .jobviews import JobViewSet
from .recipeviews import RecipeViewSet

from .views import handle_prj_training
from .views import handle_prj_upload
from .views import handle_trn
from .views import handle_trn_activate
