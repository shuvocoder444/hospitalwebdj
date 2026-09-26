"""
URL configuration for WebKoders Healthcare ERP & Hospital Software BD.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from accounts.views import landing_page_view, dashboard_view, login_view, logout_view

admin.site.site_header = "WebKoders Healthcare ERP - Admin Portal"
admin.site.site_title = "Hospital Management ERP"
admin.site.index_title = "Hospital Administration & Operations"

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Public Landing Page & Auth
    path('', landing_page_view, name='landing'),
    path('dashboard/', dashboard_view, name='dashboard'),
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    
    # Apps
    path('patients/', include('patients.urls')),
    path('appointments/', include('appointments.urls')),
    path('doctors/', include('doctors.urls')),
    path('diagnostics/', include('diagnostics.urls')),
    path('wards/', include('wards.urls')),
    path('pharmacy/', include('pharmacy.urls')),
    path('billing/', include('billing.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
