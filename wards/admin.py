from django.contrib import admin
from .models import WardType, Bed, Admission

@admin.register(WardType)
class WardTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name',)

@admin.register(Bed)
class BedAdmin(admin.ModelAdmin):
    list_display = ('bed_number', 'ward_type', 'floor', 'daily_charge', 'status')
    list_filter = ('ward_type', 'status', 'floor')
    search_fields = ('bed_number', 'description')

@admin.register(Admission)
class AdmissionAdmin(admin.ModelAdmin):
    list_display = ('admission_no', 'patient', 'bed', 'admitted_under_doctor', 'admission_date', 'status', 'total_days', 'total_bed_charge')
    list_filter = ('status', 'admission_date', 'admitted_under_doctor')
    search_fields = ('admission_no', 'patient__name', 'patient__phone', 'bed__bed_number')
    readonly_fields = ('admission_no', 'admission_date')
