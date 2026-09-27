from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db.models import Sum, Count, F, Q
from django.core.cache import cache
from django.conf import settings
from django.contrib import messages

from patients.models import Patient
from doctors.models import Doctor, Specialization
from diagnostics.models import LabTest, TestCategory, LabOrder
from wards.models import WardType, Bed
from appointments.models import Appointment
from pharmacy.models import Medicine
from billing.models import Invoice, PaymentTransaction

def landing_page_view(request):
    """
    Public Modern Landing Page for WebKoders Healthcare & Hospital Software ERP.
    """
    if request.method == 'POST' and 'public_appointment' in request.POST:
        # Public online booking request from landing page
        name = request.POST.get('name')
        phone = request.POST.get('phone')
        age = int(request.POST.get('age') or 0)
        gender = request.POST.get('gender', 'Male')
        doctor_id = request.POST.get('doctor')
        apt_date = request.POST.get('appointment_date', timezone.now().strftime('%Y-%m-%d'))
        notes = request.POST.get('notes', '')

        # Get or create patient by phone
        patient, created = Patient.objects.get_or_create(
            phone=phone,
            defaults={
                'name': name,
                'age_years': age,
                'gender': gender,
            }
        )

        doctor = Doctor.objects.filter(pk=doctor_id).first()
        if doctor:
            apt = Appointment.objects.create(
                patient=patient,
                doctor=doctor,
                appointment_date=apt_date,
                time_slot=doctor.visiting_hours,
                fee_amount=doctor.consultation_fee,
                payment_status='Unpaid',
                status='Pending',
                notes=f"Online Web Booking. {notes}",
            )
            messages.success(request, f"Appointment Serial #{apt.serial_no} booked successfully! Our reception will call you at {phone} to confirm.")
            return redirect('landing')

    doctors = Doctor.objects.select_related('specialization').filter(is_active=True)
    specializations = Specialization.objects.all()
    categories = TestCategory.objects.prefetch_related('tests').all()
    tests = LabTest.objects.select_related('category').filter(is_active=True)[:12]
    ward_types = WardType.objects.prefetch_related('beds').all()
    
    total_doctors = doctors.count()
    total_beds = Bed.objects.count()
    total_tests = LabTest.objects.filter(is_active=True).count()
    
    return render(request, 'landing/index.html', {
        'doctors': doctors,
        'specializations': specializations,
        'categories': categories,
        'tests': tests,
        'ward_types': ward_types,
        'total_doctors': total_doctors,
        'total_beds': total_beds,
        'total_tests': total_tests,
        'today': timezone.now().strftime('%Y-%m-%d'),
    })

def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    next_url = request.GET.get('next') or request.POST.get('next') or 'dashboard'
    
    if request.method == 'POST':
        u = request.POST.get('username', '').strip()
        p = request.POST.get('password', '')
        user = authenticate(request, username=u, password=p)
        if user is not None:
            login(request, user)
            return redirect(next_url)
        else:
            messages.error(request, "Invalid username or password. Please try again.")
            return render(request, 'accounts/login.html', {'next': next_url, 'entered_username': u})
            
    return render(request, 'accounts/login.html', {'next': next_url})

def logout_view(request):
    logout(request)
    messages.info(request, "You have been logged out successfully.")
    return redirect('login')

@login_required
def dashboard_view(request):
    today = timezone.now().date()
    cache_key = f"dashboard_stats_{today}"
    
    cached_stats = cache.get(cache_key)
    if not cached_stats:
        total_patients = Patient.objects.count()
        today_patients = Patient.objects.filter(created_at__date=today).count()
        today_appointments_count = Appointment.objects.filter(appointment_date=today).count()
        occupied_beds = Bed.objects.filter(status='Occupied').count()
        total_beds = Bed.objects.count()
        pending_lab_tests = LabOrder.objects.filter(status__in=['Pending', 'Sample Collected', 'In Progress']).count()
        
        today_collection = PaymentTransaction.objects.filter(created_at__date=today).aggregate(Sum('amount_paid'))['amount_paid__sum'] or 0
        total_revenue = Invoice.objects.aggregate(Sum('paid_amount'))['paid_amount__sum'] or 0
        total_due = Invoice.objects.aggregate(Sum('due_amount'))['due_amount__sum'] or 0

        low_stock_count = Medicine.objects.filter(is_active=True).annotate(
            current_stock=Sum('batches__quantity_in_stock')
        ).filter(Q(current_stock__lte=F('reorder_level')) | Q(current_stock__isnull=True)).count()

        cached_stats = {
            'total_patients': total_patients,
            'today_patients': today_patients,
            'today_appointments_count': today_appointments_count,
            'occupied_beds': occupied_beds,
            'total_beds': total_beds,
            'pending_lab_tests': pending_lab_tests,
            'today_collection': today_collection,
            'total_due': total_due,
            'total_revenue': total_revenue,
            'low_stock_count': low_stock_count,
        }
        cache.set(cache_key, cached_stats, timeout=60)

    recent_patients = Patient.objects.only('id', 'patient_id', 'name', 'phone', 'created_at').order_by('-created_at')[:5]
    recent_invoices = Invoice.objects.select_related('patient').only('id', 'invoice_no', 'patient__name', 'payable_amount', 'payment_status', 'created_at').order_by('-created_at')[:6]
    recent_appointments = Appointment.objects.select_related('patient', 'doctor', 'doctor__specialization').filter(appointment_date=today).order_by('serial_no')[:6]

    # Doctor specific data
    doctor_profile = None
    my_today_appointments = []
    my_prescriptions_count = 0
    if request.user.role == 'DOCTOR':
        doctor_profile = Doctor.objects.filter(user=request.user).first()
        if not doctor_profile:
            # Fallback matching by name
            doctor_profile = Doctor.objects.filter(name__icontains=request.user.first_name or request.user.username).first()
        if doctor_profile:
            my_today_appointments = Appointment.objects.filter(doctor=doctor_profile, appointment_date=today).select_related('patient').order_by('serial_no')
            from doctors.models import Prescription
            my_prescriptions_count = Prescription.objects.filter(doctor=doctor_profile).count()

    # Lab Tech specific data
    recent_lab_orders = []
    total_active_tests = 0
    if request.user.role in ['LAB_TECH', 'ADMIN']:
        recent_lab_orders = LabOrder.objects.select_related('patient', 'referred_by_doctor').order_by('-created_at')[:8]
        total_active_tests = LabTest.objects.filter(is_active=True).count()

    db_engine_name = "PostgreSQL" if settings.DATABASES['default']['ENGINE'].endswith('postgresql') else "SQLite3"

    context = {
        **cached_stats,
        'recent_patients': recent_patients,
        'recent_invoices': recent_invoices,
        'recent_appointments': recent_appointments,
        'doctor_profile': doctor_profile,
        'my_today_appointments': my_today_appointments,
        'my_prescriptions_count': my_prescriptions_count,
        'recent_lab_orders': recent_lab_orders,
        'total_active_tests': total_active_tests,
        'db_type': db_engine_name,
    }
    return render(request, 'dashboard/index.html', context)
