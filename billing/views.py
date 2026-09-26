from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Sum, Q
from decimal import Decimal
from datetime import datetime, date

from .models import Invoice, InvoiceItem, PaymentTransaction, ExpenseCategory, Expense, HospitalSetting
from patients.models import Patient

# ==================== INVOICES ====================

@login_required
def invoice_list(request):
    status = request.GET.get('status', '')
    bill_type = request.GET.get('type', '')
    query = request.GET.get('q', '').strip()

    invoices = Invoice.objects.select_related('patient', 'created_by').order_by('-created_at')

    if status:
        invoices = invoices.filter(payment_status=status)
    if bill_type:
        invoices = invoices.filter(bill_type=bill_type)
    if query:
        invoices = invoices.filter(
            Q(invoice_no__icontains=query) |
            Q(patient__name__icontains=query) |
            Q(patient__phone__icontains=query) |
            Q(patient__patient_id__icontains=query)
        )

    aggregates = invoices.aggregate(
        total_billed=Sum('payable_amount'),
        total_collected=Sum('paid_amount'),
        total_due=Sum('due_amount')
    )
    total_billed = aggregates['total_billed'] or Decimal('0.00')
    total_collected = aggregates['total_collected'] or Decimal('0.00')
    total_due = aggregates['total_due'] or Decimal('0.00')

    context = {
        'invoices': invoices,
        'selected_status': status,
        'selected_type': bill_type,
        'query': query,
        'total_billed': total_billed,
        'total_collected': total_collected,
        'total_due': total_due,
    }

    if request.htmx and not getattr(request.htmx, 'boosted', False) and request.headers.get('HX-Boosted') != 'true':
        return render(request, 'billing/partials/invoice_table.html', context)

    return render(request, 'billing/invoice_list.html', context)

@login_required
def invoice_create(request):
    if request.method == 'POST':
        patient_id = request.POST.get('patient')
        bill_type = request.POST.get('bill_type', 'GENERAL')
        discount = Decimal(request.POST.get('discount_amount') or '0.00')
        paid = Decimal(request.POST.get('paid_amount') or '0.00')
        pay_method = request.POST.get('payment_method', 'Cash')
        trx_ref = request.POST.get('transaction_reference', '')
        remarks = request.POST.get('remarks', '')

        descriptions = request.POST.getlist('item_description[]')
        quantities = request.POST.getlist('item_qty[]')
        unit_prices = request.POST.getlist('item_price[]')
        item_types = request.POST.getlist('item_type[]')

        if not patient_id:
            messages.error(request, "রোগী (Patient) নির্বাচন করা আবশ্যক!")
            return redirect('invoice_create')

        if not descriptions:
            messages.error(request, "Please add at least one line item to the bill!")
            return redirect('invoice_create')

        patient = Patient.objects.filter(pk=patient_id).first()
        if not patient:
            messages.error(request, "নির্বাচিত রোগী ডাটাবেজে পাওয়া যায়নি।")
            return redirect('invoice_create')

        total_sum = Decimal('0.00')
        items_data = []
        for i in range(len(descriptions)):
            desc = descriptions[i].strip()
            if not desc:
                continue
            qty = int(quantities[i])
            price = Decimal(unit_prices[i])
            subtotal = qty * price
            total_sum += subtotal
            itype = item_types[i] if i < len(item_types) else 'Other'
            items_data.append((desc, itype, qty, price, subtotal))

        invoice = Invoice.objects.create(
            patient=patient,
            bill_type=bill_type,
            total_amount=total_sum,
            discount_amount=discount,
            paid_amount=paid,
            remarks=remarks,
            created_by=request.user
        )

        invoice_items = [
            InvoiceItem(
                invoice=invoice,
                description=desc,
                item_type=itype,
                quantity=qty,
                unit_price=price,
                subtotal=subtotal
            )
            for desc, itype, qty, price, subtotal in items_data
        ]
        InvoiceItem.objects.bulk_create(invoice_items)

        if paid > 0:
            PaymentTransaction.objects.create(
                invoice=invoice,
                amount_paid=paid,
                payment_method=pay_method,
                transaction_reference=trx_ref,
                received_by=request.user
            )

        messages.success(request, f"Invoice {invoice.invoice_no} created successfully!")
        return redirect('invoice_detail', pk=invoice.pk)

    patients = Patient.objects.only('id', 'patient_id', 'name', 'phone').order_by('-created_at')[:40]
    pre_pat_id = request.GET.get('patient_id', '')

    return render(request, 'billing/invoice_form.html', {
        'patients': patients,
        'pre_pat_id': pre_pat_id,
    })

