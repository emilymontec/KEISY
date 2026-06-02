from django.urls import path
from .views import clinical_analytics

urlpatterns = [
    path('analytics/', clinical_analytics, name='clinical_analytics'),
]
