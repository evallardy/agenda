from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import EmailLog, User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    ordering = ('email',)
    list_display = ('email', 'full_name', 'specialties', 'professional_license', 'phone', 'role', 'email_verified', 'is_staff')
    list_filter = ('role', 'email_verified', 'is_staff', 'is_superuser', 'is_active')
    search_fields = ('email', 'full_name', 'specialties', 'professional_license', 'phone')
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        (
            'Informacion personal',
            {'fields': ('full_name', 'specialties', 'professional_license', 'phone', 'role', 'email_verified')},
        ),
        ('Perfil medico', {'fields': ('office_name', 'office_address', 'profile_bio', 'photo')}),
        ('Permisos', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Fechas importantes', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (
            None,
            {
                'classes': ('wide',),
                'fields': (
                    'email',
                    'full_name',
                    'specialties',
                    'professional_license',
                    'office_name',
                    'office_address',
                    'profile_bio',
                    'photo',
                    'phone',
                    'role',
                    'email_verified',
                    'password1',
                    'password2',
                ),
            },
        ),
    )


@admin.register(EmailLog)
class EmailLogAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'recipient', 'subject', 'context_type', 'status', 'triggered_by')
    list_filter = ('status', 'context_type', 'created_at')
    search_fields = ('recipient', 'subject', 'from_email', 'error_message')
    readonly_fields = ('recipient', 'subject', 'from_email', 'body', 'context_type', 'status', 'error_message', 'triggered_by', 'created_at')
