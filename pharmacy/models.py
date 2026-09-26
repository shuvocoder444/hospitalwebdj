from django.db import models
from django.conf import settings
from django.utils import timezone
import random

class MedicineCategory(models.Model):
    name = models.CharField(max_length=100, unique=True, help_text="e.g. Tablet, Capsule, Syrup, Injection, Ointment, Suspension, Drops")

    class Meta:
        verbose_name_plural = "Medicine Categories"

    def __str__(self):
        return self.name

class GenericName(models.Model):
    name = models.CharField(max_length=150, unique=True, help_text="e.g. Paracetamol, Esomeprazole, Azithromycin, Cefixime")

    def __str__(self):
        return self.name

class Medicine(models.Model):
    brand_name = models.CharField(max_length=150, db_index=True, help_text="e.g. Napa Extra, Maxpro, Seclo, Zithrox")
    generic = models.ForeignKey(GenericName, on_delete=models.SET_NULL, null=True, related_name='medicines')
    category = models.ForeignKey(MedicineCategory, on_delete=models.SET_NULL, null=True, related_name='medicines')
    strength = models.CharField(max_length=50, blank=True, null=True, help_text="e.g. 500mg, 20mg, 1gm, 5ml/100ml")
    company_name = models.CharField(max_length=150, db_index=True, help_text="e.g. Square Pharmaceuticals, Beximco, Incepta, Renata")
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, help_text="MRP per piece/strip/bottle")
    reorder_level = models.PositiveIntegerField(default=50, help_text="Alert when total stock falls below this quantity")
    is_active = models.BooleanField(default=True, db_index=True)

    @property
    def total_stock(self):
        batches = self.batches.filter(expiry_date__gte=timezone.now().date())
        return sum(b.quantity_in_stock for b in batches)

    def __str__(self):
        return f"{self.brand_name} {self.strength or ''} ({self.company_name})"

class MedicineBatch(models.Model):
    medicine = models.ForeignKey(Medicine, on_delete=models.CASCADE, related_name='batches')
    batch_number = models.CharField(max_length=50)
    expiry_date = models.DateField()
    purchase_cost_per_unit = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    selling_price_per_unit = models.DecimalField(max_digits=10, decimal_places=2)
    quantity_in_stock = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Medicine Batches"
        ordering = ['expiry_date']

    def is_expired(self):
        return self.expiry_date < timezone.now().date()

    def __str__(self):
        return f"{self.medicine.brand_name} [Batch: {self.batch_number}] - Stock: {self.quantity_in_stock} (Exp: {self.expiry_date})"

class PharmacySale(models.Model):
    invoice_no = models.CharField(max_length=35, unique=True, editable=False)
    patient = models.ForeignKey('patients.Patient', on_delete=models.SET_NULL, null=True, blank=True, related_name='pharmacy_purchases')
    customer_name = models.CharField(max_length=150, blank=True, null=True)
    customer_phone = models.CharField(max_length=20, blank=True, null=True)
    
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    net_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    paid_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    due_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    
    sold_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.invoice_no:
            date_str = timezone.now().strftime('%Y%m%d')
            rand_code = f"{random.randint(1000, 9999)}"
            self.invoice_no = f"PHM-{date_str}-{rand_code}"
            while PharmacySale.objects.filter(invoice_no=self.invoice_no).exists():
                rand_code = f"{random.randint(1000, 9999)}"
                self.invoice_no = f"PHM-{date_str}-{rand_code}"
        
        self.net_amount = max(0, self.total_amount - self.discount_amount)
        self.due_amount = max(0, self.net_amount - self.paid_amount)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.invoice_no} - ৳{self.net_amount}"

class PharmacySaleItem(models.Model):
    sale = models.ForeignKey(PharmacySale, on_delete=models.CASCADE, related_name='items')
    batch = models.ForeignKey(MedicineBatch, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)

    def save(self, *args, **kwargs):
        self.subtotal = self.quantity * self.unit_price
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.batch.medicine.brand_name} x {self.quantity} = ৳{self.subtotal}"
