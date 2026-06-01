from django.contrib import admin
from .models import UploadedDataset


@admin.register(UploadedDataset)
class UploadedDatasetAdmin(admin.ModelAdmin):
    list_display = (
        "file_name",
        "status",
        "rows_received",
        "rows_processed",
        "rows_inserted",
        "uploaded_at",
    )
    list_filter = ("status", "uploaded_at")
    search_fields = ("file_name", "notes")
    ordering = ("-uploaded_at",)
    readonly_fields = (
        "file_name",
        "stored_path",
        "rows_received",
        "rows_processed",
        "rows_inserted",
        "status",
        "notes",
        "uploaded_at",
        "processed_at",
    )
