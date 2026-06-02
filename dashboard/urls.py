from django.urls import path
from .views import home, admin_panel

urlpatterns = [
    path('', home, name='home'),
    path('admin-panel/', admin_panel, name='admin_panel'),
]