from django import forms
from django.forms import inlineformset_factory

from .models import ClinicalRecord, Medication


class ClinicalRecordForm(forms.ModelForm):
    class Meta:
        model = ClinicalRecord
        fields = ('symptoms', 'vital_signs', 'diagnosis', 'notes')
        widgets = {
            'symptoms': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'vital_signs': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'diagnosis': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }


class MedicationForm(forms.ModelForm):
    class Meta:
        model = Medication
        fields = ('name', 'quantity', 'dosage', 'frequency', 'duration_days', 'instructions')
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'quantity': forms.TextInput(attrs={'class': 'form-control'}),
            'dosage': forms.TextInput(attrs={'class': 'form-control'}),
            'frequency': forms.TextInput(attrs={'class': 'form-control'}),
            'duration_days': forms.NumberInput(attrs={'class': 'form-control'}),
            'instructions': forms.TextInput(attrs={'class': 'form-control'}),
        }


MedicationFormSet = inlineformset_factory(
    ClinicalRecord,
    Medication,
    form=MedicationForm,
    extra=1,
    can_delete=True,
)
