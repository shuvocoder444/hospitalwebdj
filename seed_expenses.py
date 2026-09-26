import os
import django
from decimal import Decimal
from datetime import date, timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from billing.models import ExpenseCategory, Expense, HospitalSetting
from accounts.models import User

print("[+] Seeding Expense Categories & Initial Hospital Settings...")

# Expense categories
categories = [
    ('Staff Salary', 'Monthly salary of nurses, ward staff, cleaning, receptionist'),
    ('Electricity & Utilities', 'DPDC/DESCO electricity bill, WASA water bill, gas bill'),
    ('Medical & Surgical Supplies', 'Syringes, cannulas, saline, gauze, cotton, bandages'),
    ('Lab Reagents & Chemicals', 'Pathology chemical kits, strips, slides, reagents'),
    ('Doctor Commission Payout', 'Referral commission payments to consultant doctors'),
    ('Building Rent & Service Charge', 'Hospital building monthly rent and maintenance fee'),
    ('Equipment Maintenance & Repairs', 'X-Ray, USG, CBC analyzer servicing and repair'),
    ('Office Stationery & Printing', 'Prescription pads, money receipt books, files, printer toner'),
    ('Marketing & Advertising', 'Online ads, banners, healthcare awareness campaigns'),
    ('Generator Diesel & Fuel', 'Fuel for generator and hospital ambulance'),
]

admin_user = User.objects.filter(is_superuser=True).first()

for name, desc in categories:
    cat, _ = ExpenseCategory.objects.get_or_create(name=name, defaults={'description': desc})

# Add a few demo expenses
Expense.objects.get_or_create(
    title='September Generator Diesel Fuel (50L)',
    defaults={
        'category': ExpenseCategory.objects.get(name='Generator Diesel & Fuel'),
        'amount': Decimal('5500.00'),
        'expense_date': date.today(),
        'payment_method': 'Cash',
        'paid_to': 'Padma Oil Service Station',
        'created_by': admin_user
    }
)
Expense.objects.get_or_create(
    title='Clinical Pathology CBC Reagent Kit',
    defaults={
        'category': ExpenseCategory.objects.get(name='Lab Reagents & Chemicals'),
        'amount': Decimal('12000.00'),
        'expense_date': date.today() - timedelta(days=2),
        'payment_method': 'Bank',
        'paid_to': 'Bio-Lab BD Importers',
        'created_by': admin_user
    }
)

# Ensure Hospital Setting exists
HospitalSetting.get_settings()

print("[SUCCESS] Expense categories & settings seeded successfully!")
