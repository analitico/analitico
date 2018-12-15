
import api.urls

from django.contrib import admin
from django.urls import include, path
from django.views.generic import TemplateView
from django.utils.translation import gettext as _
from rest_framework.documentation import include_docs_urls

# urlpatterns list routes URLs to views:
# https://docs.djangoproject.com/en/2.1/topics/http/urls/

# API endpoints
urlpatterns = [
    path('api/v1/', include('api.urls'), name='api')
]

# API documentation
urlpatterns += [
    path('api/v1/docs/', include_docs_urls(title=_('Analitico API'), description=api.urls.description, patterns=urlpatterns))
    # https://www.django-rest-framework.org/topics/documenting-your-api/
    # https://www.django-rest-framework.org/api-guide/schemas/
]

# website and backoffice
urlpatterns += [
    path('', TemplateView.as_view(template_name='index.html'), name='index'),
    path('admin/', admin.site.urls, name='admin')
]
