from django.db.models import Avg
from django.shortcuts import render

from etl.models import UploadedDataset
from patients.models import Patient


def home(request):
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
    }

    return render(request, "index.html", context)
