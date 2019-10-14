# schemas
ANALITICO_SCHEMA = "analitico"
ANALITICO_URL_PREFIX = "analitico://"

# API endpoints
ANALITICO_STAGING_API_ENDPOINT = "https://staging.analitico.ai/api/"
ANALITICO_API_ENDPOINT = "https://analitico.ai/api/"

# actions
ACTION_PROCESS = "process"  # process a dataframe to retrieve data
ACTION_TRAIN = "train"  # train a recipe to procude a model
ACTION_PREDICT = "predict"  # run a model to generate a prediction
ACTION_DEPLOY = "deploy"  # deploy a model to a serverless endpoint

ACTION_RUN = "run"  # run a recipe, notebook or dataset notebooks
ACTION_BUILD = "build"  # build a snapshot of a recipe into a docker
ACTION_RUN_AND_BUILD = "run-and-build"  # run the recipe then build its docker/model as one job with two steps

# types/models
TYPE_PREFIX = "analitico/"
DATASET_TYPE = "dataset"
ENDPOINT_TYPE = "endpoint"
JOB_TYPE = "job"
MODEL_TYPE = "model"
NOTEBOOK_TYPE = "notebook"
RECIPE_TYPE = "recipe"
TOKEN_TYPE = "token"
USER_TYPE = "user"
WORKSPACE_TYPE = "workspace"
ROLE_TYPE = "role"
DRIVE_TYPE = "drive"

# types/others
PLUGIN_TYPE = "plugin"
WORKER_TYPE = "worker"

# IDs
DATASET_PREFIX = "ds_"  # dataset source, filters, etc
ENDPOINT_PREFIX = "ep_"  # inference endpoint configuration
JOB_PREFIX = "jb_"  # sync or async job
LOG_PREFIX = "lg_"  # log record
MODEL_PREFIX = "ml_"  # trained machine learning model (not a django model)
NOTEBOOK_PREFIX = "nb_"  # Jupyter notebook
RECIPE_PREFIX = "rx_"  # machine learning recipe (an experiment with modules, code, etc)
TOKEN_PREFIX = "tok_"  # authorization token
USER_PREFIX = "id_"  # an identity profile
WORKSPACE_PREFIX = "ws_"  # workspace with rights and one or more projects and other resources
ROLE_PREFIX = "ro_"  # access management rights via roles and permissions
DRIVE_PREFIX = "dr_"  # storage drive, mount, bucket, etc...

PLUGIN_PREFIX = "pl_"  # plugin instance (not plugin description or metadata)
WORKER_PREFIX = "wk_"  # worker process

# files suffixes
PARQUET_SUFFIXES = (".parquet",)  # Apache Parquet
CSV_SUFFIXES = (".csv",)  # Comma Separated Values
EXCEL_SUFFIXES = (".xlsx", ".xls")  # Microsoft Excel
HDF_SUFFIXES = (".h5", ".hdf5", ".he5", ".hdf", ".h4", ".hdf4", ".he2")  # Hierarchical Data Format

# suffixes for files that we can load in pandas dataframes
PANDAS_SUFFIXES = PARQUET_SUFFIXES + CSV_SUFFIXES + EXCEL_SUFFIXES + HDF_SUFFIXES

# APIs query parameters
QUERY_PARAM = "query"  # query parameter used to search and filter records, etc
ORDER_PARAM = "order"  # query parameter used to sort records, eg: ?order=firstname,lastname,-age
