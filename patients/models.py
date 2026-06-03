from django.db import models
from django.contrib.auth.models import User

# Create your models here.

class Patient(models.Model):

    RISK_CHOICES = [
        ('BAJO', 'BAJO'),
        ('MEDIO', 'MEDIO'),
        ('ALTO', 'ALTO'),
        ('CRITICO', 'CRITICO'),
    ]

    SEX_CHOICES = [
        ('M', 'Masculino'),
        ('F', 'Femenino'),
    ]

    nombres = models.CharField(max_length=100)
    apellidos = models.CharField(max_length=100)
    documento = models.CharField(max_length=20, unique=True, null=True, blank=True)
    edad = models.IntegerField()
    sexo = models.CharField(
        max_length=1,
        choices=SEX_CHOICES
    )
    peso = models.FloatField()
    altura = models.FloatField()
    imc = models.FloatField()
    glucosa = models.FloatField()
    colesterol = models.FloatField()
    presion_sistolica = models.IntegerField(default=120)
    presion_diastolica = models.IntegerField(default=80)
    saturacion_oxigeno = models.FloatField(default=95)
    frecuencia_cardiaca = models.IntegerField(default=75)
    diagnostico = models.TextField(null=True, blank=True)
    es_hipertenso = models.BooleanField(default=False)
    es_diabetico = models.BooleanField(default=False)
    es_fumador = models.BooleanField(default=False)
    riesgo = models.CharField(
        max_length=20,
        choices=RISK_CHOICES
    )

    fecha_consulta = models.DateField(
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return f"{self.nombres} {self.apellidos}"

    def get_alerts(self):
        alerts = []
        if self.glucosa > 300:
            alerts.append({'type': 'CRITICO', 'msg': f'Glucosa crítica: {self.glucosa} mg/dL'})
        elif self.glucosa > 200:
            alerts.append({'type': 'ALTO', 'msg': f'Glucosa elevada: {self.glucosa} mg/dL'})

        if self.presion_sistolica > 180:
            alerts.append({'type': 'CRITICO', 'msg': f'Crisis hipertensiva: {self.presion_sistolica}/{self.presion_diastolica}'})
        elif self.presion_sistolica > 140:
            alerts.append({'type': 'ALTO', 'msg': f'Hipertensión detectada: {self.presion_sistolica}/{self.presion_diastolica}'})

        if self.saturacion_oxigeno < 85:
            alerts.append({'type': 'CRITICO', 'msg': f'Hipoxia severa: {self.saturacion_oxigeno}% SpO2'})
        elif self.saturacion_oxigeno < 90:
            alerts.append({'type': 'ALTO', 'msg': f'Saturación baja: {self.saturacion_oxigeno}% SpO2'})

        if self.frecuencia_cardiaca > 120:
            alerts.append({'type': 'ALTO', 'msg': f'Taquicardia: {self.frecuencia_cardiaca} lpm'})
        elif self.frecuencia_cardiaca < 50:
            alerts.append({'type': 'ALTO', 'msg': f'Bradicardia: {self.frecuencia_cardiaca} lpm'})

        if self.imc > 35:
            alerts.append({'type': 'MEDIO', 'msg': f'Obesidad grado II/III: IMC {self.imc}'})

        return alerts

    def get_risk_explanation(self):
        factors = []
        if self.glucosa > 126:
            factors.append("Glucosa elevada")
        if self.imc > 30:
            factors.append("IMC obesidad")
        if self.presion_sistolica > 140:
            factors.append("Presión sistólica alta")
        if self.es_fumador:
            factors.append("Hábito tabáquico")
        if self.es_diabetico:
            factors.append("Antecedente de diabetes")
        if self.es_hipertenso:
            factors.append("Antecedente de hipertensión")
        if self.saturacion_oxigeno < 90:
            factors.append("Saturación de oxígeno baja")
        
        return factors

class PatientAudit(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='audit_logs')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=50) # Created, Updated, Deleted
    changes = models.JSONField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.patient} - {self.action} by {self.user} at {self.timestamp}"
