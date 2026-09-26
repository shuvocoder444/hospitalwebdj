from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q
from decimal import Decimal
from django.core.cache import cache

from .models import TestCategory, LabTest, TestParameter, LabOrder, LabOrderItem, LabResult
from patients.models import Patient
from doctors.models import Doctor
from billing.models import Invoice, InvoiceItem, PaymentTransaction

@login_required
def lab_orders_list(request):
    status = request.GET.get('status', '')
    query = request.GET.get('q', '').strip()
    
    orders = LabOrder.objects.select_related('patient', 'referred_by_doctor').prefetch_related('items__test').order_by('-created_at')
    
    if status:
        orders = orders.filter(status=status)
    if query:
        orders = orders.filter(
            Q(order_no__icontains=query) |
            Q(patient__name__icontains=query) |
            Q(patient__phone__icontains=query) |
            Q(patient__patient_id__icontains=query)
        )
        
    context = {
        'orders': orders,
        'selected_status': status,
        'query': query,
    }

    if request.htmx:
        return render(request, 'diagnostics/partials/lab_order_table.html', context)

    return render(request, 'diagnostics/lab_orders_list.html', context)

@login_required
def lab_order_create(request):
    if request.method == 'POST':
        patient_id = request.POST.get('patient')
        doctor_id = request.POST.get('doctor') or None
        ext_doctor = request.POST.get('external_doctor_name', '')
        discount_amount = Decimal(request.POST.get('discount_amount') or '0.00')
        paid_amount = Decimal(request.POST.get('paid_amount') or '0.00')
        payment_method = request.POST.get('payment_method', 'Cash')

        test_ids = request.POST.getlist('tests[]')

        if not test_ids:
            messages.error(request, "Please select at least one lab test!")
            return redirect('lab_order_create')

        patient = get_object_or_404(Patient, pk=patient_id)
        doctor = Doctor.objects.filter(pk=doctor_id).first() if doctor_id else None

        # Fetch selected tests with parameters pre-loaded to prevent N+1
        selected_tests = LabTest.objects.filter(id__in=test_ids).prefetch_related('parameters')
        total_amount = sum(t.price for t in selected_tests)

        # Create Lab Order
        order = LabOrder.objects.create(
            patient=patient,
            referred_by_doctor=doctor,
            external_doctor_name=ext_doctor,
            total_amount=total_amount,
            discount_amount=discount_amount,
            paid_amount=paid_amount,
            status='Sample Collected',
            sample_collected_at=timezone.now(),
            created_by=request.user
        )

        # Create Order Items and Parameter Result Placeholders in bulk
        for test in selected_tests:
            item = LabOrderItem.objects.create(
                order=order,
                test=test,
                price=test.price,
                sample_collected=True
            )
            results_to_create = [
                LabResult(order_item=item, parameter=param, tested_by=request.user)
                for param in test.parameters.all()
            ]
            if results_to_create:
                LabResult.objects.bulk_create(results_to_create)

        # Create Billing Invoice & Payment Record
        invoice = Invoice.objects.create(
            patient=patient,
            bill_type='DIAGNOSTIC',
            total_amount=total_amount,
            discount_amount=discount_amount,
            paid_amount=paid_amount,
            remarks=f"Diagnostic Order {order.order_no}",
            created_by=request.user
        )
        invoice_items = [
            InvoiceItem(
                invoice=invoice,
                item_type='Lab Test',
                description=f"Lab Test: {test.name} ({test.test_code})",
                quantity=1,
                unit_price=test.price,
                subtotal=test.price
            )
            for test in selected_tests
        ]
        InvoiceItem.objects.bulk_create(invoice_items)

        if paid_amount > 0:
            PaymentTransaction.objects.create(
                invoice=invoice,
                amount_paid=paid_amount,
                payment_method=payment_method,
                received_by=request.user
            )

        messages.success(request, f"Lab Order {order.order_no} created successfully for {patient.name}!")
        return redirect('lab_result_entry', order_id=order.pk)

    pre_pat_id = request.GET.get('patient_id', '')
    patients = Patient.objects.only('id', 'patient_id', 'name', 'phone').order_by('-created_at')[:40]
    doctors = Doctor.objects.select_related('specialization').filter(is_active=True)
    tests = LabTest.objects.select_related('category').filter(is_active=True).order_by('category__name', 'name')

    return render(request, 'diagnostics/lab_order_form.html', {
        'patients': patients,
        'doctors': doctors,
        'tests': tests,
        'pre_pat_id': pre_pat_id,
    })