@login_required
def invoice_detail(request, pk):
    invoice = get_object_or_404(
        Invoice.objects.select_related('patient', 'created_by').prefetch_related('items', 'payments__received_by'), 
        pk=pk
    )
    return render(request, 'billing/invoice_detail.html', {'invoice': invoice})

@login_required
def payment_collect(request, pk):
    invoice = get_object_or_404(Invoice, pk=pk)

    if request.method == 'POST':
        amount = Decimal(request.POST.get('amount_paid') or '0.00')
        method = request.POST.get('payment_method', 'Cash')
        ref = request.POST.get('transaction_reference', '')

        if amount <= 0:
            messages.error(request, "Payment amount must be greater than zero!")
            return redirect('invoice_detail', pk=invoice.pk)

        PaymentTransaction.objects.create(
            invoice=invoice,
            amount_paid=amount,
            payment_method=method,
            transaction_reference=ref,
            received_by=request.user
        )

        invoice.paid_amount += amount
        invoice.save()

        messages.success(request, f"Payment of ৳{amount} collected for Invoice {invoice.invoice_no}!")
        return redirect('invoice_detail', pk=invoice.pk)

    return redirect('invoice_detail', pk=invoice.pk)

# ==================== EXPENSE MANAGEMENT ====================

@login_required
def expense_list(request):
    category_id = request.GET.get('category', '')
    query = request.GET.get('q', '').strip()
    from_date = request.GET.get('from_date', '')
    to_date = request.GET.get('to_date', '')

    expenses = Expense.objects.select_related('category', 'created_by').order_by('-expense_date', '-created_at')

    if category_id:
        expenses = expenses.filter(category_id=category_id)
    if from_date:
        expenses = expenses.filter(expense_date__gte=from_date)
    if to_date:
        expenses = expenses.filter(expense_date__lte=to_date)
    if query:
        expenses = expenses.filter(
            Q(expense_no__icontains=query) |
            Q(title__icontains=query) |
            Q(paid_to__icontains=query)
        )

    total_expense_amount = expenses.aggregate(Sum('amount'))['amount__sum'] or Decimal('0.00')
    categories = ExpenseCategory.objects.all()

    context = {
        'expenses': expenses,
        'categories': categories,
        'selected_category': category_id,
        'query': query,
        'from_date': from_date,
        'to_date': to_date,
        'total_expense_amount': total_expense_amount,
    }

    if request.htmx and not getattr(request.htmx, 'boosted', False) and request.headers.get('HX-Boosted') != 'true':
        return render(request, 'billing/partials/expense_table.html', context)

    return render(request, 'billing/expense_list.html', context)

@login_required
def expense_create(request):
    if request.method == 'POST':
        cat_id = request.POST.get('category')
        title = request.POST.get('title', '').strip()
        amount = Decimal(request.POST.get('amount') or '0.00')
        exp_date = request.POST.get('expense_date', timezone.now().strftime('%Y-%m-%d'))
        pay_method = request.POST.get('payment_method', 'Cash')
        paid_to = request.POST.get('paid_to', '').strip()
        voucher = request.FILES.get('voucher_receipt')
        remarks = request.POST.get('remarks', '').strip()

        errors = []
        if not cat_id:
            errors.append("খরচের ক্যাটাগরি (Expense Category) নির্বাচন করা আবশ্যক।")
        if not title:
            errors.append("খরচের বিবরণ / টাইটেল দেওয়া আবশ্যক।")
        if amount <= Decimal('0.00'):
            errors.append("খরচের পরিমাণ (Amount) ০ এর বেশি হতে হবে।")

        category = ExpenseCategory.objects.filter(pk=cat_id).first() if cat_id else None
        if not category and cat_id:
            errors.append("নির্বাচিত ক্যাটাগরি ডাটাবেজে পাওয়া যায়নি।")

        if errors:
            for err in errors:
                messages.error(request, err)
            categories = ExpenseCategory.objects.all()
            return render(request, 'billing/expense_form.html', {
                'categories': categories,
                'today': exp_date or timezone.now().strftime('%Y-%m-%d'),
            })

        exp = Expense.objects.create(
            category=category,
            title=title,
            amount=amount,
            expense_date=exp_date,
            payment_method=pay_method,
            paid_to=paid_to,
            voucher_receipt=voucher,
            remarks=remarks,
            created_by=request.user
        )

        messages.success(request, f"Expense {exp.expense_no} (৳{exp.amount}) recorded successfully!")
        return redirect('expense_list')

    categories = ExpenseCategory.objects.all()
    return render(request, 'billing/expense_form.html', {
        'categories': categories,
        'today': timezone.now().strftime('%Y-%m-%d'),
    })

