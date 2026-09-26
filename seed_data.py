import os
import django
from decimal import Decimal
from datetime import date, timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model
from accounts.models import User
from patients.models import Patient
from doctors.models import Specialization, Doctor
from appointments.models import Appointment
from diagnostics.models import TestCategory, LabTest, TestParameter, LabOrder, LabOrderItem
from wards.models import WardType, Bed, Admission
from pharmacy.models import MedicineCategory, GenericName, Medicine, MedicineBatch
from billing.models import Invoice, InvoiceItem, PaymentTransaction

print("[+] Starting Hospital Demo Data Seeding...")

# 1. Create Default Users
users_data = [
    ('admin', 'admin@hospital.com', 'admin123', User.Role.ADMIN, 'System', 'Admin'),
    ('dr_rafiq', 'dr.rafiq@hospital.com', 'doctor123', User.Role.DOCTOR, 'Dr. Rafiqul', 'Islam'),
    ('dr_nusrat', 'dr.nusrat@hospital.com', 'doctor123', User.Role.DOCTOR, 'Dr. Nusrat', 'Jahan'),
    ('reception', 'reception@hospital.com', 'reception123', User.Role.RECEPTIONIST, 'Karim', 'Uddin'),
    ('labtech', 'lab@hospital.com', 'lab123', User.Role.LAB_TECHNICIAN, 'Tanvir', 'Hossain'),
    ('pharmacist', 'pharmacy@hospital.com', 'pharm123', User.Role.PHARMACIST, 'Jahangir', 'Alam'),
]

created_users = {}
for username, email, pwd, role, fname, lname in users_data:
    u, created = User.objects.get_or_create(
        username=username,
        defaults={
            'email': email,
            'role': role,
            'first_name': fname,
            'last_name': lname,
            'is_staff': True,
            'is_superuser': (role == User.Role.ADMIN),
        }
    )
    if created:
        u.set_password(pwd)
        u.save()
    created_users[username] = u

print("[OK] Users created (Admin, Doctors, Receptionist, Lab Tech, Pharmacist)")

# 2. Create Specializations & Doctors
specs = [
    ('General Medicine', 'Internal Medicine & Diagnostic Consultation'),
    ('Cardiology', 'Heart & Cardiovascular Diseases'),
    ('Gynecology & Obstetrics', 'Female Reproductive & Maternity Care'),
    ('Pediatrics', 'Child Healthcare & Neonatal Care'),
    ('Orthopedics', 'Bone, Joint & Spine Care'),
    ('General Surgery', 'General & Laparoscopic Surgery'),
]

spec_objs = {}
for s_name, desc in specs:
    s_obj, _ = Specialization.objects.get_or_create(name=s_name, defaults={'description': desc})
    spec_objs[s_name] = s_obj

doctors_data = [
    ('Dr. Rafiqul Islam', 'General Medicine', 'Professor & Senior Consultant', 'MBBS, FCPS (Medicine), MD', 'BMDC-A10982', '01711122233', 800, 400, 15.0, 'Room 101', created_users['dr_rafiq']),
    ('Dr. Nusrat Jahan', 'Gynecology & Obstetrics', 'Associate Professor', 'MBBS, DGO, FCPS (Gynae)', 'BMDC-A20541', '01811223344', 1000, 500, 15.0, 'Room 102', created_users['dr_nusrat']),
    ('Dr. Mahbubur Rahman', 'Cardiology', 'Consultant Cardiologist', 'MBBS, D-Card, MD (Cardiology)', 'BMDC-A31092', '01911334455', 1000, 500, 12.0, 'Room 103', None),
    ('Dr. Shamima Nasrin', 'Pediatrics', 'Child Specialist', 'MBBS, DCH, FCPS (Pediatrics)', 'BMDC-A44901', '01511445566', 700, 350, 10.0, 'Room 104', None),
]

doctor_objs = []
for name, spec_name, desig, deg, bmdc, ph, fee, f_fee, comm, room, user_obj in doctors_data:
    doc, _ = Doctor.objects.get_or_create(
        name=name,
        defaults={
            'specialization': spec_objs[spec_name],
            'designation': desig,
            'degrees': deg,
            'bmdc_reg_no': bmdc,
            'phone': ph,
            'consultation_fee': fee,
            'follow_up_fee': f_fee,
            'commission_rate_percentage': comm,
            'room_number': room,
            'user': user_obj
        }
    )
    doctor_objs.append(doc)

print("[OK] Doctors & Specializations seeded.")

