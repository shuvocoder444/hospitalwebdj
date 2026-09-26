from django.db import models
from django.conf import settings
from django.utils import timezone
import random

class Invoice(models.Model):
    BILL_TYPES = [
        ('OPD', 'OPD Doctor Consultation'),
        ('IPD', 'IPD Inpatient Hospitalization'),
        ('DIAGNOSTIC', 'Diagnostic / Pathology Test'),
        ('PHARMACY', 'Pharmacy Purchase'),
        ('COMBINED', 'Combined / Package Bill'),
    ]

    PAYMENT_STATUS = [
        ('Paid', 'Paid'),
        ('Partial', 'Partial Paid'),
        ('Unpaid', 'Unpaid (Due)'),
    ]

    invoice_no = models.CharField(max_length=35, unique=True, editable=False)
    patient = models.ForeignKey('patients.Patient', on_delete=models.CASCADE, related_name='invoices')
    bill_type = models.CharField(max_length=20, choices=BILL_TYPES, default='GENERAL')
    
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    payable_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    paid_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    due_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    
    payment_status = models.CharField(max_length=15, choices=PAYMENT_STATUS, default='Unpaid')
    
    remarks = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.invoice_no:
            date_str = timezone.now().strftime('%Y%m%d')
            rand_code = f"{random.randint(1000, 9999)}"
            self.invoice_no = f"INV-{date_str}-{rand_code}"
            while Invoice.objects.filter(invoice_no=self.invoice_no).exists():
                rand_code = f"{random.randint(1000, 9999)}"
                self.invoice_no = f"INV-{date_str}-{rand_code}"
        
        self.payable_amount = max(0, self.total_amount - self.discount_amount)
        self.due_amount = max(0, self.payable_amount - self.paid_amount)
        
        if self.paid_amount >= self.payable_amount and self.payable_amount > 0:
            self.payment_status = 'Paid'
        elif self.paid_amount > 0:
            self.payment_status = 'Partial'
        else:
            self.payment_status = 'Unpaid'
            
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.invoice_no} - {self.patient.name} - Payable: ৳{self.payable_amount} ({self.payment_status})"

class InvoiceItem(models.Model):
    ITEM_TYPES = [
        ('Doctor Fee', 'Doctor Consultation Fee'),
        ('Lab Test', 'Diagnostic / Lab Test'),
        ('Bed Charge', 'Bed / Cabin Charge'),
        ('Medicine', 'Medicine / Pharmacy'),
        ('Procedure / OT', 'Surgery / Procedure / OT Charge'),
        ('Nursing', 'Nursing & Service Charge'),
        ('Other', 'Other Service'),
    ]

    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='items')
    item_type = models.CharField(max_length=30, choices=ITEM_TYPES, default='Other')
    description = models.CharField(max_length=255)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)

    def save(self, *args, **kwargs):
        self.subtotal = self.quantity * self.unit_price
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.description} ({self.quantity} x ৳{self.unit_price} = ৳{self.subtotal})"

class PaymentTransaction(models.Model):
    PAYMENT_METHODS = [
        ('Cash', 'Cash Counter'),
        ('bKash', 'bKash (Mobile Banking)'),
        ('Nagad', 'Nagad (Mobile Banking)'),
        ('Rocket', 'Rocket (DBBL)'),
        ('Card', 'Credit / Debit Card (POS)'),
        ('Bank', 'Bank Transfer / Cheque'),
    ]

    transaction_id = models.CharField(max_length=35, unique=True, editable=False)
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='payments')
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS, default='Cash')
    transaction_reference = models.CharField(max_length=100, blank=True, null=True, help_text="e.g. bKash TrxID / Card Slip No")
    
    received_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.transaction_id:
            date_str = timezone.now().strftime('%Y%m%d')
            rand_code = f"{random.randint(1000, 9999)}"
            self.transaction_id = f"TRX-{date_str}-{rand_code}"
            while PaymentTransaction.objects.filter(transaction_id=self.transaction_id).exists():
                rand_code = f"{random.randint(1000, 9999)}"
                self.transaction_id = f"TRX-{date_str}-{rand_code}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.transaction_id}: ৳{self.amount_paid} via {self.payment_method}"

# ==================== EXPENSE & ACCOUNTS ====================

class ExpenseCategory(models.Model):
    name = models.CharField(max_length=100, unique=True, help_text="e.g. Staff Salary, Electricity & Utility, Medical Supplies, Doctor Commission Payout, Equipment Maintenance, Rent, Marketing")
    description = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name_plural = "Expense Categories"

    def __str__(self):
        return self.name

