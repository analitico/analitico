
# The `urlpatterns` list routes URLs to views. For more information please see:
# https://docs.djangoproject.com/en/2.1/topics/http/urls/

from django.contrib import admin
from django.urls import include, path
from django.conf.urls import url, include
from django.views.generic import TemplateView

#from api.urls import api_router

# serves template for home page
class IndexView(TemplateView):
    template_name = 'index.html'

urlpatterns = [
    # home page served from template, named for reverse lookup
    path('', IndexView.as_view(), name='index'),

    # API endpoints
    path('api/v1/', include('api.urls'), name='api'),

    # backoffice
    path('admin/', admin.site.urls, name='admin'),
]

# add service used to retrieve tokens
from rest_framework.authtoken import views
urlpatterns += [
    url(r'^api-token-auth/', views.obtain_auth_token)
]

# API documentation site
# https://www.django-rest-framework.org/topics/documenting-your-api/
# https://www.django-rest-framework.org/api-guide/schemas/
from rest_framework.documentation import include_docs_urls
urlpatterns += [
    path('api/v1/docs/', include_docs_urls(title='Analitico API'), name='docs')
]