from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from . import views

urlpatterns = [
    path('auth/google/', views.google_auth, name='google-auth'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
    path('profile/', views.profile, name='profile'),
    path('lights/', views.lights_list, name='lights-list'),
    path('admin/lights/', views.admin_lights_list, name='admin-lights'),
]
