from django.contrib import admin

from .models import Appointment, BusinessHours, ScheduleSettings


class BusinessHoursInline(admin.TabularInline):
    model = BusinessHours
    extra = 0


@admin.register(ScheduleSettings)
class ScheduleSettingsAdmin(admin.ModelAdmin):
    list_display = ('doctor', 'consultation_duration')
    inlines = [BusinessHoursInline]


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ('patient', 'doctor', 'date', 'start_time', 'end_time', 'status')
    list_filter = ('status', 'date')
    search_fields = ('patient__full_name', 'doctor__full_name', 'patient__email')
