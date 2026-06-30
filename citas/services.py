from collections import defaultdict
from datetime import datetime, timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import EmailMultiAlternatives, send_mail
from django.db.models import Q
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from users.email_tracking import send_tracked_email_message, send_tracked_mail

from .models import Appointment, BusinessHours, ScheduleSettings

User = get_user_model()

ACTIVE_STATUSES = (Appointment.Status.PENDIENTE, Appointment.Status.CONFIRMADA)


def get_primary_doctor():
    return User.objects.filter(Q(is_superuser=True) | Q(role=User.Role.MEDICO)).order_by('-is_superuser', 'id').first()


def get_schedule_settings(doctor):
    settings_obj, _ = ScheduleSettings.objects.get_or_create(doctor=doctor)
    return settings_obj


def get_business_hours_for_date(doctor, appointment_date):
    settings_obj = get_schedule_settings(doctor)
    return settings_obj.business_hours.filter(weekday=appointment_date.weekday(), active=True).first()


def build_slots(start_time, end_time, duration_minutes):
    slots = []
    cursor = datetime.combine(datetime.today().date(), start_time)
    day_end = datetime.combine(datetime.today().date(), end_time)

    while cursor + timedelta(minutes=duration_minutes) <= day_end:
        slot_end = cursor + timedelta(minutes=duration_minutes)
        slots.append((cursor.time(), slot_end.time()))
        cursor = slot_end

    return slots


def get_available_slots(doctor, appointment_date):
    business_hours = get_business_hours_for_date(doctor, appointment_date)
    if not business_hours:
        return []

    settings_obj = get_schedule_settings(doctor)
    all_slots = build_slots(
        business_hours.start_time,
        business_hours.end_time,
        settings_obj.consultation_duration,
    )
    taken_slots = set(
        Appointment.objects.filter(
            doctor=doctor,
            date=appointment_date,
            status__in=ACTIVE_STATUSES,
        ).values_list('start_time', flat=True)
    )
    return [slot for slot in all_slots if slot[0] not in taken_slots]


def suggest_next_available_days(doctor, desired_date, limit=3):
    suggestions = []
    current_date = desired_date + timedelta(days=1)
    max_date = desired_date + timedelta(days=90)

    while len(suggestions) < limit and current_date <= max_date:
        slots = get_available_slots(doctor, current_date)
        if slots:
            suggestions.append((current_date, slots))
        current_date += timedelta(days=1)

    return suggestions


def get_next_appointment_for_patient(patient):
    return Appointment.objects.filter(
        patient=patient,
        status__in=ACTIVE_STATUSES,
        date__gte=timezone.localdate(),
    ).order_by('date', 'start_time').first()


def patient_has_future_appointment(patient):
    return Appointment.objects.filter(
        patient=patient,
        status__in=ACTIVE_STATUSES,
        date__gte=timezone.localdate(),
    ).exists()


def send_appointment_request_email(appointment, request):
    pending_url = request.build_absolute_uri(reverse('citas:doctor-review', args=[appointment.pk]))
    send_tracked_mail(
        subject='Nueva solicitud de cita',
        message=(
            f'El paciente {appointment.patient.full_name} solicito una cita para el '
            f'{appointment.date:%d/%m/%Y} a las {appointment.start_time:%H:%M}.\n\n'
            f'Revisa la solicitud aqui: {pending_url}'
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[appointment.doctor.email],
        context_type='appointment_request',
        triggered_by=appointment.patient,
    )


def _build_doctor_photo_url(appointment, request):
    if appointment.doctor.photo:
        return request.build_absolute_uri(appointment.doctor.photo.url)
    return None


def _send_patient_appointment_email(appointment, request, subject, body_template, html_template, extra_context=None):
    context = {
        'appointment': appointment,
        'doctor': appointment.doctor,
        'patient': appointment.patient,
        'doctor_photo_url': _build_doctor_photo_url(appointment, request),
        'appointment_print_url': request.build_absolute_uri(reverse('citas:appointment-print', args=[appointment.pk])),
    }
    if extra_context:
        context.update(extra_context)

    text_body = render_to_string(body_template, context)
    html_body = render_to_string(html_template, context)
    email = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[appointment.patient.email],
    )
    email.attach_alternative(html_body, 'text/html')
    send_tracked_email_message(
        email,
        context_type='appointment_patient_email',
        triggered_by=appointment.doctor,
    )


def send_patient_appointment_created_email(appointment, request):
    _send_patient_appointment_email(
        appointment,
        request,
        subject='Tu cita fue registrada',
        body_template='citas/email/patient_appointment_created.txt',
        html_template='citas/email/patient_appointment_created.html',
    )


def send_patient_appointment_status_email(appointment, request):
    status_label = appointment.get_status_display()
    _send_patient_appointment_email(
        appointment,
        request,
        subject=f'Actualizacion de tu cita: {status_label}',
        body_template='citas/email/patient_appointment_status.txt',
        html_template='citas/email/patient_appointment_status.html',
        extra_context={'status_label': status_label},
    )


def get_month_calendar(doctor, year, month):
    appointments = Appointment.objects.filter(
        doctor=doctor,
        date__year=year,
        date__month=month,
        status=Appointment.Status.CONFIRMADA,
    ).select_related('patient')
    grouped = defaultdict(list)
    for appointment in appointments:
        grouped[appointment.date.day].append(appointment)
    return grouped


def get_calendar_appointments_between(doctor, start_date, end_date):
    appointments = Appointment.objects.filter(
        doctor=doctor,
        date__gte=start_date,
        date__lte=end_date,
        status=Appointment.Status.CONFIRMADA,
    ).select_related('patient').order_by('date', 'start_time')
    grouped = defaultdict(list)
    for appointment in appointments:
        grouped[appointment.date].append(appointment)
    return grouped
