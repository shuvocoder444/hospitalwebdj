from django.urls import path
from . import views

urlpatterns = [
    path('', views.lab_orders_list, name='lab_orders_list'),
    path('order/new/', views.lab_order_create, name='lab_order_create'),
    path('order/<int:order_id>/results/', views.lab_result_entry, name='lab_result_entry'),
    path('order/<int:order_id>/report/', views.lab_report_print, name='lab_report_print'),
    
    # Test Catalog & Test Creation
    path('tests/', views.test_list, name='test_list'),
    path('tests/new/', views.test_create, name='test_create'),
]
