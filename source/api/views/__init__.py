
from .itemviews import WorkspaceViewSet, DatasetViewSet
from .tokenviews import TokenSerializer, TokenViewSet
from .projectviews import ProjectSerializer, ProjectViewSet
from .trainingviews import TrainingViewSet

from .views import handle_prj_training
from .views import handle_prj_upload

from .views import handle_trn
from .views import handle_trn_activate

