from django.contrib import messages
from django.shortcuts import redirect, render
from django.contrib.auth.decorators import login_required
from django.db.models import Avg
from pathlib import Path

from .models import UploadedDataset
from .services import ETLService
from patients.models import Patient


def _upload_page_context():
    successful_uploads = UploadedDataset.objects.filter(
        status="SUCCESS"
    ).count()
    return {
        "recent_uploads": UploadedDataset.objects.order_by("-uploaded_at")[:4],
        "total_uploads": UploadedDataset.objects.count(),
        "successful_uploads": successful_uploads,
        "total_patients": Patient.objects.count(),
        "avg_imc": Patient.objects.aggregate(avg_imc=Avg("imc"))["avg_imc"],
    }


@login_required
def upload_csv(request):
    if request.method == "POST":
        csv_file = request.FILES.get("file")
        if not csv_file:
            messages.error(request, "Selecciona un archivo CSV.")
            return redirect("upload_csv")

        datasets_dir = Path("datasets")
        datasets_dir.mkdir(parents=True, exist_ok=True)
        file_path = datasets_dir / csv_file.name
        upload_record = UploadedDataset.objects.create(
            file_name=csv_file.name,
            stored_path=str(file_path),
        )

        with file_path.open("wb+") as destination:
            for chunk in csv_file.chunks():
                destination.write(chunk)

        try:
            df = ETLService.extract(file_path)
            upload_record.rows_received = len(df)
            upload_record.save(update_fields=["rows_received"])
            df = ETLService.transform(df)
            df["riesgo"] = df.apply(
                ETLService.classify_risk,
                axis=1,
            )

            total = ETLService.load(df)
        except Exception as exc:
            upload_record.mark_error(str(exc))
            messages.error(request, str(exc))
        else:
            upload_record.mark_processed(
                rows_processed=len(df),
                rows_inserted=total,
                notes="Carga completada desde la interfaz web.",
            )
            messages.success(
                request,
                f"{total} pacientes procesados y guardados en Supabase.",
            )

        return redirect("upload_csv")

    return render(request, "views/upload.html", _upload_page_context())
