from django.contrib import admin
from .models import TestCategory, LabTest, TestParameter, LabOrder, LabOrderItem, LabResult

class TestParameterInline(admin.TabularInline):
    model = TestParameter
    extra = 1

@admin.register(TestCategory)
class TestCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name',)

@admin.register(LabTest)
class LabTestAdmin(admin.ModelAdmin):
    list_display = ('test_code', 'name', 'category', 'price', 'specimen', 'delivery_time_hours', 'is_active')
    list_filter = ('category', 'is_active')
    search_fields = ('test_code', 'name')
    inlines = [TestParameterInline]

class LabOrderItemInline(admin.TabularInline):
    model = LabOrderItem
    extra = 1

@admin.register(LabOrder)
class LabOrderAdmin(admin.ModelAdmin):
    list_display = ('order_no', 'patient', 'referred_by_doctor', 'payable_amount', 'paid_amount', 'due_amount', 'status', 'created_at')
    list_filter = ('status', 'created_at', 'referred_by_doctor')
    search_fields = ('order_no', 'patient__name', 'patient__phone', 'external_doctor_name')
    readonly_fields = ('order_no', 'payable_amount', 'due_amount', 'doctor_commission_amount', 'created_at')
    inlines = [LabOrderItemInline]

@admin.register(LabResult)
class LabResultAdmin(admin.ModelAdmin):
    list_display = ('order_item', 'parameter', 'result_value', 'flag', 'tested_by', 'verified_by', 'updated_at')
    list_filter = ('flag', 'updated_at')
    search_fields = ('order_item__order__order_no', 'parameter__name', 'result_value')
