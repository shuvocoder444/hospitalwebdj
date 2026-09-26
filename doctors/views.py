from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from decimal import Decimal
from .models import Doctor, Specialization, Prescription, PrescriptionMedicine
from patients.models import Patient

@login_required
def doctor_list(request):
    """
    Lists all medical specialists and consultants with management controls.
    """
    query = request.GET.get('q', '').strip()
    specialization_id = request.GET.get('specialization', '')

    doctors = Doctor.objects.select_related('specialization').filter(is_active=True).order_by('id')
    
    if query:
        doctors = doctors.filter(
            name__icontains=query
        ) | doctors.filter(
            designation__icontains=query
        ) | doctors.filter(
            degrees__icontains=query
        )
        
    if specialization_id:
        doctors = doctors.filter(specialization_id=specialization_id)

    specializations = Specialization.objects.all()

    return render(request, 'doctors/doctor_list.html', {
        'doctors': doctors,
        'specializations': specializations,
        'query': query,
        'selected_specialization': specialization_id,
    })

@login_required
def doctor_create(request):
    """
    Create a new Doctor / Consultant Profile.
    """
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        spec_id = request.POST.get('specialization')
        new_spec_name = request.POST.get('new_specialization', '').strip()
        designation = request.POST.get('designation', '').strip()
        degrees = request.POST.get('degrees', '').strip()
        bmdc_reg_no = request.POST.get('bmdc_reg_no', '').strip()
        phone = request.POST.get('phone', '').strip()
        email = request.POST.get('email', '').strip()
        
        consultation_fee = Decimal(request.POST.get('consultation_fee') or '500.00')
        follow_up_fee = Decimal(request.POST.get('follow_up_fee') or '300.00')
        commission_rate = Decimal(request.POST.get('commission_rate_percentage') or '10.00')
        
        room_number = request.POST.get('room_number', 'Room 101').strip()
        available_days = request.POST.get('available_days', 'Sat, Sun, Mon, Tue, Wed, Thu').strip()
        visiting_hours = request.POST.get('visiting_hours', '5:00 PM - 9:00 PM').strip()
        photo = request.FILES.get('photo')

        if not name:
            messages.error(request, "Doctor Name is required.")
            return redirect('doctor_create')

        # Handle specialization
        specialization = None
        if new_spec_name:
            specialization, _ = Specialization.objects.get_or_create(name=new_spec_name)
        elif spec_id:
            specialization = Specialization.objects.filter(pk=spec_id).first()

        doctor = Doctor.objects.create(
            name=name,
            specialization=specialization,
            designation=designation or 'Consultant Specialist',
            degrees=degrees or 'MBBS',
            bmdc_reg_no=bmdc_reg_no,
            phone=phone,
            email=email or None,
            consultation_fee=consultation_fee,
            follow_up_fee=follow_up_fee,
            commission_rate_percentage=commission_rate,
            room_number=room_number,
            available_days=available_days,
            visiting_hours=visiting_hours,
            is_active=True
        )

        if photo:
            doctor.photo = photo
            doctor.save()

        messages.success(request, f"Doctor '{doctor.name}' added successfully to the panel!")
        return redirect('doctor_list')

    specializations = Specialization.objects.all()
    return render(request, 'doctors/doctor_form.html', {
        'title': 'Add New Doctor (নতুন ডাক্তার যুক্ত করুন)',
        'action_url': 'doctor_create',
        'specializations': specializations,
        'doctor': None,
    })

@login_required
def doctor_edit(request, pk):
    """
    Edit existing Doctor details.
    """
    doctor = get_object_or_404(Doctor, pk=pk)

    if request.method == 'POST':
        doctor.name = request.POST.get('name', '').strip() or doctor.name
        spec_id = request.POST.get('specialization')
        new_spec_name = request.POST.get('new_specialization', '').strip()
        
        if new_spec_name:
            doctor.specialization, _ = Specialization.objects.get_or_create(name=new_spec_name)
        elif spec_id:
            doctor.specialization = Specialization.objects.filter(pk=spec_id).first()

        doctor.designation = request.POST.get('designation', '').strip() or doctor.designation
        doctor.degrees = request.POST.get('degrees', '').strip() or doctor.degrees
        doctor.bmdc_reg_no = request.POST.get('bmdc_reg_no', '').strip()
        doctor.phone = request.POST.get('phone', '').strip() or doctor.phone
        doctor.email = request.POST.get('email', '').strip() or None
        
        doctor.consultation_fee = Decimal(request.POST.get('consultation_fee') or str(doctor.consultation_fee))
        doctor.follow_up_fee = Decimal(request.POST.get('follow_up_fee') or str(doctor.follow_up_fee))
        doctor.commission_rate_percentage = Decimal(request.POST.get('commission_rate_percentage') or str(doctor.commission_rate_percentage))
        
        doctor.room_number = request.POST.get('room_number', '').strip() or doctor.room_number
        doctor.available_days = request.POST.get('available_days', '').strip() or doctor.available_days
        doctor.visiting_hours = request.POST.get('visiting_hours', '').strip() or doctor.visiting_hours

        if 'photo' in request.FILES:
            doctor.photo = request.FILES.get('photo')

        doctor.save()
        messages.success(request, f"Doctor '{doctor.name}' updated successfully!")
        return redirect('doctor_list')

    specializations = Specialization.objects.all()
    return render(request, 'doctors/doctor_form.html', {
        'title': f'Edit Doctor — {doctor.name}',
        'action_url': 'doctor_edit',
        'specializations': specializations,
        'doctor': doctor,
    })

