from django.contrib import admin
from .models import Patient


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = (
        "nombres",
        "apellidos",
        "edad",
        "sexo",
        "imc",
        "glucosa",
        "riesgo",
        "created_at",
    )
    list_filter = ("sexo", "riesgo", "created_at")
    search_fields = ("nombres", "apellidos")
    ordering = ("-created_at",)
