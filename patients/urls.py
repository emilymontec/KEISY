from django.urls import path
from .views import PatientCreateView, PatientUpdateView, PatientDeleteView, PatientDetailView

urlpatterns = [
    path('patients/add/', PatientCreateView.as_view(), name='patient_add'),
    path('patients/<int:pk>/edit/', PatientUpdateView.as_view(), name='patient_edit'),
    path('patients/<int:pk>/delete/', PatientDeleteView.as_view(), name='patient_delete'),
    path('patients/<int:pk>/', PatientDetailView.as_view(), name='patient_detail'),
]