# 3. Create Diagnostics Categories, Tests & Parameters
cat_hema, _ = TestCategory.objects.get_or_create(name='Hematology', defaults={'description': 'Blood counts & related tests'})
cat_bio, _ = TestCategory.objects.get_or_create(name='Biochemistry', defaults={'description': 'Blood sugar, liver, kidney profile'})
cat_sero, _ = TestCategory.objects.get_or_create(name='Serology & Immunology', defaults={'description': 'Viral markers, antigen-antibody'})
cat_urine, _ = TestCategory.objects.get_or_create(name='Clinical Pathology (Urine/Stool)', defaults={'description': 'Routine urine/stool analysis'})
cat_radio, _ = TestCategory.objects.get_or_create(name='Radiology & Imaging', defaults={'description': 'X-Ray, Ultrasonography, ECG'})

# Tests
t_cbc, _ = LabTest.objects.get_or_create(test_code='CBC', defaults={'name': 'Complete Blood Count (CBC with ESR)', 'category': cat_hema, 'price': Decimal('400.00'), 'specimen': 'EDTA Blood'})
TestParameter.objects.get_or_create(test=t_cbc, name='Hemoglobin (Hb)', defaults={'unit': 'g/dL', 'reference_range': 'M: 13.5-17.5, F: 12.0-15.5', 'order_index': 1})
TestParameter.objects.get_or_create(test=t_cbc, name='ESR (Westergren)', defaults={'unit': 'mm/1st hr', 'reference_range': 'M: 0-10, F: 0-20', 'order_index': 2})
TestParameter.objects.get_or_create(test=t_cbc, name='Total WBC Count', defaults={'unit': '/cu.mm', 'reference_range': '4,000 - 11,000', 'order_index': 3})
TestParameter.objects.get_or_create(test=t_cbc, name='Platelet Count', defaults={'unit': '/cu.mm', 'reference_range': '150,000 - 450,000', 'order_index': 4})

t_rbs, _ = LabTest.objects.get_or_create(test_code='RBS', defaults={'name': 'Random Blood Sugar (RBS)', 'category': cat_bio, 'price': Decimal('150.00'), 'specimen': 'Fluoride Blood'})
TestParameter.objects.get_or_create(test=t_rbs, name='Random Blood Sugar', defaults={'unit': 'mmol/L', 'reference_range': '< 7.8', 'order_index': 1})

t_creat, _ = LabTest.objects.get_or_create(test_code='S.CREAT', defaults={'name': 'Serum Creatinine', 'category': cat_bio, 'price': Decimal('350.00'), 'specimen': 'Clotted Blood / Serum'})
TestParameter.objects.get_or_create(test=t_creat, name='Serum Creatinine', defaults={'unit': 'mg/dL', 'reference_range': '0.6 - 1.2', 'order_index': 1})

t_sgpt, _ = LabTest.objects.get_or_create(test_code='SGPT', defaults={'name': 'SGPT / ALT (Liver Function)', 'category': cat_bio, 'price': Decimal('350.00'), 'specimen': 'Serum'})
TestParameter.objects.get_or_create(test=t_sgpt, name='SGPT (ALT)', defaults={'unit': 'U/L', 'reference_range': 'Up to 45', 'order_index': 1})

t_lipid, _ = LabTest.objects.get_or_create(test_code='LIPID', defaults={'name': 'Lipid Profile', 'category': cat_bio, 'price': Decimal('900.00'), 'specimen': 'Serum (12hr Fasting)'})
TestParameter.objects.get_or_create(test=t_lipid, name='Total Cholesterol', defaults={'unit': 'mg/dL', 'reference_range': '< 200', 'order_index': 1})
TestParameter.objects.get_or_create(test=t_lipid, name='Triglycerides (TG)', defaults={'unit': 'mg/dL', 'reference_range': '< 150', 'order_index': 2})
TestParameter.objects.get_or_create(test=t_lipid, name='HDL Cholesterol', defaults={'unit': 'mg/dL', 'reference_range': '> 40', 'order_index': 3})
TestParameter.objects.get_or_create(test=t_lipid, name='LDL Cholesterol', defaults={'unit': 'mg/dL', 'reference_range': '< 100', 'order_index': 4})

t_dengue, _ = LabTest.objects.get_or_create(test_code='DENGUE-NS1', defaults={'name': 'Dengue NS1 Antigen', 'category': cat_sero, 'price': Decimal('400.00'), 'specimen': 'Serum'})
TestParameter.objects.get_or_create(test=t_dengue, name='Dengue NS1 Ag', defaults={'unit': 'Result', 'reference_range': 'Negative', 'order_index': 1})

