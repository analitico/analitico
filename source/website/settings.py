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
import sentry_sdk
import raven
import sys

from rest_framework.exceptions import APIException

try:

    # SECURITY WARNING: don't run with debug turned on in production!
    DEBUG = os.environ.get('ANALITICO_DEBUG', 'False') == 'True'

    # Build paths inside the project like this: os.path.join(BASE_DIR, ...)
    # Project is always started with currenct directory in /analitico/source/
    # base directory is the one where manage.py is also found
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    # SECURITY WARNING: keep the secret key used in production secret!
    SECRET_KEY = os.environ['ANALITICO_SECRET_KEY']

    # MySQL database
    DATABASES = {
        'default': {
            'ENGINE': 'mysql.connector.django',
            'PORT': '3306',
            'NAME': os.environ.get('ANALITICO_MYSQL_NAME', 'analitico'),
            'HOST': os.environ['ANALITICO_MYSQL_HOST'],
            'USER': os.environ['ANALITICO_MYSQL_USER'],
            'PASSWORD': os.environ['ANALITICO_MYSQL_PASSWORD']
        }
    }

    # Covers pytest, regular testing and django-coverage
    if sys.argv[0].endswith('pytest.py') or ('test' in sys.argv) or ('test_coverage' in sys.argv): 
        DATABASES['default']['ENGINE'] = 'django.db.backends.sqlite3'


    # We are keeping file storage cloud independent so that we can use whichever
    # cloud makes the most sense and also give customers an option to bring their own
    # cloud storage configuration. Each workspace can have its own configuration which
    # is used for all assets belonging to the workspace and its children. If the workspace
    # does not have a storage configured, the following configuration is used as a default.

    ANALITICO_STORAGE = {
        "driver": "google-storage",
        "container": "data.analitico.ai",
        "basepath": "",
        "credentials": {
            "key": os.environ['ANALITICO_GCS_KEY'],
            "secret": os.environ['ANALITICO_GCS_SECRET'],
            "project": os.environ['ANALITICO_GCS_PROJECT']
        }
    }


    # Special storage for regular testing and django-coverage
    if 'test' in sys.argv or 'test_coverage' in sys.argv: 
        ANALITICO_STORAGE['container'] = 'test.analitico.ai'


    # List of domains serving the app, can be customized as needed
    ALLOWED_HOSTS = [
        '127.0.0.1',
        'localhost',

        'analitico.ai',         # main domain
        '.analitico.ai',        # any subdomain

        '138.201.196.111',      # s1.analitico.ai
        '78.46.46.165',         # s2.analitico.ai
        '159.69.242.143'        # s5.analitico.ai
    ]

    # Allow CORS requests from any subdomain of analitico.ai
    CSRF_COOKIE_DOMAIN = 'analitico.ai'

    # Allow preflight OPTION request from these origins
    CORS_ORIGIN_WHITELIST = (
        'app.analitico.ai',
        'app-staging.analitico.ai',
        'app-local.analitico.ai',
        'lab.analitico.ai',
        'lab-staging.analitico.ai'
    )

    # Allow passing cookies into CORS request (e.g. session cookie)
    CORS_ALLOW_CREDENTIALS = True

    # set the session cookie for all subdomains of analitico.ai
    SESSION_COOKIE_DOMAIN = 'analitico.ai'

    # Application definition
    INSTALLED_APPS = [
        'api',
        's24',
        'website',

        'gunicorn',
        'rest_framework',    
        'drf_yasg', # openapi schema generator
        'raven.contrib.django.raven_compat',

        'django.contrib.admin',
        'django.contrib.auth',
        'django.contrib.contenttypes',
        'django.contrib.messages',
        'django.contrib.sessions',
        'django.contrib.staticfiles',
        'django.contrib.sites',

        'allauth',
        'allauth.account',
        'allauth.socialaccount',
        # include the providers you want to enable...
        # https://django-allauth.readthedocs.io/en/latest/installation.html
        'allauth.socialaccount.providers.google',
        'allauth.socialaccount.providers.github',
        'allauth.socialaccount.providers.windowslive',
        'corsheaders'
    ]

    MIDDLEWARE = [
        'corsheaders.middleware.CorsMiddleware',
        'django.middleware.security.SecurityMiddleware',
        'django.contrib.sessions.middleware.SessionMiddleware',
        'django.middleware.common.CommonMiddleware',
        'django.middleware.csrf.CsrfViewMiddleware',
        'django.contrib.auth.middleware.AuthenticationMiddleware',
        'django.contrib.messages.middleware.MessageMiddleware',
        'django.middleware.clickjacking.XFrameOptionsMiddleware',
    ]

    ROOT_URLCONF = 'website.urls'

    TEMPLATES = [
        {
            'BACKEND': 'django.template.backends.django.DjangoTemplates',
            'DIRS': [],
            'APP_DIRS': True,
            'OPTIONS': {
                'context_processors': [
                    'django.template.context_processors.debug',
                    'django.template.context_processors.request',
                    'django.contrib.auth.context_processors.auth',
                    'django.contrib.messages.context_processors.messages',
                ],
            },
        },
    ]

    WSGI_APPLICATION = 'website.wsgi.application'


    # User substitution
    # https://docs.djangoproject.com/en/1.11/topics/auth/customizing/#auth-custom-user
    AUTH_USER_MODEL = 'api.User'

    # Password validation
    # https://docs.djangoproject.com/en/2.1/ref/settings/#auth-password-validators
    AUTH_PASSWORD_VALIDATORS = [
        { 'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator' },
        { 'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator' },
        { 'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator' },
        { 'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator' }
    ]

    AUTHENTICATION_BACKENDS = (
        # Needed to login by username in Django admin, regardless of `allauth`
        'django.contrib.auth.backends.ModelBackend',

        # `allauth` specific authentication methods, such as login by e-mail
        'allauth.account.auth_backends.AuthenticationBackend',
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
    ACCOUNT_USER_MODEL_EMAIL_FIELD='email'
    ACCOUNT_EMAIL_REQUIRED = True
    ACCOUNT_USERNAME_REQUIRED = False
    ACCOUNT_AUTHENTICATION_METHOD = 'email'
    
    ACCOUNT_PRESERVE_USERNAME_CASING=False

    SOCIALACCOUNT_PROVIDERS = {
        'google': {
            'SCOPE': [
                'profile',
                'email', # email is a requirement
            ],
            'AUTH_PARAMS': {
                'access_type': 'online',
            }
        }
    }

    LOGIN_REDIRECT_URL = 'lab'

    ##
    ## Email sender (configured in environment variables)
    ##

    # Using a paid SendGrid service account:
    # https://sendgrid.com/docs/for-developers/sending-email/django/
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_HOST = os.environ.get('ANALITICO_EMAIL_HOST', 'smtp.sendgrid.net')
    EMAIL_HOST_USER = os.environ.get('ANALITICO_EMAIL_HOST_USER', None)
    EMAIL_HOST_PASSWORD = os.environ.get('ANALITICO_EMAIL_HOST_PASSWORD', None)
    EMAIL_PORT = os.environ.get('ANALITICO_EMAIL_HOST_PORT', 587)
    EMAIL_USE_TLS = os.environ.get('ANALITICO_EMAIL_HOST_TLS', True)

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

    LANGUAGE_CODE = 'en-us'
    TIME_ZONE = 'Europe/Rome'
    USE_I18N = True
    USE_L10N = True
    USE_TZ = True


    # Static files (CSS, JavaScript, Images)
    # https://docs.djangoproject.com/en/2.1/howto/static-files/

    STATIC_URL = '/static/'
    STATIC_ROOT = "static/"

    STATICFILES_DIRS = [
        # will also include static files generated for angular frontend app?
        # os.path.join(BASE_DIR, "../app/dist/")
    ]

    ###
    ### REST Framework
    ###

    # TODO better mechanism for auth tokens
    # https://github.com/James1345/django-rest-knox

    APPEND_SLASH = False

    REST_FRAMEWORK = {

        # custom exception handler reports exception with specific formatting
        'EXCEPTION_HANDLER': 
            'api.utilities.api_exception_handler',
    #       'rest_framework_json_api.exceptions.exception_handler',

        'DEFAULT_PAGINATION_CLASS':
            'rest_framework_json_api.pagination.JsonApiPageNumberPagination',

        'DEFAULT_PARSER_CLASSES': (
    #       'rest_framework_json_api.parsers.JSONParser',
            'rest_framework.parsers.JSONParser',
            'rest_framework.parsers.FormParser',
            'rest_framework.parsers.MultiPartParser'
        ),

        'DEFAULT_RENDERER_CLASSES': (
    #       'rest_framework_json_api.renderers.JSONRenderer',
    #       'rest_framework.renderers.JSONRenderer',
            'api.renderers.JSONRenderer', # jsonapi but simplified
            'rest_framework.renderers.BrowsableAPIRenderer',
        ),

        'DEFAULT_METADATA_CLASS': 
            'rest_framework_json_api.metadata.JSONAPIMetadata',
        
        'DEFAULT_FILTER_BACKENDS': (
            'rest_framework_json_api.filters.QueryParameterValidationFilter',
            'rest_framework_json_api.filters.OrderingFilter',
            'rest_framework_json_api.django_filters.DjangoFilterBackend',
            'rest_framework.filters.SearchFilter',
        ),
        
        'SEARCH_PARAM': 
            'filter[search]',
        
        'TEST_REQUEST_RENDERER_CLASSES': (
    #       'rest_framework_json_api.renderers.JSONRenderer',
    #       'rest_framework.renderers.JSONRenderer',
            'rest_framework.renderers.MultiPartRenderer',
            'api.renderers.JSONRenderer', # jsonapi but simplified
            ),
        
        'TEST_REQUEST_DEFAULT_FORMAT': 
            'json',

        'DEFAULT_AUTHENTICATION_CLASSES': (
            'api.authentication.BearerAuthentication',
            'rest_framework.authentication.SessionAuthentication',
            'rest_framework.authentication.BasicAuthentication',
        ),

        # Use Django's standard `django.contrib.auth` permissions,
        # or allow read-only access for unauthenticated users.
        'DEFAULT_PERMISSION_CLASSES': [
            # 'rest_framework.authentication.BasicAuthentication',
            # 'rest_framework.authentication.SessionAuthentication'
        ]
    }

    # Django Swagger documentation settings
    # https://django-rest-swagger.readthedocs.io/en/latest/settings/
    SWAGGER_SETTINGS = {
        'SECURITY_DEFINITIONS': {
            'basic': {
                'description': 'Authorize using credentials from analitico.ai',
                'type': 'basic'
            },
            # Support authentication with API tokens
            'token': {
                'description': "Authorize using an 'Authorization: Bearer tok_xxx' header.",
                'type': 'apiKey',
                'in': 'header',
                'name': 'Authorization'
            }
        }
    }

    ###
    ### Logging
    ###

    # Examples of logging configuration:
    # https://lincolnloop.com/blog/django-logging-right-way/

    # Sentry/Django documentation
    # https://docs.sentry.io/clients/python/integrations/django/

    # See logs here:
    # https://sentry.io/analiticoai/python/

    sentry_sdk.init("https://3cc8a3cf05e140a9bef3946e24756dc5@sentry.io/1336917")

    RAVEN_CONFIG = {
        'dsn': 'https://3cc8a3cf05e140a9bef3946e24756dc5:30ab9adb8199489a962d94566cd746bc@sentry.io/1336917',
        # If you are using git, you can also automatically configure the
        # release based on the git info.
    #   'release': raven.fetch_git_sha(os.path.abspath(os.getcwd())),
    #   'release': raven.fetch_git_sha(os.path.abspath(os.pardir)),
        'release': 'v0.11',
    }

    LOGLEVEL = os.environ.get('LOGLEVEL', 'info').upper()

    LOGGING_CONFIG = None
    logging.config.dictConfig({
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'console': {
                # exact format is not important, this is the minimum information
                'format': '%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
            },
        },
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
                'formatter': 'console',
            },
            # Add Handler for Sentry for `warning` and above
            'sentry': {
                'level': 'WARNING',
                'class': 'raven.contrib.django.raven_compat.handlers.SentryHandler',
            },
        },
        'loggers': {
            # root logger
            '': {
                'level': 'WARNING',
                'handlers': ['console'],
                #'handlers': ['console', 'sentry'],
            },
            'analitico': {
                'level': LOGLEVEL,
                'handlers': ['console'],
                # 'handlers': ['console', 'sentry'],
                # required to avoid double logging with root logger
                'propagate': False,
            },
        },
    })


except KeyError as exc:
    detail = 'settings.py - Configuration error, did you forget to declare ' + exc.args[0] + ' as an environment variable?'
    sys.stderr.write(detail)
    sys.exit(1) # error
