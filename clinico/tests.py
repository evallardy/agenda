from datetime import time, timedelta

from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from citas.models import Appointment
from users.models import User

from .forms import MedicationFormSet
from .models import ClinicalRecord, Medication


@override_settings(ALLOWED_HOSTS=['testserver', 'localhost', '127.0.0.1'])
class ClinicalRecordTests(TestCase):
    def setUp(self):
        self.doctor = User.objects.create_user(
            email='doctor.clinico@example.com',
            password='Admin12345!',
            full_name='Doctor Clinico',
            phone='5552222222',
            role=User.Role.MEDICO,
            is_active=True,
            email_verified=True,
            is_staff=True,
        )
        self.patient = User.objects.create_user(
            email='paciente.clinico@example.com',
            password='Paciente123!',
            full_name='Paciente Clinico',
            phone='5553333333',
            role=User.Role.PACIENTE,
            is_active=True,
            email_verified=True,
        )
        self.appointment = Appointment.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            date=timezone.localdate() + timedelta(days=1),
            start_time=time(10, 0),
            end_time=time(10, 30),
            status=Appointment.Status.CONFIRMADA,
            reason='Control',
        )

    def test_saving_clinical_record_marks_appointment_attended_and_creates_medication(self):
        self.client.force_login(self.doctor)
        self.client.get(reverse('clinico:record-update', args=[self.appointment.pk]))
        record = ClinicalRecord.objects.get(appointment=self.appointment)
        prefix = MedicationFormSet(instance=record).prefix

        response = self.client.post(
            reverse('clinico:record-update', args=[self.appointment.pk]),
            {
                'symptoms': 'Dolor de garganta',
                'vital_signs': 'TA 120/80',
                'diagnosis': 'Faringitis',
                'notes': 'Seguimiento en 5 dias',
                f'{prefix}-TOTAL_FORMS': '1',
                f'{prefix}-INITIAL_FORMS': '0',
                f'{prefix}-MIN_NUM_FORMS': '0',
                f'{prefix}-MAX_NUM_FORMS': '1000',
                f'{prefix}-0-name': 'Ibuprofeno',
                f'{prefix}-0-quantity': '12 tabletas',
                f'{prefix}-0-dosage': '1 tableta',
                f'{prefix}-0-frequency': 'Cada 8 horas',
                f'{prefix}-0-duration_days': '4',
                f'{prefix}-0-instructions': 'Despues de alimentos',
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.appointment.refresh_from_db()
        record.refresh_from_db()
        self.assertEqual(self.appointment.status, Appointment.Status.ATENDIDA)
        self.assertEqual(record.medications.count(), 1)

    def test_saving_clinical_record_supports_multiple_medications(self):
        self.client.force_login(self.doctor)
        self.client.get(reverse('clinico:record-update', args=[self.appointment.pk]))
        record = ClinicalRecord.objects.get(appointment=self.appointment)
        prefix = MedicationFormSet(instance=record).prefix

        response = self.client.post(
            reverse('clinico:record-update', args=[self.appointment.pk]),
            {
                'symptoms': 'Dolor y fiebre',
                'vital_signs': 'TA 120/80',
                'diagnosis': 'Infeccion',
                'notes': 'Seguimiento en 3 dias',
                f'{prefix}-TOTAL_FORMS': '2',
                f'{prefix}-INITIAL_FORMS': '0',
                f'{prefix}-MIN_NUM_FORMS': '0',
                f'{prefix}-MAX_NUM_FORMS': '1000',
                f'{prefix}-0-name': 'Ibuprofeno',
                f'{prefix}-0-quantity': '12 tabletas',
                f'{prefix}-0-dosage': '1 tableta',
                f'{prefix}-0-frequency': 'Cada 8 horas',
                f'{prefix}-0-duration_days': '4',
                f'{prefix}-0-instructions': 'Despues de alimentos',
                f'{prefix}-1-name': 'Amoxicilina',
                f'{prefix}-1-quantity': '21 capsulas',
                f'{prefix}-1-dosage': '1 capsula',
                f'{prefix}-1-frequency': 'Cada 8 horas',
                f'{prefix}-1-duration_days': '7',
                f'{prefix}-1-instructions': 'Completar tratamiento',
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        record.refresh_from_db()
        self.assertEqual(record.medications.count(), 2)

    def test_cardex_preserves_return_url_from_calendar(self):
        self.client.force_login(self.doctor)
        return_url = f"{reverse('citas:doctor-calendar')}?view=week&date={self.appointment.date.isoformat()}"

        response = self.client.get(reverse('clinico:record-update', args=[self.appointment.pk]), {'next': return_url})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Volver al calendario')
        self.assertContains(response, f'href="{return_url}"', html=False)
        self.assertContains(response, f'value="{return_url}"', html=False)

    def test_cardex_renders_medication_list_and_modal_trigger(self):
        self.client.force_login(self.doctor)

        response = self.client.get(reverse('clinico:record-update', args=[self.appointment.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="medication-table-body"', html=False)
        self.assertContains(response, 'id="open-medication-modal"', html=False)
        self.assertContains(response, 'id="medicationModal"', html=False)
        self.assertContains(response, 'Guardar medicamento')
        self.assertContains(response, 'Guardar y agregar otro')
        self.assertContains(response, '<th>Medicamento</th>', html=False)

    def test_saving_clinical_record_redirects_back_to_origin(self):
        self.client.force_login(self.doctor)
        self.client.get(reverse('clinico:record-update', args=[self.appointment.pk]))
        record = ClinicalRecord.objects.get(appointment=self.appointment)
        prefix = MedicationFormSet(instance=record).prefix
        return_url = f"{reverse('citas:doctor-calendar')}?view=day&date={self.appointment.date.isoformat()}"

        response = self.client.post(
            reverse('clinico:record-update', args=[self.appointment.pk]),
            {
                'next': return_url,
                'symptoms': 'Dolor de garganta',
                'vital_signs': 'TA 120/80',
                'diagnosis': 'Faringitis',
                'notes': 'Seguimiento en 5 dias',
                f'{prefix}-TOTAL_FORMS': '1',
                f'{prefix}-INITIAL_FORMS': '0',
                f'{prefix}-MIN_NUM_FORMS': '0',
                f'{prefix}-MAX_NUM_FORMS': '1000',
                f'{prefix}-0-name': 'Ibuprofeno',
                f'{prefix}-0-quantity': '12 tabletas',
                f'{prefix}-0-dosage': '1 tableta',
                f'{prefix}-0-frequency': 'Cada 8 horas',
                f'{prefix}-0-duration_days': '4',
                f'{prefix}-0-instructions': 'Despues de alimentos',
            },
        )

        self.assertRedirects(response, return_url, fetch_redirect_response=False)

    def test_doctor_can_search_patient_by_name_or_email(self):
        self.client.force_login(self.doctor)

        response = self.client.get(reverse('clinico:patient-search'), {'q': 'paciente.clinico@example.com'})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Paciente Clinico')

    def test_doctor_can_view_patient_history(self):
        record = ClinicalRecord.objects.create(
            appointment=self.appointment,
            symptoms='Dolor de garganta',
            vital_signs='TA 120/80',
            diagnosis='Faringitis',
            notes='Seguimiento en 5 dias',
            created_by=self.doctor,
        )
        Medication.objects.create(
            clinical_record=record,
            name='Ibuprofeno',
            quantity='12 tabletas',
            dosage='1 tableta',
            frequency='Cada 8 horas',
            duration_days=4,
            instructions='Despues de alimentos',
        )
        self.client.force_login(self.doctor)

        response = self.client.get(reverse('clinico:patient-history', args=[self.patient.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Paciente Clinico')
        self.assertContains(response, 'Ibuprofeno')

    def test_patient_history_shows_in_progress_message(self):
        now = timezone.localtime()
        current_appointment = Appointment.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            date=now.date(),
            start_time=(now - timedelta(minutes=5)).time().replace(microsecond=0),
            end_time=(now + timedelta(minutes=25)).time().replace(microsecond=0),
            status=Appointment.Status.CONFIRMADA,
            reason='Control en curso',
        )
        ClinicalRecord.objects.create(
            appointment=current_appointment,
            symptoms='Dolor de garganta',
            vital_signs='TA 120/80',
            diagnosis='Faringitis',
            notes='Seguimiento en 5 dias',
            created_by=self.doctor,
        )
        self.client.force_login(self.doctor)

        response = self.client.get(reverse('clinico:patient-history', args=[self.patient.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'En curso, ya no cancelable.')

    def test_doctor_can_filter_patient_history_by_diagnosis_and_date(self):
        old_appointment = Appointment.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            date=timezone.localdate() - timedelta(days=7),
            start_time=time(9, 0),
            end_time=time(9, 30),
            status=Appointment.Status.ATENDIDA,
            reason='Seguimiento previo',
        )
        ClinicalRecord.objects.create(
            appointment=old_appointment,
            symptoms='Tos',
            vital_signs='TA 118/79',
            diagnosis='Bronquitis',
            notes='Control en una semana',
            created_by=self.doctor,
        )
        current_record = ClinicalRecord.objects.create(
            appointment=self.appointment,
            symptoms='Dolor de garganta',
            vital_signs='TA 120/80',
            diagnosis='Faringitis',
            notes='Seguimiento en 5 dias',
            created_by=self.doctor,
        )
        Medication.objects.create(
            clinical_record=current_record,
            name='Ibuprofeno',
            quantity='12 tabletas',
            dosage='1 tableta',
            frequency='Cada 8 horas',
            duration_days=4,
            instructions='Despues de alimentos',
        )
        self.client.force_login(self.doctor)

        response = self.client.get(
            reverse('clinico:patient-history', args=[self.patient.pk]),
            {
                'diagnosis': 'Faringitis',
                'date_from': self.appointment.date.isoformat(),
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Faringitis')
        self.assertNotContains(response, 'Bronquitis')

    def test_doctor_can_print_prescription(self):
        record = ClinicalRecord.objects.create(
            appointment=self.appointment,
            symptoms='Dolor de garganta',
            vital_signs='TA 120/80',
            diagnosis='Faringitis',
            notes='Seguimiento en 5 dias',
            created_by=self.doctor,
        )
        Medication.objects.create(
            clinical_record=record,
            name='Ibuprofeno',
            quantity='12 tabletas',
            dosage='1 tableta',
            frequency='Cada 8 horas',
            duration_days=4,
            instructions='Despues de alimentos',
        )
        self.client.force_login(self.doctor)

        response = self.client.get(reverse('clinico:prescription-print', args=[self.appointment.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Receta medica')
        self.assertContains(response, 'Ibuprofeno')

    def test_doctor_can_download_prescription_pdf(self):
        record = ClinicalRecord.objects.create(
            appointment=self.appointment,
            symptoms='Dolor de garganta',
            vital_signs='TA 120/80',
            diagnosis='Faringitis',
            notes='Seguimiento en 5 dias',
            created_by=self.doctor,
        )
        Medication.objects.create(
            clinical_record=record,
            name='Ibuprofeno',
            quantity='12 tabletas',
            dosage='1 tableta',
            frequency='Cada 8 horas',
            duration_days=4,
            instructions='Despues de alimentos',
        )
        self.client.force_login(self.doctor)

        response = self.client.get(reverse('clinico:prescription-pdf', args=[self.appointment.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertIn('receta-', response['Content-Disposition'])