t_urine_re, _ = LabTest.objects.get_or_create(test_code='URINE-RE', defaults={'name': 'Urine Routine & Microscopic Examination (R/M/E)', 'category': cat_urine, 'price': Decimal('200.00'), 'specimen': 'Mid-stream Urine'})
TestParameter.objects.get_or_create(test=t_urine_re, name='Color / Appearance', defaults={'unit': '', 'reference_range': 'Straw / Clear', 'order_index': 1})
TestParameter.objects.get_or_create(test=t_urine_re, name='Protein (Albumin)', defaults={'unit': '', 'reference_range': 'Nil', 'order_index': 2})
TestParameter.objects.get_or_create(test=t_urine_re, name='Sugar', defaults={'unit': '', 'reference_range': 'Nil', 'order_index': 3})
TestParameter.objects.get_or_create(test=t_urine_re, name='Pus Cells', defaults={'unit': '/HPF', 'reference_range': '0 - 5', 'order_index': 4})
TestParameter.objects.get_or_create(test=t_urine_re, name='R.B.C.', defaults={'unit': '/HPF', 'reference_range': 'Nil', 'order_index': 5})

t_xray, _ = LabTest.objects.get_or_create(test_code='XRAY-CHEST', defaults={'name': 'Digital X-Ray Chest P/A View', 'category': cat_radio, 'price': Decimal('500.00'), 'specimen': 'None'})
t_usg, _ = LabTest.objects.get_or_create(test_code='USG-ABDOMEN', defaults={'name': 'USG of Whole Abdomen (Color Doppler)', 'category': cat_radio, 'price': Decimal('1200.00'), 'specimen': 'None'})
t_ecg, _ = LabTest.objects.get_or_create(test_code='ECG-12', defaults={'name': '12-Lead Electrocardiogram (ECG)', 'category': cat_radio, 'price': Decimal('300.00'), 'specimen': 'None'})

print("[OK] Diagnostic categories, tests & parameters seeded.")

# 4. Create Wards & Beds
w_gen_m, _ = WardType.objects.get_or_create(name='General Ward (Male)', defaults={'description': 'Male in-patient general ward'})
w_gen_f, _ = WardType.objects.get_or_create(name='General Ward (Female)', defaults={'description': 'Female in-patient general ward'})
w_cabin_ac, _ = WardType.objects.get_or_create(name='Single AC Cabin', defaults={'description': 'Private air-conditioned cabin with attached bath'})
w_cabin_vip, _ = WardType.objects.get_or_create(name='VIP Suite Cabin', defaults={'description': 'Deluxe suite with sofa, refrigerator, AC, TV'})
w_icu, _ = WardType.objects.get_or_create(name='ICU (Intensive Care Unit)', defaults={'description': 'Critical care with ventilator and cardiac monitor'})

# Beds
for i in range(1, 6):
    Bed.objects.get_or_create(bed_number=f"M-BED-{100+i}", defaults={'ward_type': w_gen_m, 'floor': '2nd Floor', 'daily_charge': Decimal('500.00'), 'status': 'Available'})
    Bed.objects.get_or_create(bed_number=f"F-BED-{200+i}", defaults={'ward_type': w_gen_f, 'floor': '2nd Floor', 'daily_charge': Decimal('500.00'), 'status': 'Available'})

for i in range(1, 5):
    Bed.objects.get_or_create(bed_number=f"CABIN-{300+i}", defaults={'ward_type': w_cabin_ac, 'floor': '3rd Floor', 'daily_charge': Decimal('2000.00'), 'status': 'Available', 'description': 'AC, TV, Attached Bath'})

Bed.objects.get_or_create(bed_number="VIP-401", defaults={'ward_type': w_cabin_vip, 'floor': '4th Floor', 'daily_charge': Decimal('4500.00'), 'status': 'Available', 'description': 'VIP Suite, Sofa, Refrigerator'})
Bed.objects.get_or_create(bed_number="ICU-01", defaults={'ward_type': w_icu, 'floor': '1st Floor', 'daily_charge': Decimal('6000.00'), 'status': 'Available', 'description': 'Ventilator & Multi-para Monitor'})
Bed.objects.get_or_create(bed_number="ICU-02", defaults={'ward_type': w_icu, 'floor': '1st Floor', 'daily_charge': Decimal('6000.00'), 'status': 'Available', 'description': 'Ventilator & Multi-para Monitor'})

print("[OK] Wards, Cabins & Beds seeded.")

# 5. Create Pharmacy Categories, Generics, Medicines & Batches
mc_tab, _ = MedicineCategory.objects.get_or_create(name='Tablet')
mc_cap, _ = MedicineCategory.objects.get_or_create(name='Capsule')
mc_syr, _ = MedicineCategory.objects.get_or_create(name='Syrup / Suspension')
mc_inj, _ = MedicineCategory.objects.get_or_create(name='Injection / IV')

g_para, _ = GenericName.objects.get_or_create(name='Paracetamol')
g_eso, _ = GenericName.objects.get_or_create(name='Esomeprazole')
g_azi, _ = GenericName.objects.get_or_create(name='Azithromycin')
g_mon, _ = GenericName.objects.get_or_create(name='Montelukast')
g_cef, _ = GenericName.objects.get_or_create(name='Cefixime')

