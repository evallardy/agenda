from datetime import time, timedelta

from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from citas.models import Appointment
from users.models import User


@override_settings(ALLOWED_HOSTS=['testserver', 'localhost', '127.0.0.1'])
class DashboardQuickConsultationTests(TestCase):
    def setUp(self):
        self.doctor = User.objects.create_user(
            email='doctor.panel@example.com',
            password='Admin12345!',
            full_name='Doctor Panel',
            phone='5551111111',
            role=User.Role.MEDICO,
            is_active=True,
            email_verified=True,
            is_staff=True,
        )
        self.patient = User.objects.create_user(
            email='paciente.panel@example.com',
            password='Paciente123!',
            full_name='Paciente Panel',
            phone='5552222222',
            role=User.Role.PACIENTE,
            is_active=True,
            email_verified=True,
        )

    def test_doctor_dashboard_shows_quick_consultation_button(self):
        appointment = Appointment.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            date=timezone.localdate() + timedelta(days=1),
            start_time=time(10, 0),
            end_time=time(10, 30),
            status=Appointment.Status.CONFIRMADA,
            reason='Consulta general',
        )
        self.client.force_login(self.doctor)

        response = self.client.get(reverse('core:dashboard'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Nueva consulta')
        self.assertContains(response, reverse('clinico:record-update', args=[appointment.pk]))

    def test_doctor_dashboard_shows_calendar_link_when_no_available_appointments(self):
        self.client.force_login(self.doctor)

        response = self.client.get(reverse('core:dashboard'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Buscar cita para consulta')
        self.assertNotContains(response, 'Nueva consulta')

    def test_doctor_dashboard_today_appointments_only_show_confirmed(self):
        now = timezone.localtime()
        future_start = (now + timedelta(minutes=60)).time().replace(microsecond=0)
        future_end = (now + timedelta(minutes=90)).time().replace(microsecond=0)
        confirmed_patient = User.objects.create_user(
            email='confirmado.panel@example.com',
            password='Paciente123!',
            full_name='Paciente Confirmado',
            phone='5553333333',
            role=User.Role.PACIENTE,
            is_active=True,
            email_verified=True,
        )
        pending_patient = User.objects.create_user(
            email='pendiente.panel@example.com',
            password='Paciente123!',
            full_name='Paciente Pendiente',
            phone='5554444444',
            role=User.Role.PACIENTE,
            is_active=True,
            email_verified=True,
        )
        Appointment.objects.create(
            patient=confirmed_patient,
            doctor=self.doctor,
            date=timezone.localdate(),
            start_time=future_start,
            end_time=future_end,
            status=Appointment.Status.CONFIRMADA,
            reason='Cita confirmada',
        )
        Appointment.objects.create(
            patient=pending_patient,
            doctor=self.doctor,
            date=timezone.localdate(),
            start_time=time(10, 0),
            end_time=time(10, 30),
            status=Appointment.Status.PENDIENTE,
            reason='Cita pendiente',
        )
        self.client.force_login(self.doctor)

        response = self.client.get(reverse('core:dashboard'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Paciente Confirmado')
        self.assertNotContains(response, 'Paciente Pendiente')
        self.assertContains(response, 'Cancelar cita')

    def test_doctor_dashboard_hides_cancel_action_after_start_time(self):
        now = timezone.localtime()
        Appointment.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            date=now.date(),
            start_time=(now - timedelta(minutes=5)).time().replace(microsecond=0),
            end_time=(now + timedelta(minutes=25)).time().replace(microsecond=0),
            status=Appointment.Status.CONFIRMADA,
            reason='Cita en curso',
        )
        self.client.force_login(self.doctor)

        response = self.client.get(reverse('core:dashboard'))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Cancelar cita')
        self.assertContains(response, 'En curso, ya no cancelable')