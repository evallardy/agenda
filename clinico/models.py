from django.conf import settings
from django.db import models


class ClinicalRecord(models.Model):
    appointment = models.OneToOneField('citas.Appointment', on_delete=models.CASCADE, related_name='clinical_record')
    symptoms = models.TextField('sintomas')
    vital_signs = models.TextField('signos vitales')
    diagnosis = models.TextField('diagnostico', blank=True)
    notes = models.TextField('notas adicionales', blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='clinical_records')
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Cardex clinico'
        verbose_name_plural = 'Cardex clinicos'

    def __str__(self):
        return f'Cardex de {self.appointment.patient}'


class Medication(models.Model):
    clinical_record = models.ForeignKey(ClinicalRecord, on_delete=models.CASCADE, related_name='medications')
    name = models.CharField('medicamento', max_length=150)
    quantity = models.CharField('cantidad', max_length=100)
    dosage = models.CharField('como se toma', max_length=150)
    frequency = models.CharField('frecuencia', max_length=150)
    duration_days = models.PositiveIntegerField('duracion en dias')
    instructions = models.CharField('indicaciones adicionales', max_length=255, blank=True)

    class Meta:
        verbose_name = 'Medicamento recetado'
        verbose_name_plural = 'Medicamentos recetados'

    def __str__(self):
        return self.name
