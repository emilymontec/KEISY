from django.urls import path
from django.contrib.auth import views as auth_views
from .views import custom_logout, favicon_view

urlpatterns = [
    path('login/', auth_views.LoginView.as_view(
        template_name='authentication/login.html',
        redirect_authenticated_user=True
    ), name='login'),
    path('logout/', custom_logout, name='logout'),
    path('favicon.ico', favicon_view, name='favicon'),
]
