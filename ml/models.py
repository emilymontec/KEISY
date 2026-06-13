from django.db import models
from django.utils import timezone
import base64


class ModelTraining(models.Model):
    """
    Registro de entrenamientos del modelo ML
    """
    model_type = models.CharField(max_length=50, default="Random Forest Classifier")
    training_date = models.DateTimeField(default=timezone.now)
    total_records = models.IntegerField(default=0)
    training_records = models.IntegerField(default=0)
    test_records = models.IntegerField(default=0)
    accuracy = models.FloatField(default=0.0)
    precision_macro = models.FloatField(default=0.0)
    recall_macro = models.FloatField(default=0.0)
    f1_macro = models.FloatField(default=0.0)
    confusion_matrix_image = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-training_date"]

    def save_confusion_matrix(self, img_buffer):
        img_buffer.seek(0)
        self.confusion_matrix_image = base64.b64encode(img_buffer.read()).decode("utf-8")
        img_buffer.close()
        self.save()

    def __str__(self):
        return f"{self.model_type} - {self.training_date.strftime('%Y-%m-%d')}"


class PredictionHistory(models.Model):
    """
    Historial de predicciones de pacientes
    """
    patient = models.ForeignKey(
        "patients.Patient", on_delete=models.CASCADE, null=True, blank=True
    )
    prediction_date = models.DateTimeField(default=timezone.now)
    predicted_risk = models.CharField(max_length=20, choices=[
        ("BAJO", "BAJO"),
        ("MEDIO", "MEDIO"),
        ("ALTO", "ALTO"),
        ("CRITICO", "CRITICO")
    ])
    actual_risk = models.CharField(max_length=20, choices=[
        ("BAJO", "BAJO"),
        ("MEDIO", "MEDIO"),
        ("ALTO", "ALTO"),
        ("CRITICO", "CRITICO")
    ], null=True, blank=True)
    probability = models.FloatField(default=0.0)
    input_data = models.JSONField(default=dict)

    class Meta:
        ordering = ["-prediction_date"]

    def __str__(self):
        patient_name = self.patient.nombres if self.patient else "Predicción Individual"
        return f"{patient_name} - {self.predicted_risk} ({self.prediction_date.strftime('%Y-%m-%d')})"
