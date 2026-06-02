from django.db import models

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