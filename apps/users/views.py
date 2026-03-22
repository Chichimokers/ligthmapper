from rest_framework import status, generics
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
from django.conf import settings
from google.oauth2 import id_token
from google.auth.transport import requests

from .serializers import (
    UserProfileSerializer,
    LightStatusPublicSerializer,
    LightStatusAdminSerializer,
    GoogleAuthSerializer
)

User = get_user_model()


def verify_google_token(token):
    try:
        if not settings.GOOGLE_CLIENT_ID:
            return None
        idinfo = id_token.verify_oauth2_token(
            token,
            requests.Request(),
            settings.GOOGLE_CLIENT_ID
        )
        if idinfo['aud'] != settings.GOOGLE_CLIENT_ID:
            return None
        return idinfo
    except Exception:
        return None


@api_view(['POST'])
@permission_classes([AllowAny])
def google_auth(request):
    serializer = GoogleAuthSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    token = serializer.validated_data['id_token']
    google_user = verify_google_token(token)
    
    if not google_user:
        return Response(
            {'error': 'Invalid Google token'},
            status=status.HTTP_401_UNAUTHORIZED
        )
    
    email = google_user.get('email')
    user, created = User.objects.get_or_create(
        email=email,
        defaults={
            'username': email.split('@')[0],
            'first_name': google_user.get('given_name', ''),
            'last_name': google_user.get('family_name', ''),
        }
    )
    
    if created:
        user.set_unusable_password()
        user.save()
    
    refresh = RefreshToken.for_user(user)
    
    return Response({
        'user': UserProfileSerializer(user).data,
        'tokens': {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }
    }, status=status.HTTP_200_OK if not created else status.HTTP_201_CREATED)


@api_view(['GET', 'PUT'])
@permission_classes([IsAuthenticated])
def profile(request):
    if request.method == 'GET':
        serializer = UserProfileSerializer(request.user)
        return Response(serializer.data)
    
    serializer = UserProfileSerializer(
        request.user,
        data=request.data,
        partial=True
    )
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def lights_list(request):
    users = User.objects.exclude(
        latitude__isnull=True,
        longitude__isnull=True
    ).exclude(
        latitude=0,
        longitude=0
    )
    serializer = LightStatusPublicSerializer(users, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAdminUser])
def admin_lights_list(request):
    users = User.objects.exclude(
        latitude__isnull=True,
        longitude__isnull=True
    ).exclude(
        latitude=0,
        longitude=0
    )
    serializer = LightStatusAdminSerializer(users, many=True)
    return Response(serializer.data)
