from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Count
from django.utils import timezone
from .models import Patient
from appointments.models import Appointment
from wards.models import Admission

@login_required
def patient_list(request):
    today = timezone.now().date()
    
    # Calculate Patient KPI Stats exactly as requested
    total_patients = Patient.objects.count()
    today_entry = Patient.objects.filter(created_at__date=today).count()
    male_count = Patient.objects.filter(gender__iexact='Male').count()
    female_count = Patient.objects.filter(gender__iexact='Female').count()
    outdoor_count = Appointment.objects.filter(appointment_date=today).count()

    query = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', '').strip()
    gender_filter = request.GET.get('gender', '').strip()
    date_filter = request.GET.get('date', '').strip()

    patients = Patient.objects.prefetch_related('admissions', 'appointments').order_by('-created_at')
    
    if query:
        patients = patients.filter(
            Q(name__icontains=query) |
            Q(phone__icontains=query) |
            Q(patient_id__icontains=query) |
            Q(address__icontains=query) |
            Q(nid_or_birth_cert__icontains=query)
        )

    if gender_filter and gender_filter != 'All':
        patients = patients.filter(gender__iexact=gender_filter)

    if date_filter:
        patients = patients.filter(created_at__date=date_filter)

    if status_filter and status_filter != 'All':
        if status_filter == 'Admitted':
            patients = patients.filter(admissions__status='Admitted').distinct()
        elif status_filter == 'Discharged':
            patients = patients.filter(admissions__status='Discharged').distinct()
        elif status_filter == 'Outdoor':
            patients = patients.filter(appointments__isnull=False).distinct()

    context = {
        'patients': patients,
        'query': query,
        'status_filter': status_filter,
        'gender_filter': gender_filter,
        'date_filter': date_filter,
        'total_patients': total_patients,
        'today_entry': today_entry,
        'male_count': male_count,
        'female_count': female_count,
        'outdoor_count': outdoor_count,
        'today_date_str': today.strftime('%Y-%m-%d'),
    }

    # HTMX Partial Response for Instant Live Search
    if request.htmx:
        return render(request, 'patients/partials/patient_table.html', context)
        
    return render(request, 'patients/patient_list.html', context)

@login_required
def patient_create(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        gender = request.POST.get('gender')
        age_years = int(request.POST.get('age_years') or 0)
        age_months = int(request.POST.get('age_months') or 0)
        blood_group = request.POST.get('blood_group', 'Unknown')
        phone = request.POST.get('phone')
        email = request.POST.get('email', '')
        nid = request.POST.get('nid_or_birth_cert', '')
        address = request.POST.get('address', '')
        emrg_name = request.POST.get('emergency_contact_name', '')
        emrg_phone = request.POST.get('emergency_contact_phone', '')
        emrg_relation = request.POST.get('emergency_contact_relation', '')

        patient = Patient.objects.create(
            name=name,
            gender=gender,
            age_years=age_years,
            age_months=age_months,
            blood_group=blood_group,
            phone=phone,
            email=email,
            nid_or_birth_cert=nid,
            address=address,
            emergency_contact_name=emrg_name,
            emergency_contact_phone=emrg_phone,
            emergency_contact_relation=emrg_relation
        )
        messages.success(request, f"Patient {patient.name} ({patient.patient_id}) registered successfully!")
        return redirect('patient_detail', pk=patient.pk)

    return render(request, 'patients/patient_form.html')

@login_required
def patient_detail(request, pk):
    # Optimized query loading all patient relations with zero N+1 queries
    patient = get_object_or_404(Patient, pk=pk)
    appointments = patient.appointments.select_related('doctor', 'doctor__specialization').order_by('-appointment_date')
    prescriptions = patient.prescriptions.select_related('doctor', 'doctor__specialization').prefetch_related('medicines').order_by('-created_at')
    lab_orders = patient.lab_orders.select_related('referred_by_doctor').prefetch_related('items__test').order_by('-created_at')
    admissions = patient.admissions.select_related('bed', 'bed__ward_type', 'admitted_under_doctor').order_by('-admission_date')
    invoices = patient.invoices.prefetch_related('items').order_by('-created_at')

    context = {
        'patient': patient,
        'appointments': appointments,
        'prescriptions': prescriptions,
        'lab_orders': lab_orders,
        'admissions': admissions,
        'invoices': invoices,
    }
    return render(request, 'patients/patient_detail.html', context)
