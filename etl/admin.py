from django.contrib import admin
from .models import UploadedDataset


@admin.register(UploadedDataset)
class UploadedDatasetAdmin(admin.ModelAdmin):
    list_display = (
        "file_name",
        "user",
        "status",
        "rows_inserted",
        "execution_time",
        "uploaded_at",
    )
    list_filter = ("status", "uploaded_at", "user")
    search_fields = ("file_name", "notes", "user__username")
    ordering = ("-uploaded_at",)
    readonly_fields = (
        "user",
        "file_name",
        "stored_path",
        "rows_received",
        "rows_processed",
        "rows_inserted",
        "status",
        "execution_time",
        "notes",
        "uploaded_at",
        "processed_at",
    )
