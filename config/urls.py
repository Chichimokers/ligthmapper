"""
Main URL configuration for Light Mapper project.
"""

from django.contrib import admin
from django.urls import path, include, re_path
from django.http import JsonResponse
from django.views.static import serve
from django.conf import settings


def health_check(request):
    return JsonResponse({'status': 'ok', 'service': 'Light Mapper'})


def api_root(request):
    return JsonResponse({
        'service': 'Light Mapper API',
        'version': '1.0.0',
        'message': 'Sistema de monitoreo de electricidad',
        'endpoints': {
            'public': {
                'lights': '/api/v1/users/lights/',
            },
            'auth': {
                'google_login': '/api/v1/users/auth/google/',
                'refresh_token': '/api/v1/users/token/refresh/',
                'profile': '/api/v1/users/profile/',
            },
            'admin': {
                'lights': '/api/v1/users/admin/lights/',
            }
        }
    })


urlpatterns = [
    path('health/', health_check, name='health-check'),
    path('api/', api_root, name='api-root'),
    path('api/v1/', api_root, name='api-root-v1'),
    path('api/v1/users/', include('apps.users.urls')),
]

urlpatterns += [
    re_path(r'^api/v1/static/(?P<path>.*)$', serve, {'document_root': settings.STATIC_ROOT}),
    re_path(r'^api/v1/media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
]

admin.site.site_header = 'Light Mapper Admin'
admin.site.site_title = 'Light Mapper'
admin.site.index_title = 'Panel de Administración'
