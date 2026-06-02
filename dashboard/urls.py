from django.urls import path
from .views import home, admin_panel, alert_center

urlpatterns = [
    path('', home, name='home'),
    path('admin-panel/', admin_panel, name='admin_panel'),
    path('alert-center/', alert_center, name='alert_center'),
]