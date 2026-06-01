from django.db import models
from django.utils import timezone


class UploadedDataset(models.Model):
    STATUS_CHOICES = [
        ("PENDING", "Pendiente"),
        ("SUCCESS", "Procesado"),
        ("ERROR", "Error"),
    ]

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
    uploaded_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-uploaded_at"]
        verbose_name = "Archivo cargado"
        verbose_name_plural = "Archivos cargados"

    def mark_processed(self, rows_processed, rows_inserted, notes=""):
        self.rows_processed = rows_processed
        self.rows_inserted = rows_inserted
        self.status = "SUCCESS"
        self.notes = notes
        self.processed_at = timezone.now()
        self.save(
            update_fields=[
                "rows_processed",
                "rows_inserted",
                "status",
                "notes",
                "processed_at",
            ]
        )

    def mark_error(self, notes):
        self.status = "ERROR"
        self.notes = notes
        self.processed_at = timezone.now()
        self.save(update_fields=["status", "notes", "processed_at"])

    def __str__(self):
        return self.file_name
