from django.contrib import messages
from django.shortcuts import redirect, render
from pathlib import Path

from .models import UploadedDataset
from .services import ETLService


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

    return render(request, "views/upload.html")
