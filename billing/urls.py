from django.urls import path
from . import views

urlpatterns = [
    # Invoices
    path('', views.invoice_list, name='invoice_list'),
    path('new/', views.invoice_create, name='invoice_create'),
    path('<int:pk>/', views.invoice_detail, name='invoice_detail'),
    path('<int:pk>/pay/', views.payment_collect, name='payment_collect'),
    
    # Expenses
    path('expenses/', views.expense_list, name='expense_list'),
    path('expenses/new/', views.expense_create, name='expense_create'),
    
    # Ledgers & Accounts
    path('ledger/', views.daily_ledger, name='daily_ledger'),
    path('ledger/statement/', views.financial_ledger, name='financial_ledger'),
    
    # Hospital Global Settings
    path('settings/', views.hospital_settings_view, name='hospital_settings'),
]