meds_data = [
    ('Napa Extra 500mg+65mg', g_para, mc_tab, '500mg+65mg', 'Beximco Pharmaceuticals', Decimal('3.00'), Decimal('2.40'), 1000),
    ('Ace Plus 500mg+65mg', g_para, mc_tab, '500mg+65mg', 'Square Pharmaceuticals', Decimal('3.00'), Decimal('2.40'), 800),
    ('Maxpro 20mg', g_eso, mc_tab, '20mg', 'Square Pharmaceuticals', Decimal('7.00'), Decimal('5.60'), 500),
    ('Nexum 40mg', g_eso, mc_cap, '40mg', 'Incepta Pharmaceuticals', Decimal('10.00'), Decimal('8.00'), 300),
    ('Zithrox 500mg', g_azi, mc_tab, '500mg', 'Square Pharmaceuticals', Decimal('35.00'), Decimal('28.00'), 200),
    ('Monas 10mg', g_mon, mc_tab, '10mg', 'Acme Laboratories', Decimal('17.50'), Decimal('14.00'), 400),
    ('Cef-3 200mg', g_cef, mc_cap, '200mg', 'Square Pharmaceuticals', Decimal('40.00'), Decimal('32.00'), 150),
]

for bname, gen, cat, strn, comp, sprice, pprice, qty in meds_data:
    m, _ = Medicine.objects.get_or_create(
        brand_name=bname,
        defaults={
            'generic': gen,
            'category': cat,
            'strength': strn,
            'company_name': comp,
            'unit_price': sprice,
            'reorder_level': 50
        }
    )
    MedicineBatch.objects.get_or_create(
        medicine=m,
        batch_number=f"B26-{m.id}01",
        defaults={
            'expiry_date': date.today() + timedelta(days=365),
            'purchase_cost_per_unit': pprice,
            'selling_price_per_unit': sprice,
            'quantity_in_stock': qty
        }
    )

print("[OK] Pharmacy medicines, batches & stock seeded.")

# 6. Create Demo Patients
patients_data = [
    ('Mohammad Hasan Ali', 'Male', 45, 'B+', '01712345678', 'Mirpur-10, Dhaka', 'Salma Begum (Wife)'),
    ('Fatema Begum', 'Female', 32, 'O+', '01812345678', 'Dhanmondi-27, Dhaka', 'Abdul Karim (Husband)'),
    ('Anik Chowdhury', 'Male', 19, 'A+', '01912345678', 'Uttara Sector-7, Dhaka', 'Farid Chowdhury (Father)'),
    ('Sadia Akter', 'Female', 27, 'AB+', '01612345678', 'Mohammadpur, Dhaka', 'Jashim Uddin (Brother)'),
]

p_objs = []
for name, gen, age, bg, ph, addr, emrg in patients_data:
    p, _ = Patient.objects.get_or_create(
        phone=ph,
        defaults={
            'name': name,
            'gender': gen,
            'age_years': age,
            'blood_group': bg,
            'address': addr,
            'emergency_contact_name': emrg
        }
    )
    p_objs.append(p)

print("[OK] Demo patients registered.")

# 7. Create Demo Appointments & Lab Orders & Invoices
apt1, _ = Appointment.objects.get_or_create(
    patient=p_objs[0],
    doctor=doctor_objs[0],
    appointment_date=date.today(),
    defaults={'serial_no': 1, 'fee_amount': Decimal('800.00'), 'status': 'Confirmed', 'payment_status': 'Paid'}
)

lab_ord1, _ = LabOrder.objects.get_or_create(
    patient=p_objs[0],
    defaults={
        'referred_by_doctor': doctor_objs[0],
        'total_amount': Decimal('750.00'),
        'discount_amount': Decimal('50.00'),
        'paid_amount': Decimal('700.00'),
        'status': 'Sample Collected',
        'created_by': created_users['reception']
    }
)
LabOrderItem.objects.get_or_create(order=lab_ord1, test=t_cbc, defaults={'price': Decimal('400.00'), 'sample_collected': True})
LabOrderItem.objects.get_or_create(order=lab_ord1, test=t_creat, defaults={'price': Decimal('350.00'), 'sample_collected': True})

# Inpatient admission demo
bed_to_admit = Bed.objects.filter(status='Available', ward_type=w_cabin_ac).first()
if bed_to_admit:
    adm, _ = Admission.objects.get_or_create(
        patient=p_objs[1],
        status='Admitted',
        defaults={
            'bed': bed_to_admit,
            'admitted_under_doctor': doctor_objs[1],
            'initial_deposit': Decimal('5000.00'),
            'reason_for_admission': 'Post-operative observation and IV antibiotics treatment',
            'admitted_by': created_users['reception']
        }
    )

print("[SUCCESS] Successfully seeded comprehensive Hospital & Diagnostic ERP data!")
