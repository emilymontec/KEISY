from django.contrib import messages
from django.shortcuts import redirect, render
from django.contrib.auth.decorators import login_required
from django.db.models import Avg
from pathlib import Path
import time

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
        start_time = time.time()
        
        if "generate_simulated" in request.POST:
            try:
                df = ETLService.generate_simulated_dataset()
                # Para simular la carga, lo guardamos temporalmente
                datasets_dir = Path("datasets")
                datasets_dir.mkdir(parents=True, exist_ok=True)
                file_path = datasets_dir / "simulated_dataset.csv"
                df.to_csv(file_path, index=False)
                
                upload_record = UploadedDataset.objects.create(
                    user=request.user,
                    file_name="simulated_dataset.csv",
                    stored_path=str(file_path),
                    rows_received=len(df)
                )
                
                df_transformed, etl_logs = ETLService.transform(df)
                total = ETLService.load(df_transformed)
                
                execution_time = round(time.time() - start_time, 2)
                notes = f"Simulado. Duplicados: {etl_logs['duplicates_removed']}, Imputados: {etl_logs['nulls_imputed']}"
                upload_record.mark_processed(
                    rows_processed=len(df_transformed),
                    rows_inserted=total,
                    execution_time=execution_time,
                    notes=notes,
                )
                messages.success(request, f"Simulado: {total} registros (Limpieza: {etl_logs['duplicates_removed']} dupl. eliminados).")
            except Exception as exc:
                execution_time = round(time.time() - start_time, 2)
                messages.error(request, f"Error al generar dataset: {str(exc)}")
            return redirect("upload_csv")

        uploaded_file = request.FILES.get("file")
        if not uploaded_file:
            messages.error(request, "Selecciona un archivo (CSV, XLSX o JSON).")
            return redirect("upload_csv")

        datasets_dir = Path("datasets")
        datasets_dir.mkdir(parents=True, exist_ok=True)
        file_path = datasets_dir / uploaded_file.name
        upload_record = UploadedDataset.objects.create(
            user=request.user,
            file_name=uploaded_file.name,
            stored_path=str(file_path),
        )

        with file_path.open("wb+") as destination:
            for chunk in uploaded_file.chunks():
                destination.write(chunk)

        try:
            df = ETLService.extract(file_path)
            upload_record.rows_received = len(df)
            upload_record.save(update_fields=["rows_received"])
            
            df_transformed, etl_logs = ETLService.transform(df)
            total = ETLService.load(df_transformed)
        except Exception as exc:
            execution_time = round(time.time() - start_time, 2)
            upload_record.mark_error(str(exc), execution_time=execution_time)
            messages.error(request, str(exc))
        else:
            execution_time = round(time.time() - start_time, 2)
            notes = f"Carga web. Duplicados: {etl_logs['duplicates_removed']}, Imputados: {etl_logs['nulls_imputed']}, Coerced: {etl_logs['errors_coerced']}"
            upload_record.mark_processed(
                rows_processed=len(df_transformed),
                rows_inserted=total,
                execution_time=execution_time,
                notes=notes,
            )
            messages.success(
                request,
                f"{total} registros procesados. (Duplicados eliminados: {etl_logs['duplicates_removed']})",
            )

        return redirect("upload_csv")

    return render(request, "etl/upload_csv.html", _upload_page_context())
