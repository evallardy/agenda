from io import BytesIO
from textwrap import wrap

from django.contrib import messages
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.generic import TemplateView
from django.views import View
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from core.mixins import DoctorRequiredMixin
from citas.models import Appointment
from users.models import User

from .forms import ClinicalRecordForm, MedicationFormSet
from .models import ClinicalRecord


def _get_safe_return_url(request, default_url):
    candidate = request.GET.get('next') or request.POST.get('next')
    if candidate and url_has_allowed_host_and_scheme(candidate, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
        return candidate
    return default_url


def _get_return_label(appointment, return_url):
    calendar_url = reverse('citas:doctor-calendar')
    dashboard_url = reverse('core:dashboard')
    history_url = reverse('clinico:patient-history', args=[appointment.patient_id])

    if return_url.startswith(calendar_url):
        return 'Volver al calendario'
    if return_url.startswith(history_url):
        return 'Volver al historial'
    if return_url.startswith(dashboard_url):
        return 'Volver al panel'
    return 'Volver a la cita'


class DoctorPatientSearchView(DoctorRequiredMixin, TemplateView):
    template_name = 'clinico/patient_search.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        query = self.request.GET.get('q', '').strip()
        patients = User.objects.filter(
            role=User.Role.PACIENTE,
            patient_appointments__doctor=self.request.user,
        ).distinct().order_by('full_name')

        if query:
            patients = patients.filter(
                Q(full_name__icontains=query)
                | Q(email__icontains=query)
            )

        context['query'] = query
        context['patients'] = patients
        return context


class PatientClinicalHistoryView(DoctorRequiredMixin, TemplateView):
    template_name = 'clinico/patient_history.html'

    def dispatch(self, request, *args, **kwargs):
        patient_queryset = User.objects.filter(
            role=User.Role.PACIENTE,
            patient_appointments__doctor=request.user,
        )
        self.patient = get_object_or_404(patient_queryset.distinct(), pk=kwargs['pk'])
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        diagnosis_query = self.request.GET.get('diagnosis', '').strip()
        date_from = self.request.GET.get('date_from', '').strip()
        date_to = self.request.GET.get('date_to', '').strip()
        records = ClinicalRecord.objects.filter(
            appointment__doctor=self.request.user,
            appointment__patient=self.patient,
        ).select_related('appointment').prefetch_related('medications').order_by('-appointment__date', '-appointment__start_time')

        if diagnosis_query:
            records = records.filter(diagnosis__icontains=diagnosis_query)
        if date_from:
            records = records.filter(appointment__date__gte=date_from)
        if date_to:
            records = records.filter(appointment__date__lte=date_to)

        context['patient'] = self.patient
        context['records'] = records
        context['diagnosis_query'] = diagnosis_query
        context['date_from'] = date_from
        context['date_to'] = date_to
        return context


class ClinicalPrescriptionPrintView(DoctorRequiredMixin, TemplateView):
    template_name = 'clinico/prescription_print.html'

    def dispatch(self, request, *args, **kwargs):
        self.appointment = get_object_or_404(Appointment, pk=kwargs['pk'], doctor=request.user)
        self.record = get_object_or_404(ClinicalRecord.objects.prefetch_related('medications'), appointment=self.appointment)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['appointment'] = self.appointment
        context['record'] = self.record
        context['medications'] = self.record.medications.all()
        return context


class ClinicalPrescriptionPdfView(DoctorRequiredMixin, View):
    def dispatch(self, request, *args, **kwargs):
        self.appointment = get_object_or_404(Appointment, pk=kwargs['pk'], doctor=request.user)
        self.record = get_object_or_404(ClinicalRecord.objects.prefetch_related('medications'), appointment=self.appointment)
        return super().dispatch(request, *args, **kwargs)

    def _draw_wrapped_text(self, pdf, text, x, y, max_chars, line_height):
        if not text:
            pdf.drawString(x, y, 'Sin registro')
            return y - line_height

        current_y = y
        for paragraph in str(text).splitlines() or ['']:
            wrapped_lines = wrap(paragraph, width=max_chars) or ['']
            for line in wrapped_lines:
                pdf.drawString(x, current_y, line)
                current_y -= line_height
        return current_y

    def get(self, request, *args, **kwargs):
        buffer = BytesIO()
        pdf = canvas.Canvas(buffer, pagesize=A4)
        width, height = A4
        left_margin = 50
        y = height - 60

        pdf.setTitle(f'Receta_{self.appointment.patient.full_name}')
        pdf.setFont('Helvetica-Bold', 18)
        pdf.drawString(left_margin, y, 'Receta medica')
        y -= 28

        pdf.setFont('Helvetica', 11)
        pdf.drawString(left_margin, y, f'Medico: {self.appointment.doctor.full_name}')
        y -= 18
        pdf.drawString(left_margin, y, f'Especialidades: {self.appointment.doctor.specialties or "No registradas"}')
        y -= 18
        pdf.drawString(left_margin, y, f'Fecha: {self.appointment.date.strftime("%d/%m/%Y")}')
        y -= 18
        pdf.drawString(left_margin, y, f'Paciente: {self.appointment.patient.full_name}')
        y -= 18
        pdf.drawString(left_margin, y, f'Correo: {self.appointment.patient.email}')
        y -= 28

        pdf.setFont('Helvetica-Bold', 12)
        pdf.drawString(left_margin, y, 'Sintomas')
        y -= 18
        pdf.setFont('Helvetica', 11)
        y = self._draw_wrapped_text(pdf, self.record.symptoms, left_margin, y, 90, 15)
        y -= 10

        pdf.setFont('Helvetica-Bold', 12)
        pdf.drawString(left_margin, y, 'Diagnostico')
        y -= 18
        pdf.setFont('Helvetica', 11)
        y = self._draw_wrapped_text(pdf, self.record.diagnosis, left_margin, y, 90, 15)
        y -= 15

        pdf.setFont('Helvetica-Bold', 12)
        pdf.drawString(left_margin, y, 'Medicamentos')
        y -= 20
        pdf.setFont('Helvetica', 10)
        for index, medication in enumerate(self.record.medications.all(), start=1):
            if y < 110:
                pdf.showPage()
                y = height - 60
                pdf.setFont('Helvetica', 10)
            medication_line = (
                f'{index}. {medication.name} | Cantidad: {medication.quantity} | '
                f'Dosis: {medication.dosage} | Frecuencia: {medication.frequency} | '
                f'Duracion: {medication.duration_days} dias'
            )
            y = self._draw_wrapped_text(pdf, medication_line, left_margin, y, 95, 14)
            y = self._draw_wrapped_text(
                pdf,
                f'Indicaciones: {medication.instructions or "Sin indicaciones adicionales"}',
                left_margin + 12,
                y,
                90,
                14,
            )
            y -= 8

        pdf.showPage()
        pdf.save()
        buffer.seek(0)

        response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="receta-{self.appointment.pk}.pdf"'
        return response


class ClinicalRecordUpdateView(DoctorRequiredMixin, View):
    template_name = 'clinico/record_form.html'

    def dispatch(self, request, *args, **kwargs):
        self.appointment = get_object_or_404(Appointment, pk=kwargs['pk'], doctor=request.user)
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        record, _ = ClinicalRecord.objects.get_or_create(
            appointment=self.appointment,
            defaults={'created_by': request.user, 'symptoms': '', 'vital_signs': ''},
        )
        form = ClinicalRecordForm(instance=record)
        formset = MedicationFormSet(instance=record)
        return_url = _get_safe_return_url(request, reverse('citas:doctor-review', args=[self.appointment.pk]))
        return render(
            request,
            self.template_name,
            {
                'form': form,
                'formset': formset,
                'appointment': self.appointment,
                'record': record,
                'return_url': return_url,
                'return_label': _get_return_label(self.appointment, return_url),
            },
        )

    def post(self, request, *args, **kwargs):
        record, _ = ClinicalRecord.objects.get_or_create(
            appointment=self.appointment,
            defaults={'created_by': request.user, 'symptoms': '', 'vital_signs': ''},
        )
        form = ClinicalRecordForm(request.POST, instance=record)
        formset = MedicationFormSet(request.POST, instance=record)
        return_url = _get_safe_return_url(request, reverse('citas:doctor-review', args=[self.appointment.pk]))

        if form.is_valid() and formset.is_valid():
            clinical_record = form.save(commit=False)
            clinical_record.created_by = request.user
            clinical_record.save()
            formset.instance = clinical_record
            formset.save()
            if self.appointment.status != Appointment.Status.ATENDIDA:
                self.appointment.status = Appointment.Status.ATENDIDA
                self.appointment.save(update_fields=['status', 'updated_at'])
            messages.success(request, 'El cardex clinico fue guardado correctamente.')
            return redirect(return_url)

        return render(
            request,
            self.template_name,
            {
                'form': form,
                'formset': formset,
                'appointment': self.appointment,
                'record': record,
                'return_url': return_url,
                'return_label': _get_return_label(self.appointment, return_url),
            },
        )
