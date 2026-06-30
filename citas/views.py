import calendar
from datetime import date, time
from math import ceil

from django.contrib import messages
from django.db.models import Q
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import DetailView, FormView, ListView, TemplateView
from django.utils import timezone
from django.contrib.auth.mixins import LoginRequiredMixin

from core.mixins import DoctorRequiredMixin, PatientRequiredMixin

from .forms import AppointmentDateForm, ScheduleBatchForm
from .models import Appointment, BusinessHours
from .services import (
    get_available_slots,
    get_calendar_appointments_between,
    get_month_calendar,
    get_next_appointment_for_patient,
    get_primary_doctor,
    get_schedule_settings,
    patient_has_future_appointment,
    send_patient_appointment_created_email,
    send_patient_appointment_status_email,
    send_appointment_request_email,
    suggest_next_available_days,
)


def _hour_ceiling(value):
    return value.hour + (1 if value.minute or value.second or value.microsecond else 0)


def _time_to_minutes(value):
    return (value.hour * 60) + value.minute


def _get_week_slot_minutes(doctor):
    duration = get_schedule_settings(doctor).consultation_duration
    if duration % 30 == 0:
        return 30
    if duration % 15 == 0:
        return 15
    return 10


def _get_calendar_hour_range(doctor, appointments_by_date):
    business_hours = BusinessHours.objects.filter(settings__doctor=doctor, active=True)
    start_hour = min((item.start_time.hour for item in business_hours), default=None)
    end_hour = max((_hour_ceiling(item.end_time) for item in business_hours), default=None)

    all_appointments = [appointment for appointments in appointments_by_date.values() for appointment in appointments]
    if all_appointments:
        appointment_start = min(appointment.start_time.hour for appointment in all_appointments)
        appointment_end = max(_hour_ceiling(appointment.end_time) for appointment in all_appointments)
        start_hour = appointment_start if start_hour is None else min(start_hour, appointment_start)
        end_hour = appointment_end if end_hour is None else max(end_hour, appointment_end)

    if start_hour is None or end_hour is None or start_hour >= end_hour:
        start_hour, end_hour = 8, 18

    return range(start_hour, end_hour)


