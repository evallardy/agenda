from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils import timezone
from django.views.generic import TemplateView

from citas.models import Appointment
from citas.services import get_next_appointment_for_patient, get_primary_doctor


class HomeView(TemplateView):
    template_name = 'core/home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['doctor_profile'] = get_primary_doctor()
        return context


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'core/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context['is_doctor'] = user.is_superuser or user.role == user.Role.MEDICO

        if context['is_doctor']:
            context['doctor_profile'] = user
            context['pending_count'] = Appointment.objects.filter(
                doctor=user,
                status=Appointment.Status.PENDIENTE,
            ).count()
            context['today_appointments'] = Appointment.objects.filter(
                doctor=user,
                date=timezone.localdate(),
                status=Appointment.Status.CONFIRMADA,
            )[:5]
            context['quick_consultation_appointment'] = Appointment.objects.filter(
                doctor=user,
                date__gte=timezone.localdate(),
                status__in=[Appointment.Status.CONFIRMADA, Appointment.Status.PENDIENTE],
            ).order_by('date', 'start_time').first()
        else:
            context['next_appointment'] = get_next_appointment_for_patient(user)
            context['doctor_profile'] = get_primary_doctor()

        return context
