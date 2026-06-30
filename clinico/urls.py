from django.urls import path

from .views import (
    ClinicalPrescriptionPdfView,
    ClinicalPrescriptionPrintView,
    ClinicalRecordUpdateView,
    DoctorPatientSearchView,
    PatientClinicalHistoryView,
)

app_name = 'clinico'

urlpatterns = [
    path('pacientes/', DoctorPatientSearchView.as_view(), name='patient-search'),
    path('pacientes/<int:pk>/historial/', PatientClinicalHistoryView.as_view(), name='patient-history'),
    path('cita/<int:pk>/cardex/', ClinicalRecordUpdateView.as_view(), name='record-update'),
    path('cita/<int:pk>/receta/', ClinicalPrescriptionPrintView.as_view(), name='prescription-print'),
    path('cita/<int:pk>/receta/pdf/', ClinicalPrescriptionPdfView.as_view(), name='prescription-pdf'),
]
