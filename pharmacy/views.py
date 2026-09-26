from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from decimal import Decimal
from django.db import transaction

from .models import Medicine, MedicineBatch, PharmacySale, PharmacySaleItem, MedicineCategory, GenericName
from patients.models import Patient
from billing.models import Invoice, InvoiceItem, PaymentTransaction

@login_required
def medicine_stock_list(request):
    medicines = Medicine.objects.select_related('generic', 'category').prefetch_related('batches').filter(is_active=True).order_by('brand_name')
    categories = MedicineCategory.objects.all().order_by('name')
    generics = GenericName.objects.all().order_by('name')
    return render(request, 'pharmacy/medicine_stock.html', {
        'medicines': medicines, 
        'categories': categories,
        'generics': generics,
        'today': timezone.now().date()
    })

@login_required
def medicine_create(request):
    """
    Create a new medicine in pharmacy inventory with optional initial batch.
    """
    if request.method == 'POST':
        brand_name = request.POST.get('brand_name', '').strip()
        generic_input = request.POST.get('generic', '').strip()
        category_input = request.POST.get('category', '').strip()
        strength = request.POST.get('strength', '').strip()
        company_name = request.POST.get('company_name', '').strip()
        unit_price = Decimal(request.POST.get('unit_price') or '0.00')
        reorder_level = int(request.POST.get('reorder_level') or '50')

        if not brand_name:
            messages.error(request, "Medicine Brand Name is required!")
            return redirect('medicine_stock_list')

        # Get or create category
        category = None
        if category_input:
            category, _ = MedicineCategory.objects.get_or_create(name=category_input)

        # Get or create generic name
        generic = None
        if generic_input:
            generic, _ = GenericName.objects.get_or_create(name=generic_input)

        medicine = Medicine.objects.create(
            brand_name=brand_name,
            generic=generic,
            category=category,
            strength=strength,
            company_name=company_name,
            unit_price=unit_price,
            reorder_level=reorder_level,
            is_active=True
        )

        # Optional initial stock batch
        batch_no = request.POST.get('batch_number', '').strip()
        qty = int(request.POST.get('quantity_in_stock') or '0')
        exp_date = request.POST.get('expiry_date')
        purchase_cost = Decimal(request.POST.get('purchase_cost') or '0.00')

        if batch_no and qty > 0 and exp_date:
            MedicineBatch.objects.create(
                medicine=medicine,
                batch_number=batch_no,
                expiry_date=exp_date,
                purchase_cost_per_unit=purchase_cost,
                selling_price_per_unit=unit_price,
                quantity_in_stock=qty
            )

        messages.success(request, f"Medicine '{medicine.brand_name} ({medicine.strength or ''})' added successfully to inventory!")
        return redirect('medicine_stock_list')

    return redirect('medicine_stock_list')

@login_required
def medicine_add_batch(request, pk):
    """
    Add a new purchase/stock batch to an existing medicine.
    """
    medicine = get_object_or_404(Medicine, pk=pk)
    if request.method == 'POST':
        batch_no = request.POST.get('batch_number', '').strip()
        qty = int(request.POST.get('quantity') or '0')
        exp_date = request.POST.get('expiry_date')
        purchase_cost = Decimal(request.POST.get('purchase_cost') or '0.00')
        selling_price = Decimal(request.POST.get('selling_price') or str(medicine.unit_price))

        if not batch_no or qty <= 0 or not exp_date:
            messages.error(request, "Valid Batch number, quantity (>0), and expiry date are required!")
            return redirect('medicine_stock_list')

        MedicineBatch.objects.create(
            medicine=medicine,
            batch_number=batch_no,
            expiry_date=exp_date,
            purchase_cost_per_unit=purchase_cost,
            selling_price_per_unit=selling_price,
            quantity_in_stock=qty
        )

        messages.success(request, f"Added batch '{batch_no}' ({qty} pcs) to {medicine.brand_name}!")
        return redirect('medicine_stock_list')

    return redirect('medicine_stock_list')

