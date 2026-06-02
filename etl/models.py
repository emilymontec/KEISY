from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User


class UploadedDataset(models.Model):
    STATUS_CHOICES = [
        ("PENDING", "Pendiente"),
        ("SUCCESS", "Procesado"),
        ("ERROR", "Error"),
    ]

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    file_name = models.CharField(max_length=255)
    stored_path = models.CharField(max_length=255)
    rows_received = models.PositiveIntegerField(default=0)
    rows_processed = models.PositiveIntegerField(default=0)
    rows_inserted = models.PositiveIntegerField(default=0)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="PENDING",
    )
    notes = models.TextField(blank=True)
    execution_time = models.FloatField(default=0.0) # Segundos
    uploaded_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-uploaded_at"]
        verbose_name = "Archivo cargado"
        verbose_name_plural = "Archivos cargados"

    def mark_processed(self, rows_processed, rows_inserted, execution_time=0.0, notes=""):
        self.rows_processed = rows_processed
        self.rows_inserted = rows_inserted
        self.status = "SUCCESS"
        self.execution_time = execution_time
        self.notes = notes
        self.processed_at = timezone.now()
        self.save(
            update_fields=[
                "rows_processed",
                "rows_inserted",
                "status",
                "execution_time",
                "notes",
                "processed_at",
            ]
        )

    def mark_error(self, notes, execution_time=0.0):
        self.status = "ERROR"
        self.notes = notes
        self.execution_time = execution_time
        self.processed_at = timezone.now()
        self.save(update_fields=["status", "notes", "execution_time", "processed_at"])

    def __str__(self):
        return self.file_name
