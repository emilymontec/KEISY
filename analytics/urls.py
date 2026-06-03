from django.urls import path
from .views import clinical_analytics, analytical_chat

urlpatterns = [
    path('analytics/', clinical_analytics, name='clinical_analytics'),
    path('chat/', analytical_chat, name='analytical_chat'),
]
