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
        
        if "reset_data" in request.POST:
            ETLService.reset_all_data()
            messages.success(request, "Todos los datos clínicos y registros de carga han sido eliminados.")
            return redirect("upload_csv")



        # Manejo de confirmación de archivo repetido
        is_confirmed = request.POST.get("confirm_upload") == "true"
        pending_filename = request.POST.get("pending_filename")
        
        if is_confirmed and pending_filename:
            file_path = Path("datasets") / pending_filename
            file_hash = request.POST.get("file_hash")
        else:
            uploaded_file = request.FILES.get("file")
            if not uploaded_file:
                messages.error(request, "Selecciona un archivo (CSV, XLSX o JSON).")
                return redirect("upload_csv")

            datasets_dir = Path("datasets")
            datasets_dir.mkdir(parents=True, exist_ok=True)
            file_path = datasets_dir / uploaded_file.name
            
            # Guardar temporalmente para calcular hash y verificar duplicados
            with file_path.open("wb+") as destination:
                for chunk in uploaded_file.chunks():
                    destination.write(chunk)
            
            file_hash = ETLService.calculate_hash(file_path)
            
            # Verificar si el archivo ya existe
            existing_file = UploadedDataset.objects.filter(file_name=uploaded_file.name).first()
            
            if existing_file:
                if existing_file.file_hash == file_hash:
                    messages.warning(request, f"El archivo '{uploaded_file.name}' ya fue cargado con el mismo contenido.")
                else:
                    messages.info(request, f"El archivo '{uploaded_file.name}' ya existe pero tiene contenido diferente.")
                
                # Pasar a la plantilla que se requiere confirmación
                context = _upload_page_context()
                context["pending_file"] = uploaded_file.name
                context["file_hash"] = file_hash
                return render(request, "etl/upload_csv.html", context)

        # Si llegamos aquí, es una carga nueva o confirmada
        # Primero, verificar que el archivo existe (importante para el caso confirmado)
        if not file_path.exists():
            messages.error(request, f"Archivo '{file_path.name}' no encontrado en el servidor. Por favor, súbelo nuevamente.")
            return redirect("upload_csv")
            
        upload_record = UploadedDataset.objects.create(
            user=request.user,
            file_name=file_path.name,
            stored_path=str(file_path),
            file_hash=file_hash
        )

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
                f"{total} registros procesados/actualizados. (Duplicados en archivo: {etl_logs['duplicates_removed']})",
            )

        return redirect("upload_csv")

    return render(request, "etl/upload_csv.html", _upload_page_context())
