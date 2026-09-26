from django.db import models
from django.conf import settings
from django.utils import timezone
import random

class WardType(models.Model):
    name = models.CharField(max_length=100, unique=True, help_text="e.g. General Ward (Male), General Ward (Female), AC Cabin, Non-AC Cabin, VIP Suite, ICU, CCU, NICU")
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name

class Bed(models.Model):
    STATUS_CHOICES = [
        ('Available', 'Available'),
        ('Occupied', 'Occupied'),
        ('Cleaning', 'Cleaning / Sanitizing'),
        ('Maintenance', 'Maintenance'),
    ]

    bed_number = models.CharField(max_length=50, unique=True, help_text="e.g. Bed-101, Cabin-204, ICU-05")
    ward_type = models.ForeignKey(WardType, on_delete=models.CASCADE, related_name='beds')
    floor = models.CharField(max_length=50, default="1st Floor")
    daily_charge = models.DecimalField(max_digits=10, decimal_places=2, help_text="Charge per 24 hours (BDT)")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Available')
    description = models.CharField(max_length=200, blank=True, null=True, help_text="e.g. Attached Bath, AC, TV")

    def __str__(self):
        return f"{self.bed_number} ({self.ward_type.name}) - ৳{self.daily_charge}/day [{self.status}]"

class Admission(models.Model):
    STATUS_CHOICES = [
        ('Admitted', 'Currently Admitted'),
        ('Discharged', 'Discharged'),
        ('Transferred', 'Transferred'),
    ]

    admission_no = models.CharField(max_length=35, unique=True, editable=False)
    patient = models.ForeignKey('patients.Patient', on_delete=models.CASCADE, related_name='admissions')
    bed = models.ForeignKey(Bed, on_delete=models.CASCADE, related_name='admissions')
    admitted_under_doctor = models.ForeignKey('doctors.Doctor', on_delete=models.SET_NULL, null=True, related_name='admitted_patients')
    
    admission_date = models.DateTimeField(default=timezone.now)
    discharge_date = models.DateTimeField(blank=True, null=True)
    
    initial_deposit = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    reason_for_admission = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Admitted')
    
    discharge_summary = models.TextField(blank=True, null=True)
    discharge_advice = models.TextField(blank=True, null=True)
    
    admitted_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.admission_no:
            date_str = timezone.now().strftime('%Y%m%d')
            rand_code = f"{random.randint(1000, 9999)}"
            self.admission_no = f"ADM-{date_str}-{rand_code}"
            while Admission.objects.filter(admission_no=self.admission_no).exists():
                rand_code = f"{random.randint(1000, 9999)}"
                self.admission_no = f"ADM-{date_str}-{rand_code}"
        
        # Automatically update bed status
        if self.status == 'Admitted':
            self.bed.status = 'Occupied'
            self.bed.save()
        elif self.status == 'Discharged':
            self.bed.status = 'Available'
            self.bed.save()
            
        super().save(*args, **kwargs)

    @property
    def total_days(self):
        end_time = self.discharge_date or timezone.now()
        duration = end_time - self.admission_date
        days = duration.days
        if duration.seconds > 3600 * 4: # If stayed more than 4 extra hours, count +1 day
            days += 1
        return max(1, days)

    @property
    def total_bed_charge(self):
        return self.total_days * self.bed.daily_charge

    def __str__(self):
        return f"{self.admission_no} - {self.patient.name} ({self.bed.bed_number})"
