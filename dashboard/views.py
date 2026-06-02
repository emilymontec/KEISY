from django.db.models import Avg, Q
from django.shortcuts import render
from django.contrib.auth.decorators import login_required

from etl.models import UploadedDataset
from patients.models import Patient


@login_required
def home(request):
    successful_uploads = UploadedDataset.objects.filter(
        status="SUCCESS"
    ).count()
    risk_summary = {
        "critico": Patient.objects.filter(riesgo="CRITICO").count(),
        "alto": Patient.objects.filter(riesgo="ALTO").count(),
        "medio": Patient.objects.filter(riesgo="MEDIO").count(),
        "bajo": Patient.objects.filter(riesgo="BAJO").count(),
    }
    context = {
        "total_patients": Patient.objects.count(),
        "total_uploads": UploadedDataset.objects.count(),
        "avg_imc": Patient.objects.aggregate(avg_imc=Avg("imc"))["avg_imc"],
        "recent_patients": Patient.objects.order_by("-created_at")[:6],
        "recent_uploads": UploadedDataset.objects.order_by("-uploaded_at")[:5],
        "risk_summary": risk_summary,
        "successful_uploads": successful_uploads,
    }

    return render(request, "index.html", context)


@login_required
def admin_panel(request):
    search_query = request.GET.get("q", "").strip()
    risk_filter = request.GET.get("risk", "").strip().upper()
    gender_filter = request.GET.get("gender", "").strip().upper()

    patients = Patient.objects.all().order_by("-created_at")

    if search_query:
        patients = patients.filter(
            Q(nombres__icontains=search_query) |
            Q(apellidos__icontains=search_query)
        )

    if risk_filter:
        patients = patients.filter(riesgo=risk_filter)

    if gender_filter:
        patients = patients.filter(sexo=gender_filter)

    uploads = UploadedDataset.objects.all().order_by("-uploaded_at")
    filtered_count = patients.count()

    context = {
        "patients": patients,
        "uploads": uploads,
        "search_query": search_query,
        "risk_filter": risk_filter,
        "gender_filter": gender_filter,
        "filtered_count": filtered_count,
        "total_patients": Patient.objects.count(),
        "critical_count": Patient.objects.filter(riesgo="CRITICO").count(),
        "success_uploads": UploadedDataset.objects.filter(
            status="SUCCESS"
        ).count(),
        "total_uploads": UploadedDataset.objects.count(),
    }
    return render(request, "views/admin_panel.html", context)
