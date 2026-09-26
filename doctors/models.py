from django.db import models
from django.conf import settings
from django.utils import timezone
import random

class Specialization(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name

class Doctor(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='doctor_profile')
    name = models.CharField(max_length=150)
    specialization = models.ForeignKey(Specialization, on_delete=models.SET_NULL, null=True, related_name='doctors')
    designation = models.CharField(max_length=150, help_text="e.g. Professor & Head of Dept / Senior Consultant")
    degrees = models.CharField(max_length=255, help_text="e.g. MBBS, FCPS (Medicine), MD")
    bmdc_reg_no = models.CharField(max_length=50, blank=True, null=True, verbose_name="BMDC Reg No")
    
    phone = models.CharField(max_length=20)
    email = models.EmailField(blank=True, null=True)
    
    consultation_fee = models.DecimalField(max_digits=10, decimal_places=2, default=500.00)
    follow_up_fee = models.DecimalField(max_digits=10, decimal_places=2, default=300.00)
    commission_rate_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=10.00, help_text="Diagnostic referral commission %")
    
    room_number = models.CharField(max_length=50, default="Room-101")
    available_days = models.CharField(max_length=150, default="Sat, Sun, Mon, Tue, Wed, Thu")
    visiting_hours = models.CharField(max_length=100, default="5:00 PM - 9:00 PM")
    photo = models.ImageField(upload_to='doctors/', blank=True, null=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        spec = self.specialization.name if self.specialization else "General"
        return f"Dr. {self.name} ({spec})"

class Prescription(models.Model):
    prescription_no = models.CharField(max_length=30, unique=True, editable=False)
    patient = models.ForeignKey('patients.Patient', on_delete=models.CASCADE, related_name='prescriptions')
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name='prescriptions')
    
    chief_complaints = models.TextField(blank=True, null=True, help_text="Chief complaints / Symptoms")
    history_and_findings = models.TextField(blank=True, null=True, help_text="On Examination (O/E), BP, Pulse, Weight, etc.")
    diagnosis = models.TextField(blank=True, null=True, help_text="Provisional / Final Diagnosis")
    tests_advised = models.TextField(blank=True, null=True, help_text="Investigation / Lab Tests Advised")
    advice = models.TextField(blank=True, null=True, help_text="General Advice / Diet / Lifestyle")
    follow_up_date = models.DateField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.prescription_no:
            date_str = timezone.now().strftime('%Y%m%d')
            rand_code = f"{random.randint(1000, 9999)}"
            self.prescription_no = f"RX-{date_str}-{rand_code}"
            while Prescription.objects.filter(prescription_no=self.prescription_no).exists():
                rand_code = f"{random.randint(1000, 9999)}"
                self.prescription_no = f"RX-{date_str}-{rand_code}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.prescription_no} - {self.patient.name} by {self.doctor.name}"

class PrescriptionMedicine(models.Model):
    prescription = models.ForeignKey(Prescription, on_delete=models.CASCADE, related_name='medicines')
    medicine_name = models.CharField(max_length=200, help_text="e.g. Tab. Napa Extra 500mg")
    dosage = models.CharField(max_length=100, help_text="e.g. 1+0+1, 1+1+1, 0+0+1")
    duration = models.CharField(max_length=100, help_text="e.g. 5 days, 1 month, Continue")
    instruction = models.CharField(max_length=150, blank=True, null=True, help_text="e.g. After meal / Before meal")

    def __str__(self):
        return f"{self.medicine_name} ({self.dosage}) - {self.duration}"
