from django import forms
from django.utils import timezone

from .models import Appointment, BusinessHours, ScheduleSettings


class AppointmentDateForm(forms.Form):
    appointment_date = forms.DateField(
        label='Dia deseado',
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
    )
    reason = forms.CharField(
        label='Motivo de consulta',
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Opcional'}),
    )

    def clean_appointment_date(self):
        appointment_date = self.cleaned_data['appointment_date']
        if appointment_date < timezone.localdate():
            raise forms.ValidationError('Debes elegir una fecha actual o futura.')
        return appointment_date


class ScheduleBatchForm(forms.Form):
    consultation_duration = forms.IntegerField(
        label='Duracion de consulta (minutos)',
        min_value=10,
        widget=forms.NumberInput(attrs={'class': 'form-control'}),
    )
    weekdays = forms.MultipleChoiceField(
        label='Dias a configurar',
        choices=BusinessHours.Weekday.choices,
        widget=forms.CheckboxSelectMultiple,
    )
    start_time = forms.TimeField(
        label='Hora de apertura',
        widget=forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
    )
    end_time = forms.TimeField(
        label='Hora de cierre',
        widget=forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
    )

    def clean(self):
        cleaned_data = super().clean()
        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')
        weekdays = cleaned_data.get('weekdays')

        if start_time and end_time and start_time >= end_time:
            raise forms.ValidationError('La hora de apertura debe ser menor que la hora de cierre.')
        if not weekdays:
            raise forms.ValidationError('Selecciona al menos un dia para aplicar el horario.')
        return cleaned_data

    def save(self, doctor):
        settings, _ = ScheduleSettings.objects.get_or_create(doctor=doctor)
        settings.consultation_duration = self.cleaned_data['consultation_duration']
        settings.save()

        for weekday in self.cleaned_data['weekdays']:
            BusinessHours.objects.update_or_create(
                settings=settings,
                weekday=int(weekday),
                defaults={
                    'start_time': self.cleaned_data['start_time'],
                    'end_time': self.cleaned_data['end_time'],
                    'active': True,
                },
            )

        return settings


class AppointmentDecisionForm(forms.ModelForm):
    class Meta:
        model = Appointment
        fields = ('reason',)
