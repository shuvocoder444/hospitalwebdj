from django.db import models
from django.utils import timezone
import random

class Patient(models.Model):
    GENDER_CHOICES = [
        ('Male', 'Male'),
        ('Female', 'Female'),
        ('Other', 'Other'),
    ]
    
    BLOOD_GROUP_CHOICES = [
        ('A+', 'A+'), ('A-', 'A-'),
        ('B+', 'B+'), ('B-', 'B-'),
        ('AB+', 'AB+'), ('AB-', 'AB-'),
        ('O+', 'O+'), ('O-', 'O-'),
        ('Unknown', 'Unknown'),
    ]

    patient_id = models.CharField(max_length=30, unique=True, editable=False)
    name = models.CharField(max_length=150)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, default='Male')
    age_years = models.PositiveIntegerField(default=0)
    age_months = models.PositiveIntegerField(default=0)
    date_of_birth = models.DateField(blank=True, null=True)
    blood_group = models.CharField(max_length=10, choices=BLOOD_GROUP_CHOICES, default='Unknown')
    
    phone = models.CharField(max_length=20)
    email = models.EmailField(blank=True, null=True)
    nid_or_birth_cert = models.CharField(max_length=50, blank=True, null=True, verbose_name="NID / Birth Certificate")
    address = models.TextField(blank=True, null=True)
    
    emergency_contact_name = models.CharField(max_length=100, blank=True, null=True)
    emergency_contact_phone = models.CharField(max_length=20, blank=True, null=True)
    emergency_contact_relation = models.CharField(max_length=50, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.patient_id:
            last_patient = Patient.objects.exclude(patient_id='').order_by('-id').first()
            next_num = (last_patient.id + 1) if last_patient else 1
            new_id = f"P{next_num:06d}"
            while Patient.objects.filter(patient_id=new_id).exists():
                next_num += 1
                new_id = f"P{next_num:06d}"
            self.patient_id = new_id
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.patient_id} - {self.name} ({self.phone})"
