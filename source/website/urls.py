
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

    path('api/v1/', include('api.urls')),
    #path('api/v1/', include(api_router.urls)),

    path('polls/', include('polls.urls')),
    path('admin/', admin.site.urls),

    # home page served from template, named for reverse lookup
    path('', IndexView.as_view(), name='index')
]

# service used to retrieve tokens
from rest_framework.authtoken import views
urlpatterns += [
    url(r'^api-token-auth/', views.obtain_auth_token)
]
