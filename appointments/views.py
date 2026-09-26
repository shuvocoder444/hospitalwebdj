from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from .models import Appointment
from patients.models import Patient
from doctors.models import Doctor

@login_required
def appointment_list(request):
    selected_date = request.GET.get('date', timezone.now().strftime('%Y-%m-%d'))
    doctor_id = request.GET.get('doctor_id', '')
    
    appointments = Appointment.objects.select_related('patient', 'doctor', 'doctor__specialization').order_by('serial_no')
    
    if selected_date:
        appointments = appointments.filter(appointment_date=selected_date)
    if doctor_id:
        appointments = appointments.filter(doctor_id=doctor_id)
        
    doctors = Doctor.objects.select_related('specialization').filter(is_active=True)

    context = {
        'appointments': appointments,
        'doctors': doctors,
        'selected_date': selected_date,
        'selected_doctor_id': doctor_id,
    }

    if request.htmx and not getattr(request.htmx, 'boosted', False) and request.headers.get('HX-Boosted') != 'true':
        return render(request, 'appointments/partials/appointment_table.html', context)
    
    return render(request, 'appointments/appointment_list.html', context)

@login_required
def appointment_create(request):
    if request.method == 'POST':
        patient_id = request.POST.get('patient')
        doctor_id = request.POST.get('doctor')
        appointment_date = request.POST.get('appointment_date', timezone.now().strftime('%Y-%m-%d'))
        time_slot = request.POST.get('time_slot', '')
        payment_status = request.POST.get('payment_status', 'Paid')
        notes = request.POST.get('notes', '')

        errors = []
        if not patient_id:
            errors.append("রোগী (Patient) নির্বাচন করা আবশ্যক।")
        if not doctor_id:
            errors.append("ডাক্তার (Doctor) নির্বাচন করা আবশ্যক।")
        if not appointment_date:
            errors.append("অ্যাপয়েন্টমেন্ট এর তারিখ দেওয়া আবশ্যক।")

        patient = Patient.objects.filter(pk=patient_id).first() if patient_id else None
        doctor = Doctor.objects.filter(pk=doctor_id).first() if doctor_id else None

        if not patient and patient_id:
            errors.append("নির্বাচিত রোগী ডাটাবেজে পাওয়া যায়নি।")
        if not doctor and doctor_id:
            errors.append("নির্বাচিত ডাক্তার ডাটাবেজে পাওয়া যায়নি।")

        if errors:
            for err in errors:
                messages.error(request, err)
            patients = Patient.objects.only('id', 'patient_id', 'name', 'phone').order_by('-created_at')[:40]
            doctors = Doctor.objects.select_related('specialization').filter(is_active=True)
            return render(request, 'appointments/appointment_form.html', {
                'patients': patients,
                'doctors': doctors,
                'preselected_patient_id': patient_id,
                'today': appointment_date or timezone.now().strftime('%Y-%m-%d'),
            })

        appointment = Appointment.objects.create(
            patient=patient,
            doctor=doctor,
            appointment_date=appointment_date,
            time_slot=time_slot or doctor.visiting_hours,
            fee_amount=doctor.consultation_fee,
            payment_status=payment_status,
            status='Confirmed',
            notes=notes,
            created_by=request.user
        )
        messages.success(request, f"OPD Serial #{appointment.serial_no} booked for {patient.name} with Dr. {doctor.name}")
        return redirect('appointment_list')

    patients = Patient.objects.only('id', 'patient_id', 'name', 'phone').order_by('-created_at')[:40]
    doctors = Doctor.objects.select_related('specialization').filter(is_active=True)
    preselected_patient_id = request.GET.get('patient_id', '')

    return render(request, 'appointments/appointment_form.html', {
        'patients': patients,
        'doctors': doctors,
        'preselected_patient_id': preselected_patient_id,
        'today': timezone.now().strftime('%Y-%m-%d'),
    })
