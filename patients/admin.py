from django.contrib import admin
from .models import Patient

@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ('patient_id', 'name', 'gender', 'age_years', 'blood_group', 'phone', 'created_at')
    list_filter = ('gender', 'blood_group', 'created_at')
    search_fields = ('patient_id', 'name', 'phone', 'nid_or_birth_cert', 'emergency_contact_phone')
    readonly_fields = ('patient_id', 'created_at', 'updated_at')
