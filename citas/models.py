from datetime import datetime

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class ScheduleSettings(models.Model):
    doctor = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='schedule_settings',
        limit_choices_to={'role': 'medico'},
    )
    consultation_duration = models.PositiveIntegerField(default=50)

    class Meta:
        verbose_name = 'Configuracion de agenda'
        verbose_name_plural = 'Configuraciones de agenda'

    def __str__(self):
        return f'Agenda de {self.doctor}'


class BusinessHours(models.Model):
    class Weekday(models.IntegerChoices):
        LUNES = 0, 'Lunes'
        MARTES = 1, 'Martes'
        MIERCOLES = 2, 'Miercoles'
        JUEVES = 3, 'Jueves'
        VIERNES = 4, 'Viernes'
        SABADO = 5, 'Sabado'
        DOMINGO = 6, 'Domingo'

    settings = models.ForeignKey(ScheduleSettings, on_delete=models.CASCADE, related_name='business_hours')
    weekday = models.PositiveSmallIntegerField(choices=Weekday.choices)
    start_time = models.TimeField()
    end_time = models.TimeField()
    active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Horario laboral'
        verbose_name_plural = 'Horarios laborales'
        ordering = ('weekday', 'start_time')
        constraints = [
            models.UniqueConstraint(fields=('settings', 'weekday'), name='unique_schedule_weekday'),
        ]

    def clean(self):
        if self.start_time >= self.end_time:
            raise ValidationError('La hora de inicio debe ser menor que la hora de cierre.')

    def __str__(self):
        return f'{self.get_weekday_display()} {self.start_time} - {self.end_time}'


class Appointment(models.Model):
    class Status(models.TextChoices):
        PENDIENTE = 'pendiente', 'Pendiente'
        CONFIRMADA = 'confirmada', 'Confirmada'
        CANCELADA_PACIENTE = 'cancelada_paciente', 'Cancelada por paciente'
        CANCELADA_MEDICO = 'cancelada_medico', 'Cancelada por medico'
        ATENDIDA = 'atendida', 'Atendida'

    patient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='patient_appointments',
        limit_choices_to={'role': 'paciente'},
    )
    doctor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='doctor_appointments',
        limit_choices_to={'role': 'medico'},
    )
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    reason = models.CharField(max_length=255, blank=True)
    doctor_cancellation_reason = models.TextField(blank=True)
    status = models.CharField(max_length=30, choices=Status.choices, default=Status.PENDIENTE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Cita'
        verbose_name_plural = 'Citas'
        ordering = ('date', 'start_time')
        constraints = [
            models.UniqueConstraint(fields=('doctor', 'date', 'start_time'), name='unique_doctor_timeslot'),
        ]

    def clean(self):
        if self.start_time >= self.end_time:
            raise ValidationError('La hora inicial de la cita debe ser menor que la hora final.')

    @property
    def starts_at(self):
        return timezone.make_aware(
            datetime.combine(self.date, self.start_time),
            timezone.get_current_timezone(),
        )

    @property
    def ends_at(self):
        return timezone.make_aware(
            datetime.combine(self.date, self.end_time),
            timezone.get_current_timezone(),
        )

    @property
    def is_in_progress(self):
        current_time = timezone.localtime()
        return self.status == self.Status.CONFIRMADA and self.starts_at <= current_time < self.ends_at

    @property
    def can_be_cancelled(self):
        return self.status in (self.Status.PENDIENTE, self.Status.CONFIRMADA) and timezone.localtime() < self.starts_at

    def __str__(self):
        return f'{self.patient} - {self.date} {self.start_time}'
