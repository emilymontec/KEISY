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