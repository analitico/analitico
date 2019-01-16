
from django.contrib import admin
from django.urls import include, path
from django.views.generic import TemplateView
from django.utils.translation import gettext as _
from django.conf.urls import url
from django.conf import settings
from django.conf.urls.static import static

from rest_framework import permissions

from drf_yasg.views import get_schema_view
from drf_yasg import openapi

import api.urls

# API documentation
# https://github.com/axnsan12/drf-yasg/
schema_view = get_schema_view(
   openapi.Info(
      title='Analitico API',
      default_version='v1',
      description=api.urls.description,
      terms_of_service="https://analitico.ai/",
      contact=openapi.Contact(email="support@analitico.ai"),
      license=openapi.License(name="GPLv3", url='https://www.gnu.org/licenses/quick-guide-gplv3.en.html'),
   ),
   validators=['flex', 'ssv'],
   public=True,
   permission_classes=(permissions.AllowAny,),
)

# urlpatterns list routes URLs to views:
# https://docs.djangoproject.com/en/2.1/topics/http/urls/
urlpatterns = [
   # static home page from template
   path('', TemplateView.as_view(template_name='index.html'), name='index'),   

   # angular frontend application (any path under /app)
   # url(r'^app.*', TemplateView.as_view(template_name="app.html"), name="app"),

   # django admin site
   path('admin/', admin.site.urls, name='admin'),

   # REST APIs
   path('api/v1/', include('api.urls'), name='api'),

   # APIs documentation and swagger manifest
   url(r'^api/v1/docs', schema_view.with_ui('swagger', cache_timeout=0), name='api-docs'),
   url(r'^swagger(?P<format>\.json|\.yaml)$', schema_view.without_ui(cache_timeout=0), name='schema-json'),
   url(r'^swagger/$', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
   url(r'^redoc/$', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),

] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)


