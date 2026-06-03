from django.urls import path
from .views import export_patients

urlpatterns = [
    path('export/<str:format>/', export_patients, name='export_patients'),
]