# ==================== COMPLETE FINANCIAL LEDGER & PROFIT / LOSS ====================

@login_required
def financial_ledger(request):
    # Default date range: current month
    today = timezone.now().date()
    first_day_of_month = today.replace(day=1)
    
    from_date = request.GET.get('from_date', first_day_of_month.strftime('%Y-%m-%d'))
    to_date = request.GET.get('to_date', today.strftime('%Y-%m-%d'))

    # Income queries
    payments = PaymentTransaction.objects.select_related('invoice__patient', 'received_by').filter(
        created_at__date__gte=from_date,
        created_at__date__lte=to_date
    )

    total_income = payments.aggregate(Sum('amount_paid'))['amount_paid__sum'] or Decimal('0.00')
    
    # Income breakdown by Department / Bill Type
    opd_income = payments.filter(invoice__bill_type='OPD').aggregate(Sum('amount_paid'))['amount_paid__sum'] or Decimal('0.00')
    ipd_income = payments.filter(invoice__bill_type='IPD').aggregate(Sum('amount_paid'))['amount_paid__sum'] or Decimal('0.00')
    diagnostic_income = payments.filter(invoice__bill_type='DIAGNOSTIC').aggregate(Sum('amount_paid'))['amount_paid__sum'] or Decimal('0.00')
    pharmacy_income = payments.filter(invoice__bill_type='PHARMACY').aggregate(Sum('amount_paid'))['amount_paid__sum'] or Decimal('0.00')
    general_income = payments.filter(invoice__bill_type__in=['GENERAL', 'COMBINED']).aggregate(Sum('amount_paid'))['amount_paid__sum'] or Decimal('0.00')

    # Income breakdown by Payment Gateway
    cash_income = payments.filter(payment_method='Cash').aggregate(Sum('amount_paid'))['amount_paid__sum'] or Decimal('0.00')
    bkash_income = payments.filter(payment_method='bKash').aggregate(Sum('amount_paid'))['amount_paid__sum'] or Decimal('0.00')
    nagad_income = payments.filter(payment_method='Nagad').aggregate(Sum('amount_paid'))['amount_paid__sum'] or Decimal('0.00')
    card_income = payments.filter(payment_method__in=['Card', 'Bank', 'Rocket']).aggregate(Sum('amount_paid'))['amount_paid__sum'] or Decimal('0.00')

    # Expense queries
    expenses = Expense.objects.select_related('category').filter(
        expense_date__gte=from_date,
        expense_date__lte=to_date
    )
    total_expense = expenses.aggregate(Sum('amount'))['amount__sum'] or Decimal('0.00')

    # Expense breakdown by category
    expense_categories = ExpenseCategory.objects.annotate(
        category_total=Sum('expenses__amount', filter=Q(expenses__expense_date__gte=from_date, expenses__expense_date__lte=to_date))
    ).filter(category_total__gt=0).order_by('-category_total')

    # Net Profit / Loss Calculation
    net_profit = total_income - total_expense

    context = {
        'from_date': from_date,
        'to_date': to_date,
        'total_income': total_income,
        'total_expense': total_expense,
        'net_profit': net_profit,
        'opd_income': opd_income,
        'ipd_income': ipd_income,
        'diagnostic_income': diagnostic_income,
        'pharmacy_income': pharmacy_income,
        'general_income': general_income,
        'cash_income': cash_income,
        'bkash_income': bkash_income,
        'nagad_income': nagad_income,
        'card_income': card_income,
        'expense_categories': expense_categories,
        'payments': payments.order_by('-created_at')[:25],
        'expenses': expenses.order_by('-expense_date')[:25],
    }
    return render(request, 'billing/financial_ledger.html', context)

