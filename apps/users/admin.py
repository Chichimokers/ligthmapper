from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['email', 'username', 'latitude', 'longitude', 'has_power', 'last_power_update', 'is_staff']
    list_filter = ['has_power', 'is_staff', 'is_active']
    search_fields = ['email', 'username']
    ordering = ['-created_at']
    
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Ubicación y Luz', {'fields': ('latitude', 'longitude', 'has_power', 'last_power_update')}),
    )
    readonly_fields = ['last_power_update', 'created_at', 'updated_at']