class Expense(models.Model):
    PAYMENT_METHODS = [
        ('Cash', 'Cash (ক্যাশ)'),
        ('Bank', 'Bank Transfer / Cheque'),
        ('bKash', 'bKash'),
        ('Nagad', 'Nagad'),
        ('Card', 'Credit/Debit Card'),
    ]

    expense_no = models.CharField(max_length=35, unique=True, editable=False)
    category = models.ForeignKey(ExpenseCategory, on_delete=models.PROTECT, related_name='expenses')
    title = models.CharField(max_length=200, help_text="e.g. September Staff Salary, Generator Diesel, Lab Reagent purchase")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    expense_date = models.DateField(default=timezone.now)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS, default='Cash')
    paid_to = models.CharField(max_length=150, blank=True, null=True, help_text="Name of vendor / employee / payee")
    
    voucher_receipt = models.FileField(upload_to='vouchers/', blank=True, null=True)
    remarks = models.TextField(blank=True, null=True)
    
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-expense_date', '-created_at']

    def save(self, *args, **kwargs):
        if not self.expense_no:
            date_str = timezone.now().strftime('%Y%m%d')
            rand_code = f"{random.randint(1000, 9999)}"
            self.expense_no = f"EXP-{date_str}-{rand_code}"
            while Expense.objects.filter(expense_no=self.expense_no).exists():
                rand_code = f"{random.randint(1000, 9999)}"
                self.expense_no = f"EXP-{date_str}-{rand_code}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.expense_no} - {self.title} (৳{self.amount})"

# ==================== HOSPITAL GLOBAL SETTINGS & CUSTOMIZATION ====================

class HospitalSetting(models.Model):
    SMS_PROVIDERS = [
        ('BulkSMSBD', 'BulkSMSBD (Bangladesh)'),
        ('Greenweb', 'Greenweb SMS Gateway'),
        ('SSLWireless', 'SSL Wireless SMS Gateway'),
        ('Custom', 'Custom HTTP SMS API URL'),
    ]

    hospital_name = models.CharField(max_length=200, default="WebKoders Healthcare & Hospital BD")
    hospital_tagline = models.CharField(max_length=255, default="Modern Healthcare & Diagnostic Center")
    reg_license_no = models.CharField(max_length=100, default="DGHS-REG-10492/2026", blank=True, null=True)
    
    phone = models.CharField(max_length=50, default="01826027203")
    hotline = models.CharField(max_length=50, default="+880 1711-122233", blank=True, null=True)
    email = models.EmailField(default="hospitalsoftwarebd@gmail.com")
    website = models.CharField(max_length=150, default="www.hospitalsoftwarebd.com")
    address = models.TextField(default="437 Shahid Jahanara Imam Road, New Elephant Road, Dhaka-1205")
    currency_symbol = models.CharField(max_length=10, default="৳")
    
    # Visual Assets & Printing
    logo = models.ImageField(upload_to='settings/', blank=True, null=True)
    favicon = models.ImageField(upload_to='settings/', blank=True, null=True)
    pdf_header_banner = models.ImageField(upload_to='settings/', blank=True, null=True, help_text="Banner letterhead for prescription pad & lab reports")
    authorized_signature_seal = models.ImageField(upload_to='settings/', blank=True, null=True, help_text="Official Director/Doctor seal & signature image")

    # Document Footers
    invoice_footer_note = models.TextField(default="* Payment is non-refundable. Please keep this money receipt for future reference.", blank=True)
    lab_report_footer_note = models.TextField(default="* This is an authorized digital diagnostic laboratory report.", blank=True)
    prescription_footer_note = models.TextField(default="* Take medicines as advised. For emergency, visit our casualty department.", blank=True)

    # SMS Gateway Integration
    sms_enabled = models.BooleanField(default=False)
    sms_provider = models.CharField(max_length=30, choices=SMS_PROVIDERS, default='BulkSMSBD')
    sms_api_key = models.CharField(max_length=255, blank=True, null=True)
    sms_sender_id = models.CharField(max_length=50, blank=True, null=True)
    sms_custom_url = models.CharField(max_length=255, blank=True, null=True)
    
    sms_on_registration = models.BooleanField(default=True)
    sms_on_appointment = models.BooleanField(default=True)
    sms_on_lab_ready = models.BooleanField(default=True)

    updated_at = models.DateTimeField(auto_now=True)

    @classmethod
    def get_settings(cls):
        obj, _ = cls.objects.get_or_create(id=1)
        return obj

    def __str__(self):
        return self.hospital_name
