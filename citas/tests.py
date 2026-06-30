from datetime import time, timedelta

from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from users.models import EmailLog, User

from .models import Appointment, BusinessHours
from .services import build_slots, get_available_slots, get_month_calendar, get_schedule_settings


@override_settings(
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    ALLOWED_HOSTS=['testserver', 'localhost', '127.0.0.1'],
)
class SchedulingTests(TestCase):
    def setUp(self):
        self.doctor = User.objects.create_user(
            email='doctor@example.com',
            password='Admin12345!',
            full_name='Doctor Demo',
            phone='5550000000',
            role=User.Role.MEDICO,
            is_active=True,
            email_verified=True,
            is_staff=True,
        )
        self.patient = User.objects.create_user(
            email='paciente@example.com',
            password='Paciente123!',
            full_name='Paciente Demo',
            phone='5551111111',
            role=User.Role.PACIENTE,
            is_active=True,
            email_verified=True,
        )
        self.settings = get_schedule_settings(self.doctor)
        self.settings.consultation_duration = 30
        self.settings.save(update_fields=['consultation_duration'])

    def configure_day(self, appointment_date, start_hour=9, end_hour=11):
        business_hours, _ = BusinessHours.objects.get_or_create(
            settings=self.settings,
            weekday=appointment_date.weekday(),
            defaults={
                'start_time': time(start_hour, 0),
                'end_time': time(end_hour, 0),
                'active': True,
            },
        )
        business_hours.start_time = time(start_hour, 0)
        business_hours.end_time = time(end_hour, 0)
        business_hours.active = True
        business_hours.save(update_fields=['start_time', 'end_time', 'active'])

    def test_build_slots_returns_exact_blocks(self):
        slots = build_slots(time(9, 0), time(11, 0), 30)

        self.assertEqual(len(slots), 4)
        self.assertEqual(slots[0], (time(9, 0), time(9, 30)))
        self.assertEqual(slots[-1], (time(10, 30), time(11, 0)))

    def test_get_available_slots_excludes_taken_active_appointments(self):
        appointment_date = timezone.localdate() + timedelta(days=1)
        self.configure_day(appointment_date)
        Appointment.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            date=appointment_date,
            start_time=time(9, 30),
            end_time=time(10, 0),
            status=Appointment.Status.CONFIRMADA,
            reason='Consulta previa',
        )

        available_slots = get_available_slots(self.doctor, appointment_date)

        self.assertIn((time(9, 0), time(9, 30)), available_slots)
        self.assertNotIn((time(9, 30), time(10, 0)), available_slots)

    def test_patient_cannot_create_second_active_appointment(self):
        appointment_date = timezone.localdate() + timedelta(days=1)
        self.configure_day(appointment_date)
        Appointment.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            date=appointment_date,
            start_time=time(9, 0),
            end_time=time(9, 30),
            status=Appointment.Status.PENDIENTE,
            reason='Primera cita',
        )

        self.client.force_login(self.patient)
        response = self.client.post(
            reverse('citas:patient-create'),
            {
                'appointment_date': appointment_date.isoformat(),
                'start_time': '09:30',
                'reason': 'Segunda cita',
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Appointment.objects.filter(patient=self.patient).count(), 1)

    def test_doctor_can_confirm_and_cancel_appointment(self):
        appointment_date = timezone.localdate() + timedelta(days=1)
        appointment = Appointment.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            date=appointment_date,
            start_time=time(9, 0),
            end_time=time(9, 30),
            status=Appointment.Status.PENDIENTE,
            reason='Revision',
        )
        self.client.force_login(self.doctor)

        confirm_response = self.client.post(
            reverse('citas:doctor-decision', args=[appointment.pk]),
            {'action': 'confirm'},
            follow=True,
        )
        self.assertEqual(confirm_response.status_code, 200)
        self.assertRedirects(confirm_response, reverse('core:dashboard'))
        appointment.refresh_from_db()
        self.assertEqual(appointment.status, Appointment.Status.CONFIRMADA)

        cancel_response = self.client.post(
            reverse('citas:doctor-decision', args=[appointment.pk]),
            {'action': 'cancel', 'cancellation_reason': 'Se presento una urgencia en consultorio.'},
            follow=True,
        )
        self.assertEqual(cancel_response.status_code, 200)
        self.assertRedirects(cancel_response, reverse('core:dashboard'))
        appointment.refresh_from_db()
        self.assertEqual(appointment.status, Appointment.Status.CANCELADA_MEDICO)
        self.assertEqual(appointment.doctor_cancellation_reason, 'Se presento una urgencia en consultorio.')
        self.assertEqual(len(mail.outbox), 2)
        self.assertIn('Se presento una urgencia en consultorio.', mail.outbox[-1].body)
        self.assertEqual(
            EmailLog.objects.filter(
                recipient=self.patient.email,
                context_type='appointment_patient_email',
                status='sent',
            ).count(),
            2,
        )

    def test_doctor_cannot_cancel_without_reason(self):
        appointment_date = timezone.localdate() + timedelta(days=1)
        appointment = Appointment.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            date=appointment_date,
            start_time=time(9, 0),
            end_time=time(9, 30),
            status=Appointment.Status.PENDIENTE,
            reason='Revision',
        )
        self.client.force_login(self.doctor)

        response = self.client.post(
            reverse('citas:doctor-decision', args=[appointment.pk]),
            {'action': 'cancel', 'cancellation_reason': ''},
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertRedirects(response, reverse('citas:doctor-review', args=[appointment.pk]))
        appointment.refresh_from_db()
        self.assertEqual(appointment.status, Appointment.Status.PENDIENTE)
        self.assertContains(response, 'Debes indicar la explicacion de la cancelacion.')

    def test_doctor_cannot_cancel_after_start_time(self):
        now = timezone.localtime()
        appointment = Appointment.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            date=now.date(),
            start_time=(now - timedelta(minutes=5)).time().replace(microsecond=0),
            end_time=(now + timedelta(minutes=25)).time().replace(microsecond=0),
            status=Appointment.Status.CONFIRMADA,
            reason='Revision iniciada',
        )
        self.client.force_login(self.doctor)

        response = self.client.post(
            reverse('citas:doctor-decision', args=[appointment.pk]),
            {'action': 'cancel', 'cancellation_reason': 'Ya no podre atender.'},
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertRedirects(response, reverse('citas:doctor-review', args=[appointment.pk]))
        appointment.refresh_from_db()
        self.assertEqual(appointment.status, Appointment.Status.CONFIRMADA)
        self.assertContains(response, 'La cita ya no se puede cancelar porque el horario ya comenzo.')

    def test_patient_cannot_cancel_after_start_time(self):
        now = timezone.localtime()
        appointment = Appointment.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            date=now.date(),
            start_time=(now - timedelta(minutes=5)).time().replace(microsecond=0),
            end_time=(now + timedelta(minutes=25)).time().replace(microsecond=0),
            status=Appointment.Status.CONFIRMADA,
            reason='Revision iniciada',
        )
        self.client.force_login(self.patient)

        response = self.client.post(reverse('citas:patient-cancel'), follow=True)

        self.assertEqual(response.status_code, 200)
        appointment.refresh_from_db()
        self.assertEqual(appointment.status, Appointment.Status.CONFIRMADA)
        self.assertContains(response, 'La cita ya no se puede cancelar porque el horario ya comenzo.')

    def test_patient_next_appointment_shows_in_progress_message(self):
        now = timezone.localtime()
        Appointment.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            date=now.date(),
            start_time=(now - timedelta(minutes=5)).time().replace(microsecond=0),
            end_time=(now + timedelta(minutes=25)).time().replace(microsecond=0),
            status=Appointment.Status.CONFIRMADA,
            reason='Revision iniciada',
        )
        self.client.force_login(self.patient)

        response = self.client.get(reverse('citas:patient-next'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Tu cita ya esta en curso.')
        self.assertContains(response, 'Ya no se puede cancelar')

    def test_doctor_pending_list_supports_search_and_date_filters(self):
        appointment_date = timezone.localdate() + timedelta(days=1)
        other_date = appointment_date + timedelta(days=1)
        first_patient = User.objects.create_user(
            email='ana@example.com',
            password='Paciente123!',
            full_name='Ana Perez',
            phone='5554444444',
            role=User.Role.PACIENTE,
            is_active=True,
            email_verified=True,
        )
        second_patient = User.objects.create_user(
            email='bruno@example.com',
            password='Paciente123!',
            full_name='Bruno Diaz',
            phone='5555555555',
            role=User.Role.PACIENTE,
            is_active=True,
            email_verified=True,
        )
        first_appointment = Appointment.objects.create(
            patient=first_patient,
            doctor=self.doctor,
            date=appointment_date,
            start_time=time(9, 0),
            end_time=time(9, 30),
            status=Appointment.Status.PENDIENTE,
            reason='Revision anual',
        )
        Appointment.objects.create(
            patient=second_patient,
            doctor=self.doctor,
            date=other_date,
            start_time=time(10, 0),
            end_time=time(10, 30),
            status=Appointment.Status.PENDIENTE,
            reason='Dolor lumbar',
        )

        self.client.force_login(self.doctor)
        response = self.client.get(reverse('citas:doctor-pending'), {'q': 'Ana', 'date': appointment_date.isoformat()})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context['appointments']), [first_appointment])
        self.assertContains(response, 'Ver detalle')

    def test_pending_review_shows_confirm_and_reject_actions(self):
        appointment_date = timezone.localdate() + timedelta(days=1)
        appointment = Appointment.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            date=appointment_date,
            start_time=time(9, 0),
            end_time=time(9, 30),
            status=Appointment.Status.PENDIENTE,
            reason='Solicitud pendiente',
        )
        self.client.force_login(self.doctor)

        response = self.client.get(reverse('citas:doctor-review', args=[appointment.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Confirmar cita')
        self.assertContains(response, 'Rechazar cita')
        self.assertNotContains(response, 'Confirmar cancelacion')

    def test_confirmed_review_shows_cancel_action_without_confirm_button(self):
        appointment_date = timezone.localdate() + timedelta(days=1)
        appointment = Appointment.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            date=appointment_date,
            start_time=time(9, 0),
            end_time=time(9, 30),
            status=Appointment.Status.CONFIRMADA,
            reason='Revision confirmada',
        )
        self.client.force_login(self.doctor)

        response = self.client.get(reverse('citas:doctor-review', args=[appointment.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Cancelar cita')
        self.assertNotContains(response, 'Confirmar cita')

    def test_confirmed_review_hides_cancel_action_after_start_time(self):
        now = timezone.localtime()
        appointment = Appointment.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            date=now.date(),
            start_time=(now - timedelta(minutes=5)).time().replace(microsecond=0),
            end_time=(now + timedelta(minutes=25)).time().replace(microsecond=0),
            status=Appointment.Status.CONFIRMADA,
            reason='Revision en curso',
        )
        self.client.force_login(self.doctor)

        response = self.client.get(reverse('citas:doctor-review', args=[appointment.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Cancelar cita')
        self.assertContains(response, 'En curso, ya no cancelable.')

    def test_doctor_calendar_only_returns_confirmed_appointments(self):
        appointment_date = timezone.localdate() + timedelta(days=1)
        confirmed_appointment = Appointment.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            date=appointment_date,
            start_time=time(9, 0),
            end_time=time(9, 30),
            status=Appointment.Status.CONFIRMADA,
            reason='Confirmada',
        )
        Appointment.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            date=appointment_date,
            start_time=time(10, 0),
            end_time=time(10, 30),
            status=Appointment.Status.PENDIENTE,
            reason='Pendiente',
        )

        calendar_data = get_month_calendar(self.doctor, appointment_date.year, appointment_date.month)

        self.assertEqual(calendar_data[appointment_date.day], [confirmed_appointment])

    def test_doctor_calendar_shows_in_progress_message_after_start_time(self):
        now = timezone.localtime()
        appointment = Appointment.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            date=now.date(),
            start_time=(now - timedelta(minutes=5)).time().replace(microsecond=0),
            end_time=(now + timedelta(minutes=25)).time().replace(microsecond=0),
            status=Appointment.Status.CONFIRMADA,
            reason='Revision en curso',
        )
        self.client.force_login(self.doctor)

        response = self.client.get(reverse('citas:doctor-calendar'), {'month': now.strftime('%Y-%m')})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, appointment.patient.full_name)
        self.assertContains(response, 'En curso, ya no cancelable')
        self.assertNotContains(response, 'Cancelar cita')

    def test_doctor_calendar_provides_direct_links_to_cardex_and_history(self):
        appointment_date = timezone.localdate() + timedelta(days=1)
        appointment = Appointment.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            date=appointment_date,
            start_time=time(9, 0),
            end_time=time(9, 30),
            status=Appointment.Status.CONFIRMADA,
            reason='Control',
        )
        self.client.force_login(self.doctor)

        response = self.client.get(reverse('citas:doctor-calendar'), {'month': appointment_date.strftime('%Y-%m')})

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            f"{reverse('clinico:record-update', args=[appointment.pk])}?next=%2Fcitas%2Fmedico%2Fcalendario%2F%3Fmonth%3D{appointment_date.strftime('%Y-%m')}",
            html=False,
        )
        self.assertContains(response, reverse('clinico:patient-history', args=[self.patient.pk]))

    def test_doctor_calendar_supports_week_view(self):
        appointment_date = timezone.localdate() + timedelta(days=(2 - timezone.localdate().weekday()) % 7)
        appointment = Appointment.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            date=appointment_date,
            start_time=time(11, 0),
            end_time=time(12, 0),
            status=Appointment.Status.CONFIRMADA,
            reason='Seguimiento semanal',
        )
        self.client.force_login(self.doctor)

        response = self.client.get(reverse('citas:doctor-calendar'), {'view': 'week', 'date': appointment_date.isoformat()})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Semana')
        self.assertContains(response, 'Hora')
        self.assertContains(response, '11:00')
        self.assertContains(response, appointment.patient.full_name)
        self.assertContains(response, reverse('clinico:record-update', args=[appointment.pk]))
        self.assertContains(
            response,
            f'?view=week&amp;date={(appointment_date - timedelta(days=7)).isoformat()}',
            html=False,
        )

    def test_doctor_calendar_week_view_supports_overlapping_cards(self):
        appointment_date = timezone.localdate() + timedelta(days=(2 - timezone.localdate().weekday()) % 7)
        first_patient = User.objects.create_user(
            email='solape1@example.com',
            password='Paciente123!',
            full_name='Paciente Paralelo Uno',
            phone='5557770001',
            role=User.Role.PACIENTE,
            is_active=True,
            email_verified=True,
        )
        second_patient = User.objects.create_user(
            email='solape2@example.com',
            password='Paciente123!',
            full_name='Paciente Paralelo Dos',
            phone='5557770002',
            role=User.Role.PACIENTE,
            is_active=True,
            email_verified=True,
        )
        Appointment.objects.create(
            patient=first_patient,
            doctor=self.doctor,
            date=appointment_date,
            start_time=time(11, 0),
            end_time=time(12, 0),
            status=Appointment.Status.CONFIRMADA,
            reason='Bloque uno',
        )
        Appointment.objects.create(
            patient=second_patient,
            doctor=self.doctor,
            date=appointment_date,
            start_time=time(11, 30),
            end_time=time(12, 30),
            status=Appointment.Status.CONFIRMADA,
            reason='Bloque dos',
        )
        self.client.force_login(self.doctor)

        response = self.client.get(reverse('citas:doctor-calendar'), {'view': 'week', 'date': appointment_date.isoformat()})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Paciente Paralelo Uno')
        self.assertContains(response, 'Paciente Paralelo Dos')
        self.assertContains(response, '--lane-count: 2;', html=False)

    def test_doctor_calendar_supports_day_view(self):
        appointment_date = timezone.localdate() + timedelta(days=1)
        appointment = Appointment.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            date=appointment_date,
            start_time=time(15, 0),
            end_time=time(15, 30),
            status=Appointment.Status.CONFIRMADA,
            reason='Seguimiento diario',
        )
        self.client.force_login(self.doctor)

        response = self.client.get(reverse('citas:doctor-calendar'), {'view': 'day', 'date': appointment_date.isoformat()})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, appointment.patient.full_name)
        self.assertContains(response, reverse('clinico:patient-history', args=[self.patient.pk]))
        self.assertContains(
            response,
            f'?view=day&amp;date={(appointment_date + timedelta(days=1)).isoformat()}',
            html=False,
        )

    def test_doctor_calendar_month_view_has_previous_and_next_navigation(self):
        month_date = timezone.localdate().replace(day=1)
        previous_month = (month_date - timedelta(days=1)).replace(day=1)
        next_month = (month_date.replace(day=28) + timedelta(days=4)).replace(day=1)
        self.client.force_login(self.doctor)

        response = self.client.get(reverse('citas:doctor-calendar'), {'view': 'month', 'month': month_date.strftime('%Y-%m')})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f'?view=month&amp;month={previous_month.strftime("%Y-%m")}', html=False)
        self.assertContains(response, f'?view=month&amp;month={next_month.strftime("%Y-%m")}', html=False)

    def test_appointment_print_shows_in_progress_message(self):
        now = timezone.localtime()
        appointment = Appointment.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            date=now.date(),
            start_time=(now - timedelta(minutes=5)).time().replace(microsecond=0),
            end_time=(now + timedelta(minutes=25)).time().replace(microsecond=0),
            status=Appointment.Status.CONFIRMADA,
            reason='Revision en curso',
        )
        self.client.force_login(self.doctor)

        response = self.client.get(reverse('citas:appointment-print', args=[appointment.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'En curso, ya no cancelable.')
