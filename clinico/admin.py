from django.contrib import admin

from .models import ClinicalRecord, Medication


class MedicationInline(admin.TabularInline):
    model = Medication
    extra = 0


@admin.register(ClinicalRecord)
class ClinicalRecordAdmin(admin.ModelAdmin):
    list_display = ('appointment', 'created_by', 'updated_at')
    inlines = [MedicationInline]
