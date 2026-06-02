from django import forms
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from .models import Patient

class PatientForm(forms.ModelForm):
    class Meta:
        model = Patient
        fields = ['nombres', 'apellidos', 'documento', 'edad', 'sexo', 'peso', 'altura', 'imc', 'glucosa', 'colesterol', 'diagnostico', 'riesgo']
        widgets = {
            'nombres': forms.TextInput(attrs={'class': 'form-control'}),
            'apellidos': forms.TextInput(attrs={'class': 'form-control'}),
            'documento': forms.TextInput(attrs={'class': 'form-control'}),
            'edad': forms.NumberInput(attrs={'class': 'form-control'}),
            'sexo': forms.Select(attrs={'class': 'form-select'}),
            'peso': forms.NumberInput(attrs={'class': 'form-control'}),
            'altura': forms.NumberInput(attrs={'class': 'form-control'}),
            'imc': forms.NumberInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
            'glucosa': forms.NumberInput(attrs={'class': 'form-control'}),
            'colesterol': forms.NumberInput(attrs={'class': 'form-control'}),
            'diagnostico': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'riesgo': forms.Select(attrs={'class': 'form-select'}),
        }

class PatientBaseView(LoginRequiredMixin):
    model = Patient
    success_url = reverse_lazy('admin_panel')
    form_class = PatientForm

class PatientCreateView(PatientBaseView, UserPassesTestMixin, CreateView):
    template_name = 'patients/patient_form.html'
    def test_func(self):
        return self.request.user.is_superuser or self.request.user.groups.filter(name__in=['Administrador', 'Medico']).exists()

class PatientUpdateView(PatientBaseView, UserPassesTestMixin, UpdateView):
    template_name = 'patients/patient_form.html'
    def test_func(self):
        return self.request.user.is_superuser or self.request.user.groups.filter(name__in=['Administrador', 'Medico']).exists()

class PatientDeleteView(PatientBaseView, UserPassesTestMixin, DeleteView):
    template_name = 'patients/patient_confirm_delete.html'
    def test_func(self):
        return self.request.user.is_superuser or self.request.user.groups.filter(name='Administrador').exists()


class PatientDetailView(PatientBaseView, UpdateView): # Reusing update for view/edit
    template_name = 'patients/patient_detail.html'