@login_required
def pharmacy_pos(request):
    if request.method == 'POST':
        patient_id = request.POST.get('patient') or None
        cust_name = request.POST.get('customer_name', 'Walk-in Customer')
        cust_phone = request.POST.get('customer_phone', '')
        discount = Decimal(request.POST.get('discount_amount') or '0.00')
        paid = Decimal(request.POST.get('paid_amount') or '0.00')
        payment_method = request.POST.get('payment_method', 'Cash')

        batch_ids = request.POST.getlist('batch_id[]')
        quantities = request.POST.getlist('quantity[]')

        if not batch_ids:
            messages.error(request, "Please add at least one medicine item to the cart!")
            return redirect('pharmacy_pos')

        patient = Patient.objects.filter(pk=patient_id).first() if patient_id else None

        with transaction.atomic():
            # Calculate total & validate stock
            total_sum = Decimal('0.00')
            items_to_create = []

            for i in range(len(batch_ids)):
                b_id = batch_ids[i]
                qty = int(quantities[i])
                if qty <= 0:
                    continue

                batch = get_object_or_404(MedicineBatch, pk=b_id)
                if batch.quantity_in_stock < qty:
                    messages.error(request, f"Insufficient stock for {batch.medicine.brand_name}! Available: {batch.quantity_in_stock}")
                    return redirect('pharmacy_pos')

                unit_price = batch.selling_price_per_unit
                subtotal = unit_price * qty
                total_sum += subtotal

                # Decrement stock
                batch.quantity_in_stock -= qty
                batch.save()

                items_to_create.append((batch, qty, unit_price, subtotal))

            sale = PharmacySale.objects.create(
                patient=patient,
                customer_name=patient.name if patient else cust_name,
                customer_phone=patient.phone if patient else cust_phone,
                total_amount=total_sum,
                discount_amount=discount,
                paid_amount=paid,
                sold_by=request.user
            )

            for b, q, up, sub in items_to_create:
                PharmacySaleItem.objects.create(
                    sale=sale,
                    batch=b,
                    quantity=q,
                    unit_price=up,
                    subtotal=sub
                )

            # If patient is linked, create a Billing Invoice entry
            if patient:
                inv = Invoice.objects.create(
                    patient=patient,
                    bill_type='PHARMACY',
                    total_amount=total_sum,
                    discount_amount=discount,
                    paid_amount=paid,
                    remarks=f"Pharmacy Sale {sale.invoice_no}",
                    created_by=request.user
                )
                for b, q, up, sub in items_to_create:
                    InvoiceItem.objects.create(
                        invoice=inv,
                        item_type='Medicine',
                        description=f"{b.medicine.brand_name} ({b.medicine.strength or ''}) x {q}",
                        quantity=q,
                        unit_price=up
                    )
                if paid > 0:
                    PaymentTransaction.objects.create(
                        invoice=inv,
                        amount_paid=paid,
                        payment_method=payment_method,
                        received_by=request.user
                    )

        messages.success(request, f"Pharmacy Sale {sale.invoice_no} completed successfully!")
        return redirect('pharmacy_receipt', pk=sale.pk)

    patients = Patient.objects.all().order_by('-created_at')[:30]
    available_batches = MedicineBatch.objects.select_related('medicine').filter(
        quantity_in_stock__gt=0,
        expiry_date__gte=timezone.now().date()
    ).order_by('medicine__brand_name')

    return render(request, 'pharmacy/pharmacy_pos.html', {
        'patients': patients,
        'batches': available_batches,
    })

@login_required
def pharmacy_receipt(request, pk):
    sale = get_object_or_404(PharmacySale.objects.prefetch_related('items__batch__medicine'), pk=pk)
    return render(request, 'pharmacy/pharmacy_receipt.html', {'sale': sale})
