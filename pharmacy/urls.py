from django.urls import path
from . import views

urlpatterns = [
    path('pos/', views.pharmacy_pos, name='pharmacy_pos'),
    path('stock/', views.medicine_stock_list, name='medicine_stock_list'),
    path('medicine/add/', views.medicine_create, name='medicine_create'),
    path('medicine/<int:pk>/add-batch/', views.medicine_add_batch, name='medicine_add_batch'),
    path('receipt/<int:pk>/', views.pharmacy_receipt, name='pharmacy_receipt'),
]