@login_required
def doctor_delete(request, pk):
    """
    Delete a Doctor (or soft delete if linked to historical records).
    """
    doctor = get_object_or_404(Doctor, pk=pk)
    doc_name = doctor.name

    if request.method == 'POST':
        try:
            doctor.delete()
            messages.success(request, f"Doctor '{doc_name}' was permanently deleted.")
        except Exception:
            # If constrained by foreign keys, soft-delete
            doctor.is_active = False
            doctor.save()
            messages.warning(request, f"Doctor '{doc_name}' has existing appointment/prescription records, so status was marked as Inactive/Removed.")
        return redirect('doctor_list')

    return render(request, 'doctors/doctor_confirm_delete.html', {'doctor': doctor})

@login_required
def prescription_create(request):
    if request.method == 'POST':
        patient_id = request.POST.get('patient')
        doctor_id = request.POST.get('doctor')
        chief_complaints = request.POST.get('chief_complaints', '')
        history = request.POST.get('history_and_findings', '')
        diagnosis = request.POST.get('diagnosis', '')
        tests_advised = request.POST.get('tests_advised', '')
        advice = request.POST.get('advice', '')
        follow_up_date = request.POST.get('follow_up_date') or None

        errors = []
        if not patient_id:
            errors.append("রোগী (Patient) নির্বাচন করা আবশ্যক।")
        if not doctor_id:
            errors.append("ডাক্তার (Doctor) নির্বাচন করা আবশ্যক।")

        patient = Patient.objects.filter(pk=patient_id).first() if patient_id else None
        doctor = Doctor.objects.filter(pk=doctor_id).first() if doctor_id else None

        if not patient and patient_id:
            errors.append("নির্বাচিত রোগী ডাটাবেজে পাওয়া যায়নি।")
        if not doctor and doctor_id:
            errors.append("নির্বাচিত ডাক্তার ডাটাবেজে পাওয়া যায়নি।")

        if errors:
            for err in errors:
                messages.error(request, err)
            
            # Re-render with existing context
            patients = Patient.objects.all().order_by('-created_at')[:50]
            doctors = Doctor.objects.filter(is_active=True)
            from pharmacy.models import Medicine
            from diagnostics.models import LabTest
            return render(request, 'doctors/prescription_form.html', {
                'patients': patients,
                'doctors': doctors,
                'pre_pat_id': patient_id,
                'pre_doc_id': doctor_id,
                'medicines_catalog': Medicine.objects.filter(is_active=True).select_related('category', 'generic').order_by('brand_name'),
                'lab_tests_catalog': LabTest.objects.filter(is_active=True).order_by('name'),
            })

        rx = Prescription.objects.create(
            patient=patient,
            doctor=doctor,
            chief_complaints=chief_complaints,
            history_and_findings=history,
            diagnosis=diagnosis,
            tests_advised=tests_advised,
            advice=advice,
            follow_up_date=follow_up_date
        )

        # Parse medicines arrays
        med_names = request.POST.getlist('med_name[]')
        dosages = request.POST.getlist('dosage[]')
        durations = request.POST.getlist('duration[]')
        instructions = request.POST.getlist('instruction[]')

        for i in range(len(med_names)):
            name = med_names[i].strip()
            if name:
                PrescriptionMedicine.objects.create(
                    prescription=rx,
                    medicine_name=name,
                    dosage=dosages[i] if i < len(dosages) else '1+0+1',
                    duration=durations[i] if i < len(durations) else '7 days',
                    instruction=instructions[i] if i < len(instructions) else 'After meal'
                )

        messages.success(request, f"Prescription {rx.prescription_no} তৈরি সম্পন্ন হয়েছে!")
        return redirect('prescription_detail', pk=rx.pk)

    pre_pat_id = request.GET.get('patient_id', '')
    pre_doc_id = request.GET.get('doctor_id', '')

    # Auto detect logged in doctor
    if not pre_doc_id and request.user.is_doctor:
        doc_profile = Doctor.objects.filter(user=request.user).first()
        if doc_profile:
            pre_doc_id = str(doc_profile.id)

    patients = Patient.objects.all().order_by('-created_at')[:50]
    doctors = Doctor.objects.filter(is_active=True)

    from pharmacy.models import Medicine
    from diagnostics.models import LabTest
    medicines_catalog = Medicine.objects.filter(is_active=True).select_related('category', 'generic').order_by('brand_name')
    lab_tests_catalog = LabTest.objects.filter(is_active=True).order_by('name')

    return render(request, 'doctors/prescription_form.html', {
        'patients': patients,
        'doctors': doctors,
        'pre_pat_id': pre_pat_id,
        'pre_doc_id': pre_doc_id,
        'medicines_catalog': medicines_catalog,
        'lab_tests_catalog': lab_tests_catalog,
    })

@login_required
def prescription_detail(request, pk):
    prescription = get_object_or_404(Prescription.objects.select_related('patient', 'doctor', 'doctor__specialization'), pk=pk)
    medicines = prescription.medicines.all()
    return render(request, 'doctors/prescription_detail.html', {
        'prescription': prescription,
        'medicines': medicines,
    })