@login_required
def lab_result_entry(request, order_id):
    order = get_object_or_404(
        LabOrder.objects.select_related('patient', 'referred_by_doctor').prefetch_related('items__test', 'items__results__parameter'), 
        pk=order_id
    )

    if request.method == 'POST':
        for item in order.items.all():
            for result in item.results.all():
                val = request.POST.get(f"result_{result.id}", '').strip()
                flg = request.POST.get(f"flag_{result.id}", '').strip()
                rem = request.POST.get(f"remarks_{result.id}", '').strip()
                
                result.result_value = val
                result.flag = flg
                result.remarks = rem
                result.verified_by = request.user
                result.save()
            
            item.report_completed = True
            item.save()

        order.status = 'Completed'
        order.report_ready_at = timezone.now()
        order.save()

        messages.success(request, f"Lab results updated successfully for {order.order_no}!")
        return redirect('lab_report_print', order_id=order.pk)

    return render(request, 'diagnostics/lab_result_form.html', {'order': order})

@login_required
def lab_report_print(request, order_id):
    order = get_object_or_404(
        LabOrder.objects.select_related('patient', 'referred_by_doctor', 'referred_by_doctor__specialization').prefetch_related('items__test', 'items__results__parameter'), 
        pk=order_id
    )
    return render(request, 'diagnostics/lab_report_print.html', {'order': order})

@login_required
def test_list(request):
    """
    Catalog of all Diagnostic Lab Tests with search, filter, and parameter details.
    """
    category_id = request.GET.get('category', '')
    query = request.GET.get('q', '').strip()

    tests = LabTest.objects.select_related('category').prefetch_related('parameters').filter(is_active=True).order_by('category__name', 'name')
    categories = TestCategory.objects.all().order_by('name')

    if category_id:
        tests = tests.filter(category_id=category_id)
    if query:
        tests = tests.filter(Q(name__icontains=query) | Q(test_code__icontains=query))

    return render(request, 'diagnostics/test_list.html', {
        'tests': tests,
        'categories': categories,
        'selected_category': category_id,
        'query': query
    })

@login_required
def test_create(request):
    """
    Create a new Lab Test with category, specimen, pricing, delivery time, and parameters.
    """
    if request.method == 'POST':
        category_input = request.POST.get('category', '').strip()
        test_code = request.POST.get('test_code', '').strip().upper()
        name = request.POST.get('name', '').strip()
        specimen = request.POST.get('specimen', 'Blood').strip()
        price = Decimal(request.POST.get('price') or '0.00')
        cost = Decimal(request.POST.get('cost') or '0.00')
        delivery_hours = int(request.POST.get('delivery_time_hours') or '24')

        if not test_code or not name:
            messages.error(request, "Test Code and Test Name are required!")
            return redirect('test_create')

        if LabTest.objects.filter(test_code=test_code).exists():
            messages.error(request, f"Test with code '{test_code}' already exists! Please use a unique code.")
            return redirect('test_create')

        # Get or create category
        category = None
        if category_input:
            category, _ = TestCategory.objects.get_or_create(name=category_input)
        else:
            category, _ = TestCategory.objects.get_or_create(name="General Diagnostics")

        test = LabTest.objects.create(
            category=category,
            test_code=test_code,
            name=name,
            specimen=specimen,
            price=price,
            cost=cost,
            delivery_time_hours=delivery_hours,
            is_active=True
        )

        # Dynamic Parameters
        param_names = request.POST.getlist('param_name[]')
        param_units = request.POST.getlist('param_unit[]')
        param_ranges = request.POST.getlist('param_range[]')

        parameters_to_create = []
        for idx in range(len(param_names)):
            p_name = param_names[idx].strip()
            if not p_name:
                continue
            p_unit = param_units[idx].strip() if idx < len(param_units) else ''
            p_range = param_ranges[idx].strip() if idx < len(param_ranges) else ''
            parameters_to_create.append(
                TestParameter(
                    test=test,
                    name=p_name,
                    unit=p_unit,
                    reference_range=p_range,
                    order_index=idx + 1
                )
            )

        if parameters_to_create:
            TestParameter.objects.bulk_create(parameters_to_create)

        messages.success(request, f"Diagnostic Test '{test.name} ({test.test_code})' created successfully with {len(parameters_to_create)} parameters!")
        return redirect('test_list')

    categories = TestCategory.objects.all().order_by('name')
    return render(request, 'diagnostics/test_form.html', {'categories': categories})
