from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Crea o actualiza el superusuario medico inicial del consultorio.'

    def handle(self, *args, **options):
        user_model = get_user_model()
        defaults = {
            'email': 'admin@consultorio.local',
            'full_name': 'Administrador del consultorio',
            'specialties': 'Medicina general',
            'professional_license': 'CED-0001',
            'office_name': 'Consultorio Agenda',
            'office_address': 'Direccion principal del consultorio',
            'profile_bio': 'Atencion medica general con seguimiento clinico y agenda en linea.',
            'phone': '0000000000',
            'role': user_model.Role.MEDICO,
            'is_staff': True,
            'is_superuser': True,
            'is_active': True,
            'email_verified': True,
        }
        user, created = user_model.objects.update_or_create(username='admin', defaults=defaults)
        user.set_password('Admin12345!')
        user.save()

        if created:
            self.stdout.write(self.style.SUCCESS('Superusuario medico creado con usuario admin.'))
        else:
            self.stdout.write(self.style.SUCCESS('Superusuario medico actualizado con usuario admin.'))
