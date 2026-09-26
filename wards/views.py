from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from decimal import Decimal

from .models import WardType, Bed, Admission
from patients.models import Patient
from doctors.models import Doctor
from billing.models import Invoice, InvoiceItem, PaymentTransaction

@login_required
def ward_bed_status(request):
    ward_types = WardType.objects.prefetch_related('beds').all()
    admissions = Admission.objects.select_related('patient', 'bed', 'admitted_under_doctor').filter(status='Admitted').order_by('-admission_date')
    
    total_beds = Bed.objects.count()
    occupied_count = Bed.objects.filter(status='Occupied').count()
    available_count = Bed.objects.filter(status='Available').count()
    
    return render(request, 'wards/bed_status.html', {
        'ward_types': ward_types,
        'admissions': admissions,
        'total_beds': total_beds,
        'occupied_count': occupied_count,
        'available_count': available_count,
    })

@login_required
def admission_create(request):
    if request.method == 'POST':
        patient_id = request.POST.get('patient')
        bed_id = request.POST.get('bed')
        doctor_id = request.POST.get('doctor')
        deposit = Decimal(request.POST.get('initial_deposit') or '0.00')
        reason = request.POST.get('reason_for_admission', '')

        patient = get_object_or_404(Patient, pk=patient_id)
        bed = get_object_or_404(Bed, pk=bed_id)
        doctor = get_object_or_404(Doctor, pk=doctor_id)

        if bed.status != 'Available':
            messages.error(request, f"Bed {bed.bed_number} is currently not available!")
            return redirect('admission_create')

        adm = Admission.objects.create(
            patient=patient,
            bed=bed,
            admitted_under_doctor=doctor,
            initial_deposit=deposit,
            reason_for_admission=reason,
            status='Admitted',
            admitted_by=request.user
        )

        # Create initial IPD invoice with advance deposit if deposited
        if deposit > 0:
            inv = Invoice.objects.create(
                patient=patient,
                bill_type='IPD',
                total_amount=deposit,
                paid_amount=deposit,
                remarks=f"IPD Advance Deposit for Admission {adm.admission_no}",
                created_by=request.user
            )
            InvoiceItem.objects.create(
                invoice=inv,
                item_type='Other',
                description=f"IPD Admission Advance Deposit ({bed.bed_number})",
                quantity=1,
                unit_price=deposit
            )
            PaymentTransaction.objects.create(
                invoice=inv,
                amount_paid=deposit,
                payment_method='Cash',
                received_by=request.user
            )

        messages.success(request, f"Patient {patient.name} admitted successfully to {bed.bed_number}!")
        return redirect('ward_bed_status')

    pre_pat_id = request.GET.get('patient_id', '')
    pre_bed_id = request.GET.get('bed_id', '')
    patients = Patient.objects.all().order_by('-created_at')[:30]
    available_beds = Bed.objects.filter(status='Available').select_related('ward_type')
    doctors = Doctor.objects.filter(is_active=True)

    return render(request, 'wards/admission_form.html', {
        'patients': patients,
        'available_beds': available_beds,
        'doctors': doctors,
        'pre_pat_id': pre_pat_id,
        'pre_bed_id': pre_bed_id,
    })

@login_required
def admission_discharge(request, pk):
    admission = get_object_or_404(Admission.objects.select_related('patient', 'bed', 'bed__ward_type', 'admitted_under_doctor'), pk=pk)

    if request.method == 'POST':
        summary = request.POST.get('discharge_summary', '')
        advice = request.POST.get('discharge_advice', '')
        
        admission.discharge_date = timezone.now()
        admission.status = 'Discharged'
        admission.discharge_summary = summary
        admission.discharge_advice = advice
        admission.save()

        # Generate Final Bed Stay Invoice
        total_stay_charge = admission.total_bed_charge
        inv = Invoice.objects.create(
            patient=admission.patient,
            bill_type='IPD',
            total_amount=total_stay_charge,
            discount_amount=Decimal('0.00'),
            paid_amount=admission.initial_deposit,
            remarks=f"Final Inpatient Bed Stay Bill for {admission.admission_no}",
            created_by=request.user
        )
        InvoiceItem.objects.create(
            invoice=inv,
            item_type='Bed Charge',
            description=f"Cabin / Bed Charges ({admission.bed.bed_number} - {admission.total_days} Days @ ৳{admission.bed.daily_charge}/day)",
            quantity=admission.total_days,
            unit_price=admission.bed.daily_charge
        )

        messages.success(request, f"Patient {admission.patient.name} discharged successfully. Final invoice generated!")
        return redirect('invoice_detail', pk=inv.pk)

    return render(request, 'wards/discharge_form.html', {'admission': admission})
