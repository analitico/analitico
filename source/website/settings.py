"""
Django settings for analitico.ai

Some settings like passwords, keys, etc are private and should not be in the git repo.
These are stored in a separate environment variables which are loaded at runtime.
This also makes it easier to have separate development settings vs production settings, etc. 
A blank template is available and can be customized, see 

For more information on this file, see
https://docs.djangoproject.com/en/2.1/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/2.1/ref/settings/
"""

import os
import logging.config
import sys
import tempfile
import stripe

import analitico.logging
from analitico.utilities import save_text, read_json
from rest_framework.exceptions import APIException

try:

    # Covers pytest, regular testing and django-coverage
    TESTING = False
    if (
        sys.argv[0].endswith("pytest.py")
        or sys.argv[0].endswith("testlauncher.py")
        or ("pytest.py" in sys.argv)
        or ("test" in sys.argv)
        or ("test_coverage" in sys.argv)
    ):
        TESTING = True

    # SECURITY WARNING: don't run with debug turned on in production!
    DEBUG = os.environ.get("ANALITICO_DEBUG", "False").lower() == "true"
    PRODUCTION = os.environ.get("ANALITICO_PRODUCTION", "False").lower() == "true"
    assert not (DEBUG and PRODUCTION), "SECURITY WARNING: don't run with debug turned on in production"

    ##
    ## Django cache is based on local file system and is temporary
    ## https://docs.djangoproject.com/en/2.2/topics/cache/#cache-arguments
    ##

    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.filebased.FileBasedCache",
            "LOCATION": os.path.join(tempfile.gettempdir(), "analitico_djang_temp"),
            "TIMEOUT": 30 * 60,
            "OPTIONS": {"MAX_ENTRIES": 5000},
        }
    }

    ##
    ## Stripe billing
    ##

    # These are test tokens, actual tokens are in secrets
    ANALITICO_STRIPE_SECRET_KEY = "sk_test_HOYuiExkdXkVdrhov3M6LwQQ"
    if not TESTING and PRODUCTION:
        ANALITICO_STRIPE_SECRET_KEY = os.environ.get("ANALITICO_STRIPE_SECRET_KEY", ANALITICO_STRIPE_SECRET_KEY)
    assert ANALITICO_STRIPE_SECRET_KEY, "Are you missing the environment variable ANALITICO_STRIPE_SECRET_KEY?"
    stripe.api_key = ANALITICO_STRIPE_SECRET_KEY

    ###
    ### Logging (setup log first so at least if there's an error you get it logged)
    ###

    # Examples of logging configuration:
    # https://lincolnloop.com/blog/django-logging-right-way/

    LOGLEVEL = os.environ.get("LOGLEVEL", "info").upper()

    LOGGING_CONFIG = None
    if TESTING:
        logging.config.dictConfig(
            {
                "version": 1,
                "disable_existing_loggers": False,
                "formatters": {
                    "console": {
                        # exact format is not important, this is the minimum information
                        "format": "%(asctime)s %(name)-12s %(levelname)-8s %(message)s"
                    }
                },
                "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "console"}},
                "loggers": {
                    # root logger
                    "": {"level": "INFO", "handlers": ["console"]}
                },
            }
        )
    else:
        logging.config.dictConfig(
            {
                "version": 1,
                "disable_existing_loggers": False,
                "formatters": {
                    # format messages as json in a way that is easily readable by our fluentd
                    # while preserving the log messages' metadata (eg. level, function, line, logger, etc)
                    "json": {"()": analitico.logging.FluentdFormatter, "format": "%(asctime)s %(message)s"}
                },
                "handlers": {
                    "json": {
                        "level": "INFO",
                        "class": "logging.StreamHandler",
                        "formatter": "json",
                        "stream": "ext://sys.stderr",
                    }
                },
                "loggers": {
                    # root logger
                    "": {"level": "INFO", "handlers": ["json"]}
                },
            }
        )

    # Build paths inside the project like this: os.path.join(BASE_DIR, ...)
    # Project is always started with currenct directory in /analitico/source/
    # base directory is the one where manage.py is also found
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    # SECURITY WARNING: keep the secret key used in production secret!
    SECRET_KEY = os.environ["ANALITICO_SECRET_KEY"]

    # We connect to MySQL using SSL so we need the proper certificates
    sql_ssl_key_path = os.path.join(BASE_DIR, "../../analitico-ci/ssl/cloudsql/client-key.pem")
    sql_ssl_cert_path = os.path.join(BASE_DIR, "../../analitico-ci/ssl/cloudsql/client-cert.pem")
    sql_ssl_ca_path = os.path.join(BASE_DIR, "../../analitico-ci/ssl/cloudsql/server-ca.pem")

    # assert os.path.isfile(sql_ssl_key_path), sql_ssl_key_path + " is missing, please install"
    # assert os.path.isfile(sql_ssl_cert_path), sql_ssl_cert_path + " is missing, please install"
    # assert os.path.isfile(sql_ssl_ca_path), sql_ssl_ca_path + " is missing, please install"

    # MySQL database
    DATABASES = {
        "default": {
            "ENGINE": "mysql.connector.django",
            "PORT": "3306",
            "NAME": os.environ.get("ANALITICO_MYSQL_NAME", "analitico"),
            "HOST": os.environ["ANALITICO_MYSQL_HOST"],
            "USER": os.environ["ANALITICO_MYSQL_USER"],
            "PASSWORD": os.environ["ANALITICO_MYSQL_PASSWORD"],
            "CONN_MAX_AGE": 120,  # connection stays on for two minutes
            "OPTIONS": {"ssl_key": sql_ssl_key_path, "ssl_cert": sql_ssl_cert_path, "ssl_ca": sql_ssl_ca_path},
        }
    }

    if TESTING:
        DATABASES = {
            "default": {"ENGINE": "django.db.backends.sqlite3", "NAME": os.path.join(BASE_DIR, "analitico.sqlite")}
        }


    # WARNING: Private sql keys are included in /conf
    # They can later be easily removed and rotated out of service
    # https://dev.mysql.com/doc/refman/5.5/en/mysql-ssl-set.html

    # We are keeping file storage cloud independent so that we can use whichever
    # cloud makes the most sense and also give customers an option to bring their own
    # cloud storage configuration. Each workspace can have its own configuration which
    # is used for all assets belonging to the workspace and its children. If the workspace
    # does not have a storage configured, the following configuration is used as a default.

    GCS_KEY_FILENAME = os.path.realpath(
        os.path.join(os.path.dirname(__file__), "../../../analitico-ci/gcloud/analitico-api-service-account-key.json")
    )
    gcs_key = read_json(GCS_KEY_FILENAME)

    ANALITICO_STORAGE = {
        "driver": "google-storage",
        "container": "data.analitico.ai",
        "basepath": "",
        "credentials": {
            "key": gcs_key["client_email"],
            "secret": gcs_key["private_key"],
            "project": gcs_key["project_id"],
        },
    }

    # Special storage for regular testing and django-coverage
    if "test" in sys.argv or "test_coverage" in sys.argv:
        ANALITICO_STORAGE["container"] = "test.analitico.ai"

    # List of domains serving the app, can be customized as needed
    ALLOWED_HOSTS = [
        "127.0.0.1",
        "localhost",
        "analitico.ai",  # main domain
        ".analitico.ai",  # any subdomain
        "138.201.196.111",  # s1.analitico.ai
        "78.46.46.165",  # s2.analitico.ai
        "159.69.242.143",  # s5.analitico.ai
        # serve webdav proxy mount
        "*.cloud.analitico.ai",
        # for local testing
        "analitico.test",
        # server local clients in LAN
        "192.168.1.*:8000",
        "192.168.1.*",
    ]

    # X-Forwarded-Host header used in preference to the Host header #205
    USE_X_FORWARDED_HOST = True

    # Disable maximum upload size
    DATA_UPLOAD_MAX_MEMORY_SIZE = None

    # Application definition
    INSTALLED_APPS = [
        "api",
        "website",
        "gunicorn",
        "rest_framework",
        "django_filters",
        "drf_yasg",  # openapi schema generator
        "django.contrib.admin",
        "django.contrib.auth",
        "django.contrib.contenttypes",
        "django.contrib.messages",
        "django.contrib.sessions",
        "django.contrib.staticfiles",
        "django.contrib.sites",
        "allauth",
        "allauth.account",
        "allauth.socialaccount",
        # include the providers you want to enable...
        # https://django-allauth.readthedocs.io/en/latest/installation.html
        "allauth.socialaccount.providers.google",
        "allauth.socialaccount.providers.github",
        "allauth.socialaccount.providers.windowslive",
        "corsheaders",
    ]

    MIDDLEWARE = [
        "api.webdav.WebDavProxyMiddleware",
        "corsheaders.middleware.CorsMiddleware",
        "django.middleware.security.SecurityMiddleware",
        "django.contrib.sessions.middleware.SessionMiddleware",
        "django.middleware.http.ConditionalGetMiddleware",
        "django.middleware.common.CommonMiddleware",
        "django.middleware.csrf.CsrfViewMiddleware",
        "django.contrib.auth.middleware.AuthenticationMiddleware",
        "django.contrib.messages.middleware.MessageMiddleware",
        "django.middleware.clickjacking.XFrameOptionsMiddleware",
    ]

    ROOT_URLCONF = "website.urls"

    TEMPLATES = [
        {
            "BACKEND": "django.template.backends.django.DjangoTemplates",
            "DIRS": [os.path.join(BASE_DIR, "templates")],
            "APP_DIRS": True,
            "OPTIONS": {
                "context_processors": [
                    "django.template.context_processors.debug",
                    "django.template.context_processors.request",
                    "django.contrib.auth.context_processors.auth",
                    "django.contrib.messages.context_processors.messages",
                ]
            },
        }
    ]

    # CORS Configuration
    CORS_ORIGIN_ALLOW_ALL = True
    CORS_ALLOW_CREDENTIALS = True

    CORS_ALLOW_HEADERS = (
        "accept",
        "accept-encoding",
        "authorization",
        "content-disposition",
        "content-type",
        "dnt",
        "origin",
        "user-agent",
        "x-csrftoken",
        "x-requested-with",
    )

    WSGI_APPLICATION = "website.wsgi.application"

    # User substitution
    # https://docs.djangoproject.com/en/1.11/topics/auth/customizing/#auth-custom-user
    AUTH_USER_MODEL = "api.User"

    # Password validation
    # https://docs.djangoproject.com/en/2.1/ref/settings/#auth-password-validators
    AUTH_PASSWORD_VALIDATORS = [
        {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
        {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
        {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
        {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
    ]

    AUTHENTICATION_BACKENDS = (
        # Needed to login by username in Django admin, regardless of `allauth`
        "django.contrib.auth.backends.ModelBackend",
        # `allauth` specific authentication methods, such as login by e-mail
        "allauth.account.auth_backends.AuthenticationBackend",
    )

    # Must match the site configured in /admin/sites/
    SITE_ID = 1

    ##
    ## Social Authentication and Accounts
    ##

    # Configurations:
    # https://django-allauth.readthedocs.io/en/latest/configuration.html

    # Use custom user model that has email instead of username
    ACCOUNT_USER_MODEL_USERNAME_FIELD = None
    ACCOUNT_USER_MODEL_EMAIL_FIELD = "email"
    ACCOUNT_EMAIL_REQUIRED = True
    ACCOUNT_USERNAME_REQUIRED = False
    ACCOUNT_AUTHENTICATION_METHOD = "email"

    ACCOUNT_PRESERVE_USERNAME_CASING = False

    SOCIALACCOUNT_PROVIDERS = {
        "google": {"SCOPE": ["profile", "email"], "AUTH_PARAMS": {"access_type": "online"}}  # email is a requirement
    }

    LOGIN_REDIRECT_URL = "app"

    ##
    ## Email sender (configured in environment variables)
    ##

    # Using a paid SendGrid service account:
    # https://sendgrid.com/docs/for-developers/sending-email/django/
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
    EMAIL_HOST = os.environ.get("ANALITICO_EMAIL_HOST", "smtp.sendgrid.net")
    EMAIL_HOST_USER = os.environ.get("ANALITICO_EMAIL_HOST_USER", None)
    EMAIL_HOST_PASSWORD = os.environ.get("ANALITICO_EMAIL_HOST_PASSWORD", None)
    EMAIL_PORT = os.environ.get("ANALITICO_EMAIL_HOST_PORT", 587)
    EMAIL_USE_TLS = os.environ.get("ANALITICO_EMAIL_HOST_TLS", True)

    # Simple setup using a Gmail account (SMTP needs to be excplicitely authorized):
    # https://medium.com/@_christopher/how-to-send-emails-with-python-django-through-google-smtp-server-for-free-22ea6ea0fb8e
    # EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    # EMAIL_HOST = 'smtp.gmail.com'
    # EMAIL_USE_TLS = True
    # EMAIL_PORT = 587
    # EMAIL_HOST_USER = 'xxx@gmail.com'
    # EMAIL_HOST_PASSWORD = 'xxx'

    # Internationalization
    # https://docs.djangoproject.com/en/2.1/topics/i18n/

    LANGUAGE_CODE = "en-us"
    TIME_ZONE = "Europe/Rome"
    USE_I18N = True
    USE_L10N = True
    USE_TZ = True

    # Static files (CSS, JavaScript, Images)
    # https://docs.djangoproject.com/en/2.1/howto/static-files/

    STATIC_URL = "/static/"
    STATIC_ROOT = "static/"

    STATICFILES_DIRS = [
        # will also include static files generated for angular frontend app?
        # os.path.join(BASE_DIR, "static")
    ]

    ###
    ### REST Framework
    ###

    # TODO better mechanism for auth tokens
    # https://github.com/James1345/django-rest-knox

    APPEND_SLASH = False

    REST_FRAMEWORK = {
        # custom exception handler reports exception with specific formatting
        "EXCEPTION_HANDLER": "api.utilities.exception_to_response",
        # calls with ?page=x or over fixed number of items will be paged
        "DEFAULT_PAGINATION_CLASS": "api.pagination.AnaliticoPageNumberPagination",
        # if you set a page size here all list queries will be paged, even
        # when there are few items like in the case of workspaces or datasets
        # instead we changed the pager to enable paging on demand or automatically
        # enable it by default when the number of items exceed the max page size
        # so we can avoid slowing down the server with huge unpaged requests
        # "PAGE_SIZE": 100,
        "DEFAULT_PARSER_CLASSES": (
            #       'rest_framework_json_api.parsers.JSONParser',
            "rest_framework.parsers.JSONParser",
            "rest_framework.parsers.FormParser",
            "rest_framework.parsers.MultiPartParser",
        ),
        "DEFAULT_RENDERER_CLASSES": (
            "api.renderers.JSONRenderer",  # jsonapi but simplified
            # browsable API is somewhat useful as it makes it easy to post or update
            # from the browser. however it always take precedence over json unless
            # accept headers are forced and makes it harder to see what the API really returns
            # so for now let's disable it
            # "rest_framework.renderers.BrowsableAPIRenderer",
        ),
        "DEFAULT_METADATA_CLASS": "rest_framework_json_api.metadata.JSONAPIMetadata",
        "DEFAULT_FILTER_BACKENDS": (
            # Enforce strict validation on query parameters:
            # "rest_framework_json_api.filters.QueryParameterValidationFilter",
            "rest_framework_json_api.filters.OrderingFilter",
            "rest_framework_json_api.django_filters.DjangoFilterBackend",
            "rest_framework.filters.SearchFilter",
        ),
        "SEARCH_PARAM": "filter[search]",
        "TEST_REQUEST_RENDERER_CLASSES": (
            #       'rest_framework_json_api.renderers.JSONRenderer',
            #       'rest_framework.renderers.JSONRenderer',
            "rest_framework.renderers.MultiPartRenderer",
            "api.renderers.JSONRenderer",  # jsonapi but simplified
        ),
        "TEST_REQUEST_DEFAULT_FORMAT": "json",
        # APIs use Bearer tokens, app and site use sessions
        "DEFAULT_AUTHENTICATION_CLASSES": (
            "api.authentication.BearerAuthentication",
            "rest_framework.authentication.SessionAuthentication",
            "rest_framework.authentication.BasicAuthentication",
        ),
        # Use Django's standard `django.contrib.auth` permissions,
        # or allow read-only access for unauthenticated users.
        "DEFAULT_PERMISSION_CLASSES": [
            # 'rest_framework.authentication.BasicAuthentication',
            # 'rest_framework.authentication.SessionAuthentication'
        ],
    }

    # Django Swagger documentation settings
    # https://django-rest-swagger.readthedocs.io/en/latest/settings/
    SWAGGER_SETTINGS = {
        "SECURITY_DEFINITIONS": {
            "basic": {"description": "Authorize using credentials from analitico.ai", "type": "basic"},
            # Support authentication with API tokens
            "token": {
                "description": "Authorize using an 'Authorization: Bearer tok_xxx' header.",
                "type": "apiKey",
                "in": "header",
                "name": "Authorization",
            },
        }
    }

    ##
    ## Prometheus service used for metrics on kubernetes cluster
    ##

    PROMETHEUS_SERVICE_URL = "https://prometheus.cloud.analitico.ai/api/v1"

    ##
    ##  Elastic search used for cluster logs
    ##

    # kubernetes endpoint used for elastic search service
    ELASTIC_SEARCH_URL = "https://cloud.analitico.ai:6443/api/v1/namespaces/knative-monitoring/services/elasticsearch-logging/proxy/logstash-*/_search"

    # bearer token used to authenticate on elastic search service
    ELASTIC_SEARCH_API_TOKEN = os.environ.get("ANALITICO_ELASTIC_SEARCH_API_TOKEN", None)
    assert ELASTIC_SEARCH_API_TOKEN, "Did you forget to configure the env variable ANALITICO_ELASTIC_SEARCH_API_TOKEN?"

except KeyError as exc:
    detail = (
        "settings.py - Configuration error, did you forget to declare " + exc.args[0] + " as an environment variable?"
    )
    sys.stderr.write(detail)
    sys.exit(1)  # error
