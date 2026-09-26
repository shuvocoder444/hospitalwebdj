from django.db import models
from django.conf import settings
from django.utils import timezone
import random

class Appointment(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Confirmed', 'Confirmed'),
        ('Completed', 'Completed'),
        ('Cancelled', 'Cancelled'),
    ]

    PAYMENT_CHOICES = [
        ('Unpaid', 'Unpaid'),
        ('Paid', 'Paid'),
    ]

    appointment_no = models.CharField(max_length=30, unique=True, editable=False)
    patient = models.ForeignKey('patients.Patient', on_delete=models.CASCADE, related_name='appointments')
    doctor = models.ForeignKey('doctors.Doctor', on_delete=models.CASCADE, related_name='appointments')
    
    appointment_date = models.DateField(default=timezone.now)
    serial_no = models.PositiveIntegerField(default=1)
    time_slot = models.CharField(max_length=50, blank=True, null=True, help_text="e.g. 05:30 PM")
    
    fee_amount = models.DecimalField(max_digits=10, decimal_places=2, default=500.00)
    payment_status = models.CharField(max_length=15, choices=PAYMENT_CHOICES, default='Unpaid')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    
    notes = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-appointment_date', 'serial_no']

    def save(self, *args, **kwargs):
        if not self.appointment_no:
            date_str = timezone.now().strftime('%Y%m%d')
            rand_code = f"{random.randint(1000, 9999)}"
            self.appointment_no = f"APT-{date_str}-{rand_code}"
            while Appointment.objects.filter(appointment_no=self.appointment_no).exists():
                rand_code = f"{random.randint(1000, 9999)}"
                self.appointment_no = f"APT-{date_str}-{rand_code}"
        
        if not self.serial_no or self.serial_no == 1:
            existing_count = Appointment.objects.filter(doctor=self.doctor, appointment_date=self.appointment_date).count()
            if not self.pk:
                self.serial_no = existing_count + 1

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.appointment_no} - Serial #{self.serial_no} - {self.patient.name} with {self.doctor.name}"
