from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = 'ADMIN', 'Admin / Director'
        DOCTOR = 'DOCTOR', 'Doctor'
        RECEPTIONIST = 'RECEPTIONIST', 'Receptionist / Cashier'
        LAB_TECHNICIAN = 'LAB_TECH', 'Lab Technician / Pathologist'
        PHARMACIST = 'PHARMACIST', 'Pharmacist'
        NURSE = 'NURSE', 'Nurse / Ward Staff'
        PATIENT = 'PATIENT', 'Patient'

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.ADMIN)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)

    def is_admin(self):
        return self.role == self.Role.ADMIN or self.is_superuser

    def is_doctor(self):
        return self.role == self.Role.DOCTOR

    def is_receptionist(self):
        return self.role == self.Role.RECEPTIONIST

    def is_lab_technician(self):
        return self.role == self.Role.LAB_TECHNICIAN

    def is_pharmacist(self):
        return self.role == self.Role.PHARMACIST

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.get_role_display()})"