@login_required
def daily_ledger(request):
    selected_date = request.GET.get('date', timezone.now().strftime('%Y-%m-%d'))

    payments = PaymentTransaction.objects.select_related('invoice__patient', 'received_by').filter(created_at__date=selected_date).order_by('-created_at')
    expenses = Expense.objects.select_related('category').filter(expense_date=selected_date).order_by('-created_at')

    aggregates = payments.aggregate(
        total_collection=Sum('amount_paid'),
        cash_total=Sum('amount_paid', filter=Q(payment_method='Cash')),
        bkash_total=Sum('amount_paid', filter=Q(payment_method='bKash')),
        nagad_total=Sum('amount_paid', filter=Q(payment_method='Nagad')),
        card_total=Sum('amount_paid', filter=Q(payment_method__in=['Card', 'Bank', 'Rocket']))
    )
    total_expense = expenses.aggregate(Sum('amount'))['amount__sum'] or Decimal('0.00')

    total_collection = aggregates['total_collection'] or Decimal('0.00')
    cash_total = aggregates['cash_total'] or Decimal('0.00')
    bkash_total = aggregates['bkash_total'] or Decimal('0.00')
    nagad_total = aggregates['nagad_total'] or Decimal('0.00')
    card_total = aggregates['card_total'] or Decimal('0.00')
    net_daily = total_collection - total_expense

    return render(request, 'billing/daily_ledger.html', {
        'payments': payments,
        'expenses': expenses,
        'selected_date': selected_date,
        'total_collection': total_collection,
        'total_expense': total_expense,
        'net_daily': net_daily,
        'cash_total': cash_total,
        'bkash_total': bkash_total,
        'nagad_total': nagad_total,
        'card_total': card_total,
    })

# ==================== HOSPITAL GLOBAL SETTINGS & CUSTOMIZATION ====================

@login_required
def hospital_settings_view(request):
    setting = HospitalSetting.get_settings()

    if request.method == 'POST':
        setting.hospital_name = request.POST.get('hospital_name', setting.hospital_name)
        setting.hospital_tagline = request.POST.get('hospital_tagline', setting.hospital_tagline)
        setting.reg_license_no = request.POST.get('reg_license_no', setting.reg_license_no)
        setting.phone = request.POST.get('phone', setting.phone)
        setting.hotline = request.POST.get('hotline', setting.hotline)
        setting.email = request.POST.get('email', setting.email)
        setting.website = request.POST.get('website', setting.website)
        setting.address = request.POST.get('address', setting.address)
        setting.currency_symbol = request.POST.get('currency_symbol', '৳')

        # Document Footers
        setting.invoice_footer_note = request.POST.get('invoice_footer_note', setting.invoice_footer_note)
        setting.lab_report_footer_note = request.POST.get('lab_report_footer_note', setting.lab_report_footer_note)
        setting.prescription_footer_note = request.POST.get('prescription_footer_note', setting.prescription_footer_note)

        # File Uploads
        if 'logo' in request.FILES:
            setting.logo = request.FILES['logo']
        if 'favicon' in request.FILES:
            setting.favicon = request.FILES['favicon']
        if 'pdf_header_banner' in request.FILES:
            setting.pdf_header_banner = request.FILES['pdf_header_banner']
        if 'authorized_signature_seal' in request.FILES:
            setting.authorized_signature_seal = request.FILES['authorized_signature_seal']

        # SMS Gateway Settings
        setting.sms_enabled = 'sms_enabled' in request.POST
        setting.sms_provider = request.POST.get('sms_provider', 'BulkSMSBD')
        setting.sms_api_key = request.POST.get('sms_api_key', '')
        setting.sms_sender_id = request.POST.get('sms_sender_id', '')
        setting.sms_custom_url = request.POST.get('sms_custom_url', '')
        setting.sms_on_registration = 'sms_on_registration' in request.POST
        setting.sms_on_appointment = 'sms_on_appointment' in request.POST
        setting.sms_on_lab_ready = 'sms_on_lab_ready' in request.POST

        setting.save()
        messages.success(request, "Hospital branding, PDF letterhead banner, and SMS settings updated successfully!")
        return redirect('hospital_settings')

    return render(request, 'billing/hospital_settings.html', {'setting': setting})
