from django.urls import path

from .views import (
    AppointmentPrintView,
    DoctorAppointmentDecisionView,
    DoctorAppointmentReviewView,
    DoctorBusinessHoursDeactivateView,
    DoctorCalendarView,
    DoctorPendingAppointmentListView,
    DoctorScheduleConfigView,
    PatientAppointmentCancelView,
    PatientAppointmentCreateView,
    PatientAppointmentRequestView,
    PatientNextAppointmentView,
)

app_name = 'citas'

urlpatterns = [
    path('solicitar/', PatientAppointmentRequestView.as_view(), name='patient-request'),
    path('registrar/', PatientAppointmentCreateView.as_view(), name='patient-create'),
    path('<int:pk>/imprimir/', AppointmentPrintView.as_view(), name='appointment-print'),
    path('proxima/', PatientNextAppointmentView.as_view(), name='patient-next'),
    path('cancelar/', PatientAppointmentCancelView.as_view(), name='patient-cancel'),
    path('medico/agenda/', DoctorScheduleConfigView.as_view(), name='doctor-schedule'),
    path('medico/agenda/<int:pk>/desactivar/', DoctorBusinessHoursDeactivateView.as_view(), name='doctor-schedule-disable'),
    path('medico/solicitudes/', DoctorPendingAppointmentListView.as_view(), name='doctor-pending'),
    path('medico/solicitudes/<int:pk>/', DoctorAppointmentReviewView.as_view(), name='doctor-review'),
    path('medico/solicitudes/<int:pk>/decision/', DoctorAppointmentDecisionView.as_view(), name='doctor-decision'),
    path('medico/calendario/', DoctorCalendarView.as_view(), name='doctor-calendar'),
]
