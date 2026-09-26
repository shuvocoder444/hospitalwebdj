from django.contrib import admin
from .models import MedicineCategory, GenericName, Medicine, MedicineBatch, PharmacySale, PharmacySaleItem

@admin.register(MedicineCategory)
class MedicineCategoryAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

@admin.register(GenericName)
class GenericNameAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

class MedicineBatchInline(admin.TabularInline):
    model = MedicineBatch
    extra = 1

@admin.register(Medicine)
class MedicineAdmin(admin.ModelAdmin):
    list_display = ('brand_name', 'generic', 'category', 'strength', 'company_name', 'unit_price', 'total_stock', 'is_active')
    list_filter = ('category', 'is_active', 'company_name')
    search_fields = ('brand_name', 'generic__name', 'company_name')
    inlines = [MedicineBatchInline]

@admin.register(MedicineBatch)
class MedicineBatchAdmin(admin.ModelAdmin):
    list_display = ('medicine', 'batch_number', 'expiry_date', 'quantity_in_stock', 'selling_price_per_unit')
    list_filter = ('expiry_date',)
    search_fields = ('medicine__brand_name', 'batch_number')

class PharmacySaleItemInline(admin.TabularInline):
    model = PharmacySaleItem
    extra = 1

@admin.register(PharmacySale)
class PharmacySaleAdmin(admin.ModelAdmin):
    list_display = ('invoice_no', 'customer_name', 'customer_phone', 'net_amount', 'paid_amount', 'due_amount', 'sold_by', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('invoice_no', 'customer_name', 'customer_phone')
    readonly_fields = ('invoice_no', 'net_amount', 'due_amount', 'created_at')
    inlines = [PharmacySaleItemInline]
