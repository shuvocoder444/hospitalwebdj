from django.db import models
from django.conf import settings
from django.utils import timezone
import random

class TestCategory(models.Model):
    name = models.CharField(max_length=100, unique=True, help_text="e.g. Hematology, Biochemistry, Radiology, Microbiology, Serology")
    description = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name_plural = "Test Categories"

    def __str__(self):
        return self.name

class LabTest(models.Model):
    category = models.ForeignKey(TestCategory, on_delete=models.CASCADE, related_name='tests')
    test_code = models.CharField(max_length=30, unique=True, help_text="e.g. CBC, RBS, LFT, S.CREATININE, USG-WHOLE-ABDOMEN")
    name = models.CharField(max_length=200)
    specimen = models.CharField(max_length=100, default="Blood", help_text="e.g. Blood, Urine, Stool, Swab, Sputum, None")
    price = models.DecimalField(max_digits=10, decimal_places=2, help_text="Patient Charge (BDT)")
    cost = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, help_text="Lab Chemical/Internal Cost")
    delivery_time_hours = models.PositiveIntegerField(default=24, help_text="Report delivery time in hours")
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.test_code} - {self.name} (৳{self.price})"

class TestParameter(models.Model):
    test = models.ForeignKey(LabTest, on_delete=models.CASCADE, related_name='parameters')
    name = models.CharField(max_length=150, help_text="e.g. Hemoglobin, Fasting Blood Sugar, SGPT (ALT), Serum Creatinine")
    unit = models.CharField(max_length=50, blank=True, null=True, help_text="e.g. g/dL, mg/dL, U/L, %")
    reference_range = models.CharField(max_length=200, blank=True, null=True, help_text="e.g. Male: 13.5-17.5, Female: 12.0-15.5")
    order_index = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ['order_index']

    def __str__(self):
        return f"{self.test.test_code} -> {self.name} ({self.reference_range} {self.unit or ''})"

class LabOrder(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Sample Collected', 'Sample Collected'),
        ('In Progress', 'In Progress'),
        ('Completed', 'Completed (Report Ready)'),
        ('Delivered', 'Delivered to Patient'),
        ('Cancelled', 'Cancelled'),
    ]

    order_no = models.CharField(max_length=35, unique=True, editable=False)
    patient = models.ForeignKey('patients.Patient', on_delete=models.CASCADE, related_name='lab_orders')
    referred_by_doctor = models.ForeignKey('doctors.Doctor', on_delete=models.SET_NULL, null=True, blank=True, related_name='referred_lab_orders')
    external_doctor_name = models.CharField(max_length=150, blank=True, null=True, help_text="If referred by an outside doctor")
    
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    payable_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    paid_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    due_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    
    doctor_commission_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='Pending')
    sample_collected_at = models.DateTimeField(blank=True, null=True)
    report_ready_at = models.DateTimeField(blank=True, null=True)
    delivered_at = models.DateTimeField(blank=True, null=True)
    
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.order_no:
            date_str = timezone.now().strftime('%Y%m%d')
            rand_code = f"{random.randint(1000, 9999)}"
            self.order_no = f"LAB-{date_str}-{rand_code}"
            while LabOrder.objects.filter(order_no=self.order_no).exists():
                rand_code = f"{random.randint(1000, 9999)}"
                self.order_no = f"LAB-{date_str}-{rand_code}"
        
        self.payable_amount = max(0, self.total_amount - self.discount_amount)
        self.due_amount = max(0, self.payable_amount - self.paid_amount)
        
        # Calculate doctor referral commission if doctor is linked
        if self.referred_by_doctor and self.referred_by_doctor.commission_rate_percentage:
            from decimal import Decimal
            comm_rate = Decimal(str(self.referred_by_doctor.commission_rate_percentage))
            self.doctor_commission_amount = (self.payable_amount * comm_rate) / Decimal('100.00')
            
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.order_no} - {self.patient.name} (৳{self.payable_amount})"

class LabOrderItem(models.Model):
    order = models.ForeignKey(LabOrder, on_delete=models.CASCADE, related_name='items')
    test = models.ForeignKey(LabTest, on_delete=models.CASCADE)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    sample_collected = models.BooleanField(default=False)
    report_completed = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.order.order_no} - {self.test.name}"

class LabResult(models.Model):
    order_item = models.ForeignKey(LabOrderItem, on_delete=models.CASCADE, related_name='results')
    parameter = models.ForeignKey(TestParameter, on_delete=models.CASCADE)
    result_value = models.CharField(max_length=255, blank=True, null=True)
    flag = models.CharField(max_length=20, blank=True, null=True, help_text="Normal / High / Low / Positive / Negative")
    remarks = models.TextField(blank=True, null=True)
    
    tested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='tested_results')
    verified_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='verified_results')
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.order_item.test.test_code}: {self.parameter.name} = {self.result_value}"
