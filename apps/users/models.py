from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    email = models.EmailField(unique=True)
    latitude = models.DecimalField(
        max_digits=10, 
        decimal_places=7, 
        null=True, 
        blank=True,
        help_text='Latitud de la ubicación del usuario'
    )
    longitude = models.DecimalField(
        max_digits=10, 
        decimal_places=7, 
        null=True, 
        blank=True,
        help_text='Longitud de la ubicación del usuario'
    )
    has_power = models.BooleanField(
        null=True, 
        blank=True,
        help_text='Indica si el usuario tiene luz actualmente'
    )
    last_power_update = models.DateTimeField(
        auto_now=True,
        help_text='Última vez que se actualizó el estado de luz'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'

    def __str__(self):
        return self.email
