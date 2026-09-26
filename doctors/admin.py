from django.contrib import admin
from .models import Specialization, Doctor, Prescription, PrescriptionMedicine

@admin.register(Specialization)
class SpecializationAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name',)

@admin.register(Doctor)
class DoctorAdmin(admin.ModelAdmin):
    list_display = ('name', 'specialization', 'designation', 'phone', 'consultation_fee', 'commission_rate_percentage', 'room_number', 'is_active')
    list_filter = ('specialization', 'is_active')
    search_fields = ('name', 'degrees', 'phone', 'bmdc_reg_no')

class PrescriptionMedicineInline(admin.TabularInline):
    model = PrescriptionMedicine
    extra = 1

@admin.register(Prescription)
class PrescriptionAdmin(admin.ModelAdmin):
    list_display = ('prescription_no', 'patient', 'doctor', 'follow_up_date', 'created_at')
    list_filter = ('doctor', 'created_at')
    search_fields = ('prescription_no', 'patient__name', 'patient__phone', 'doctor__name')
    readonly_fields = ('prescription_no', 'created_at')
    inlines = [PrescriptionMedicineInline]
