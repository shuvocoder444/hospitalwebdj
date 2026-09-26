from django.contrib import admin
from .models import Invoice, InvoiceItem, PaymentTransaction, ExpenseCategory, Expense, HospitalSetting

class InvoiceItemInline(admin.TabularInline):
    model = InvoiceItem
    extra = 1

class PaymentTransactionInline(admin.TabularInline):
    model = PaymentTransaction
    extra = 1

@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ('invoice_no', 'patient', 'bill_type', 'total_amount', 'discount_amount', 'payable_amount', 'paid_amount', 'due_amount', 'payment_status', 'created_at')
    list_filter = ('bill_type', 'payment_status', 'created_at')
    search_fields = ('invoice_no', 'patient__name', 'patient__phone')
    readonly_fields = ('invoice_no', 'payable_amount', 'due_amount', 'created_at', 'updated_at')
    inlines = [InvoiceItemInline, PaymentTransactionInline]

@admin.register(PaymentTransaction)
class PaymentTransactionAdmin(admin.ModelAdmin):
    list_display = ('transaction_id', 'invoice', 'amount_paid', 'payment_method', 'transaction_reference', 'received_by', 'created_at')
    list_filter = ('payment_method', 'created_at')
    search_fields = ('transaction_id', 'invoice__invoice_no', 'transaction_reference')
    readonly_fields = ('transaction_id', 'created_at')

@admin.register(ExpenseCategory)
class ExpenseCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name',)

@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ('expense_no', 'title', 'category', 'amount', 'expense_date', 'payment_method', 'paid_to', 'created_by')
    list_filter = ('category', 'payment_method', 'expense_date')
    search_fields = ('expense_no', 'title', 'paid_to')
    readonly_fields = ('expense_no', 'created_at')

@admin.register(HospitalSetting)
class HospitalSettingAdmin(admin.ModelAdmin):
    list_display = ('hospital_name', 'phone', 'email', 'currency_symbol', 'sms_enabled', 'updated_at')
