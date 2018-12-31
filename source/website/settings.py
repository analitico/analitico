"""
Django settings for analitico.ai

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

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
# Project is always started with currenct directory in /analitico/source/
BASE_DIR = os.path.dirname(os.path.abspath(__file__))


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/2.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = '111&xe5+tyf29&&%t!jk9-v)!v07gc%0ha4*4#8e+rfd@7i80#'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

ALLOWED_HOSTS = [
    '127.0.0.1',
    'localhost',

    'analitico.ai',         # main domain
    '.analitico.ai',        # any subdomain

    '138.201.196.111',      # s1.analitico.ai
    '78.46.46.165',         # s2.analitico.ai
    '159.69.242.143'        # s5.analitico.ai
]

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
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles'
]

MIDDLEWARE = [
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

# Database
# https://docs.djangoproject.com/en/2.1/ref/settings/#databases
# https://dev.mysql.com/doc/connector-python/en/connector-python-django-backend.html

DATABASES = {
    'default': {
        'ENGINE': 'mysql.connector.django',
        'NAME': 'ai',
        'USER': 'analitico',
        'PASSWORD': '4eRwg67hj',
        'HOST': 's1.analitico.ai',
        'PORT': '3306',
 
#       'PASSWORD': 'xxx',
#       'HOST': '127.0.0.1',
    }
}

if 'test' in sys.argv or 'test_coverage' in sys.argv: # Covers regular testing and django-coverage
    DATABASES['default']['ENGINE'] = 'django.db.backends.sqlite3'

# TODO use environment variable or external file to hide password:
#   'OPTIONS': {
#     'read_default_file': '/etc/mysql/my.cnf',
#   }


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

###
### REST Framework
###

# TODO better mechanism for auth tokens
# https://github.com/James1345/django-rest-knox

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
        'api.renderers.JSONRenderer',
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
#           'rest_framework_json_api.renderers.JSONRenderer',
            'rest_framework.renderers.JSONRenderer',
        ),
    
    'TEST_REQUEST_DEFAULT_FORMAT': 
        'vnd.api+json',

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