def _build_week_timeline(doctor, week_days, appointments_by_date):
    slot_minutes = _get_week_slot_minutes(doctor)
    hour_range = list(_get_calendar_hour_range(doctor, appointments_by_date))
    start_minutes = hour_range[0] * 60
    end_minutes = hour_range[-1] * 60 + 60
    total_slots = max(1, ceil((end_minutes - start_minutes) / slot_minutes))
    time_rows = []
    for slot_index in range(total_slots):
        row_minutes = start_minutes + (slot_index * slot_minutes)
        time_rows.append(
            {
                'label': f'{row_minutes // 60:02d}:{row_minutes % 60:02d}',
                'is_hour_mark': row_minutes % 60 == 0,
                'grid_row': slot_index + 2,
            }
        )

    background_cells = [
        {
            'grid_column': day_index + 2,
            'grid_row': slot_index + 2,
            'is_hour_mark': (start_minutes + (slot_index * slot_minutes)) % 60 == 0,
        }
        for day_index, _week_day in enumerate(week_days)
        for slot_index in range(total_slots)
    ]

    positioned_appointments = []
    for day_index, week_day in enumerate(week_days):
        day_appointments = appointments_by_date.get(week_day, [])
        lane_end_minutes = []
        day_lane_assignments = []

        for appointment in day_appointments:
            appointment_start = _time_to_minutes(appointment.start_time)
            appointment_end = _time_to_minutes(appointment.end_time)
            lane_index = 0
            while lane_index < len(lane_end_minutes) and lane_end_minutes[lane_index] > appointment_start:
                lane_index += 1
            if lane_index == len(lane_end_minutes):
                lane_end_minutes.append(appointment_end)
            else:
                lane_end_minutes[lane_index] = appointment_end
            day_lane_assignments.append((appointment, lane_index))

        lane_count = max(1, len(lane_end_minutes))
        for appointment, lane_index in day_lane_assignments:
            start_slot = max(0, (_time_to_minutes(appointment.start_time) - start_minutes) // slot_minutes)
            slot_span = max(1, ceil((_time_to_minutes(appointment.end_time) - _time_to_minutes(appointment.start_time)) / slot_minutes))
            positioned_appointments.append(
                {
                    'appointment': appointment,
                    'grid_column': day_index + 2,
                    'grid_row': start_slot + 2,
                    'slot_span': slot_span,
                    'lane_index': lane_index,
                    'lane_count': lane_count,
                }
            )

    return {
        'slot_minutes': slot_minutes,
        'row_count': total_slots,
        'time_rows': time_rows,
        'background_cells': background_cells,
        'positioned_appointments': positioned_appointments,
    }


class PatientAppointmentRequestView(PatientRequiredMixin, FormView):
    template_name = 'citas/patient_request.html'
    form_class = AppointmentDateForm
    success_url = reverse_lazy('citas:patient-request')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['doctor_profile'] = get_primary_doctor()
        return context

    def form_valid(self, form):
        if patient_has_future_appointment(self.request.user):
            form.add_error(None, 'Solo puedes tener una cita activa a la vez.')
            return self.form_invalid(form)

        doctor = get_primary_doctor()
        if doctor is None:
            form.add_error(None, 'Aun no hay un medico configurado en el sistema.')
            return self.form_invalid(form)

        appointment_date = form.cleaned_data['appointment_date']
        slots = get_available_slots(doctor, appointment_date)
        suggestions = [] if slots else suggest_next_available_days(doctor, appointment_date)

        context = self.get_context_data(form=form)
        context.update(
            {
                'selected_date': appointment_date,
                'selected_reason': form.cleaned_data['reason'],
                'available_slots': slots,
                'suggestions': suggestions,
            }
        )
        return self.render_to_response(context)


class PatientAppointmentCreateView(PatientRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        if patient_has_future_appointment(request.user):
            messages.error(request, 'Ya tienes una cita activa. Debes cancelarla antes de solicitar otra.')
            return redirect('citas:patient-next')

        doctor = get_primary_doctor()
        if doctor is None:
            messages.error(request, 'No hay medico disponible para recibir citas.')
            return redirect('citas:patient-request')

        appointment_date = request.POST.get('appointment_date')
        start_time_raw = request.POST.get('start_time')
        reason = request.POST.get('reason', '')
        if not appointment_date or not start_time_raw:
            messages.error(request, 'Debes seleccionar un horario disponible.')
            return redirect('citas:patient-request')

        appointment_date_value = date.fromisoformat(appointment_date)
        available_slots = {}
        for start_time_value, end_time_value in get_available_slots(doctor, appointment_date_value):
            available_slots[start_time_value.isoformat(timespec='minutes')] = end_time_value
            available_slots[start_time_value.isoformat()] = end_time_value
        end_time = available_slots.get(start_time_raw)
        if end_time is None:
            messages.error(request, 'Ese horario ya no esta disponible.')
            return redirect('citas:patient-request')

        appointment = Appointment.objects.create(
            patient=request.user,
            doctor=doctor,
            date=appointment_date_value,
            start_time=time.fromisoformat(start_time_raw),
            end_time=end_time,
            reason=reason,
        )
        send_appointment_request_email(appointment, request)
        send_patient_appointment_created_email(appointment, request)
        messages.success(request, 'Tu cita fue solicitada y quedo pendiente de confirmacion del medico.')
        return redirect('citas:patient-next')


class PatientNextAppointmentView(PatientRequiredMixin, TemplateView):
    template_name = 'citas/patient_next_appointment.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['next_appointment'] = get_next_appointment_for_patient(self.request.user)
        return context


class PatientAppointmentCancelView(PatientRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        appointment = get_next_appointment_for_patient(request.user)
        if appointment is None:
            messages.error(request, 'No tienes una cita activa para cancelar.')
            return redirect('citas:patient-next')

        if not appointment.can_be_cancelled:
            messages.error(request, 'La cita ya no se puede cancelar porque el horario ya comenzo.')
            return redirect('citas:patient-next')

        appointment.status = Appointment.Status.CANCELADA_PACIENTE
        appointment.save(update_fields=['status', 'updated_at'])
        messages.success(request, 'Tu cita fue cancelada correctamente.')
        return redirect('citas:patient-next')


class DoctorScheduleConfigView(DoctorRequiredMixin, FormView):
    template_name = 'citas/doctor_schedule_settings.html'
    form_class = ScheduleBatchForm
    success_url = reverse_lazy('citas:doctor-schedule')

    def get_initial(self):
        initial = super().get_initial()
        settings_obj = get_schedule_settings(self.request.user)
        initial['consultation_duration'] = settings_obj.consultation_duration
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['business_hours'] = BusinessHours.objects.filter(settings__doctor=self.request.user).order_by('weekday')
        return context

    def form_valid(self, form):
        form.save(self.request.user)
        messages.success(self.request, 'La configuracion de agenda fue actualizada.')
        return super().form_valid(form)


class DoctorBusinessHoursDeactivateView(DoctorRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        business_hour = get_object_or_404(BusinessHours, pk=kwargs['pk'], settings__doctor=request.user)
        business_hour.active = False
        business_hour.save(update_fields=['active'])
        messages.success(request, 'El horario seleccionado quedo desactivado.')
        return redirect('citas:doctor-schedule')


class DoctorPendingAppointmentListView(DoctorRequiredMixin, ListView):
    template_name = 'citas/doctor_pending_appointments.html'
    context_object_name = 'appointments'

    def get_queryset(self):
        queryset = Appointment.objects.filter(
            doctor=self.request.user,
            status=Appointment.Status.PENDIENTE,
        ).select_related('patient')

        search_term = self.request.GET.get('q', '').strip()
        selected_date = self.request.GET.get('date', '').strip()

        if search_term:
            queryset = queryset.filter(
                Q(patient__full_name__icontains=search_term)
                | Q(patient__email__icontains=search_term)
                | Q(patient__phone__icontains=search_term)
                | Q(reason__icontains=search_term)
            )

        if selected_date:
            queryset = queryset.filter(date=selected_date)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_term'] = self.request.GET.get('q', '').strip()
        context['selected_date'] = self.request.GET.get('date', '').strip()
        context['pending_total'] = Appointment.objects.filter(
            doctor=self.request.user,
            status=Appointment.Status.PENDIENTE,
        ).count()
        return context


class DoctorAppointmentReviewView(DoctorRequiredMixin, DetailView):
    template_name = 'citas/doctor_appointment_review.html'
    model = Appointment
    context_object_name = 'appointment'

    def get_queryset(self):
        return Appointment.objects.filter(doctor=self.request.user).select_related('patient')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['print_url'] = reverse('citas:appointment-print', args=[self.object.pk])
        return context


class DoctorAppointmentDecisionView(DoctorRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        appointment = get_object_or_404(Appointment, pk=kwargs['pk'], doctor=request.user)
        action = request.POST.get('action')
        if appointment.status not in (Appointment.Status.PENDIENTE, Appointment.Status.CONFIRMADA):
            messages.error(request, 'La cita ya no se puede modificar desde este panel.')
            return redirect('core:dashboard')

        if action == 'confirm':
            appointment.status = Appointment.Status.CONFIRMADA
            appointment.doctor_cancellation_reason = ''
            message = 'La cita fue confirmada.'
        elif action == 'cancel':
            if not appointment.can_be_cancelled:
                messages.error(request, 'La cita ya no se puede cancelar porque el horario ya comenzo.')
                return redirect('citas:doctor-review', pk=appointment.pk)
            cancellation_reason = request.POST.get('cancellation_reason', '').strip()
            if not cancellation_reason:
                messages.error(request, 'Debes indicar la explicacion de la cancelacion.')
                return redirect('citas:doctor-review', pk=appointment.pk)
            appointment.status = Appointment.Status.CANCELADA_MEDICO
            appointment.doctor_cancellation_reason = cancellation_reason
            message = 'La cita fue cancelada.'
        else:
            raise Http404('Accion no valida.')

        appointment.save(update_fields=['status', 'doctor_cancellation_reason', 'updated_at'])
        send_patient_appointment_status_email(appointment, request)
        messages.success(request, message)
        return redirect('core:dashboard')


class AppointmentPrintView(LoginRequiredMixin, DetailView):
    template_name = 'citas/appointment_print.html'
    model = Appointment
    context_object_name = 'appointment'

    def get_queryset(self):
        return Appointment.objects.select_related('patient', 'doctor')

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        user = request.user
        is_owner = self.object.patient_id == user.id or self.object.doctor_id == user.id or user.is_superuser
        if not is_owner:
            raise Http404('No tienes acceso a esta cita.')
        return super().dispatch(request, *args, **kwargs)


class DoctorCalendarView(DoctorRequiredMixin, TemplateView):
    template_name = 'citas/doctor_calendar.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        view_mode = self.request.GET.get('view', 'month').strip().lower() or 'month'
        if view_mode not in {'month', 'week', 'day'}:
            view_mode = 'month'

        month_value = self.request.GET.get('month')
        date_value = self.request.GET.get('date')
        current_date = Appointment._meta.get_field('date').to_python(date_value) if date_value else None
        current_month = Appointment._meta.get_field('date').to_python(f'{month_value}-01') if month_value else None

        if current_date is None:
            current_date = timezone.localdate()
        if current_month is None:
            current_month = current_date.replace(day=1)

        previous_month = (current_month - timezone.timedelta(days=1)).replace(day=1)
        next_month = (current_month.replace(day=28) + timezone.timedelta(days=4)).replace(day=1)

        context.update(
            {
                'calendar_view': view_mode,
                'current_date': current_date,
                'current_month': current_month,
                'month_label': current_month.strftime('%B %Y').capitalize(),
                'previous_month': previous_month,
                'next_month': next_month,
                'previous_week_date': current_date - timezone.timedelta(days=7),
                'next_week_date': current_date + timezone.timedelta(days=7),
                'previous_day_date': current_date - timezone.timedelta(days=1),
                'next_day_date': current_date + timezone.timedelta(days=1),
            }
        )

        if view_mode == 'month':
            month_matrix = calendar.monthcalendar(current_month.year, current_month.month)
            appointments_by_day = get_month_calendar(self.request.user, current_month.year, current_month.month)
            weeks = []
            for week in month_matrix:
                weeks.append([
                    {
                        'day': day,
                        'appointments': appointments_by_day.get(day, []),
                    }
                    for day in week
                ])
            context['weeks'] = weeks
        elif view_mode == 'week':
            week_start = current_date - timezone.timedelta(days=current_date.weekday())
            week_days = [week_start + timezone.timedelta(days=offset) for offset in range(7)]
            appointments_by_date = get_calendar_appointments_between(self.request.user, week_start, week_start + timezone.timedelta(days=6))
            context['week_days'] = [
                {
                    'date': week_day,
                    'appointments': appointments_by_date.get(week_day, []),
                }
                for week_day in week_days
            ]
            context['week_timeline'] = _build_week_timeline(self.request.user, week_days, appointments_by_date)
            context['week_label'] = f'{week_start.strftime("%d/%m")} - {(week_start + timezone.timedelta(days=6)).strftime("%d/%m/%Y")}'
        else:
            appointments_by_date = get_calendar_appointments_between(self.request.user, current_date, current_date)
            context['day_appointments'] = appointments_by_date.get(current_date, [])
            context['day_label'] = current_date.strftime('%A %d de %B de %Y').capitalize()

        return context
