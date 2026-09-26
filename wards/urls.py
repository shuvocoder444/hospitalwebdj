from django.urls import path
from . import views

urlpatterns = [
    path('', views.ward_bed_status, name='ward_bed_status'),
    path('admit/', views.admission_create, name='admission_create'),
    path('admission/<int:pk>/discharge/', views.admission_discharge, name='admission_discharge'),
]
