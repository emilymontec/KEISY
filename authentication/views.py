from django.contrib.auth import logout, update_session_auth_hash
from django.shortcuts import redirect, render
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.forms import PasswordChangeForm
from django import forms
from django.contrib.auth.models import User

class UserProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombres'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Apellidos'}),
        }

def custom_logout(request):
    logout(request)
    return redirect('login')

def favicon_view(request):
    return HttpResponse(status=204)

@login_required
def profile_view(request):
    user_form = UserProfileForm(instance=request.user)
    password_form = PasswordChangeForm(request.user)

    if request.method == 'POST':
        if 'update_profile' in request.POST:
            user_form = UserProfileForm(request.POST, instance=request.user)
            if user_form.is_valid():
                user_form.save()
                messages.success(request, 'Tu perfil ha sido actualizado correctamente.')
                return redirect('profile')
        
        elif 'change_password' in request.POST:
            password_form = PasswordChangeForm(request.user, request.POST)
            if password_form.is_valid():
                user = password_form.save()
                update_session_auth_hash(request, user)  # Mantiene la sesión iniciada
                messages.success(request, 'Tu contraseña ha sido cambiada con éxito.')
                return redirect('profile')
            else:
                messages.error(request, 'Por favor corrige los errores en el formulario de contraseña.')

    context = {
        'user_form': user_form,
        'password_form': password_form,
    }
    return render(request, 'authentication/profile.html', context)
