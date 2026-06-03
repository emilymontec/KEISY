from django.db.models import Avg, Q, Count
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models.functions import TruncDay
from django.utils import timezone
from datetime import timedelta
import json

from etl.models import UploadedDataset
from patients.models import Patient


@login_required
def home(request):
    successful_uploads = UploadedDataset.objects.filter(
        status="SUCCESS"
    ).count()
    
    # Pacientes por sexo
    gender_stats = list(Patient.objects.values('sexo').annotate(total=Count('id')))
    
    # Distribución por edad
    age_ranges = {
        "Jóvenes (18-30)": Patient.objects.filter(edad__gte=18, edad__lte=30).count(),
        "Adultos (31-50)": Patient.objects.filter(edad__gte=31, edad__lte=50).count(),
        "Mayores (51-70)": Patient.objects.filter(edad__gte=51, edad__lte=70).count(),
        "Ancianos (71+)": Patient.objects.filter(edad__gte=71).count(),
    }
    
    # Diagnósticos frecuentes
    top_diagnoses = list(Patient.objects.values('diagnostico').annotate(total=Count('id')).order_by('-total')[:5])
    
    # Evolución Temporal (Últimos 30 días de pacientes críticos)
    today = timezone.now().date()
    start_date = today - timedelta(days=29)
    
    evolution_qs = Patient.objects.filter(
        riesgo="CRITICO",
        created_at__date__gte=start_date
    ).annotate(day=TruncDay('created_at')).values('day').annotate(total=Count('id')).order_by('day')
    
    # Mapear los datos a un diccionario para fácil acceso
    evolution_map = {item['day'].date(): item['total'] for item in evolution_qs}
    
    evolution_labels = []
    evolution_counts = []
    
    for i in range(30):
        current_date = start_date + timedelta(days=i)
        evolution_labels.append(current_date.strftime('%d/%m'))
        evolution_counts.append(evolution_map.get(current_date, 0))

    # Datos para gráficas (JSON)
    chart_data = {
        "gender": {
            "labels": [g['sexo'] for g in gender_stats],
            "data": [g['total'] for g in gender_stats]
        },
        "age": {
            "labels": list(age_ranges.keys()),
            "data": list(age_ranges.values())
        },
        "diagnoses": {
            "labels": [d['diagnostico'] for d in top_diagnoses],
            "data": [d['total'] for d in top_diagnoses]
        },
        "evolution": {
            "labels": evolution_labels,
            "data": evolution_counts
        }
    }

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
        "chart_data_json": json.dumps(chart_data),
        "age_ranges": age_ranges,
        "gender_stats": gender_stats,
        "top_diagnoses": top_diagnoses,
    }

    return render(request, "dashboard/index.html", context)


@login_required
def alert_center(request):
    # Obtener todos los pacientes con riesgo alto o crítico para las alertas iniciales
    all_patients = Patient.objects.all()
    
    patient_alerts = []
    for patient in all_patients:
        alerts = patient.get_alerts()
        if alerts:
            # Priorizar por el tipo más severo de alerta que tenga el paciente
            severity_order = {'CRITICO': 3, 'ALTO': 2, 'MEDIO': 1}
            max_severity = max([severity_order.get(a['type'], 0) for a in alerts])
            
            patient_alerts.append({
                'patient': patient,
                'alerts': alerts,
                'max_severity': max_severity
            })
    
    # Ordenar por severidad (Crítico primero)
    patient_alerts.sort(key=lambda x: x['max_severity'], reverse=True)
    
    # Top 10 pacientes para atención inmediata
    # Criterio: Riesgo CRITICO > ALTO, luego por número de alertas, luego por fecha creación
    top_10_patients = Patient.objects.filter(riesgo__in=['CRITICO', 'ALTO']).order_by(
        '-riesgo', # Esto funciona si el orden alfabético coincide o si usamos un Case/When
    )[:10]
    
    # Mejora del ordenamiento del Top 10 con Case/When para asegurar CRITICO > ALTO
    from django.db.models import Case, When, Value, IntegerField
    top_10_patients = Patient.objects.annotate(
        priority=Case(
            When(riesgo='CRITICO', then=Value(3)),
            When(riesgo='ALTO', then=Value(2)),
            When(riesgo='MEDIO', then=Value(1)),
            default=Value(0),
            output_field=IntegerField(),
        )
    ).filter(priority__gt=0).order_by('-priority', '-created_at')[:10]

    context = {
        'patient_alerts': patient_alerts,
        'top_10_patients': top_10_patients,
    }
    return render(request, 'patients/alert_center.html', context)


@login_required
def admin_panel(request):
    search_query = request.GET.get("q", "").strip()
    risk_filter = request.GET.get("risk", "").strip().upper()
    gender_filter = request.GET.get("gender", "").strip().upper()

    patients = Patient.objects.all().order_by("-created_at")

    if search_query:
        patients = patients.filter(
            Q(nombres__icontains=search_query) |
            Q(apellidos__icontains=search_query) |
            Q(documento__icontains=search_query) |
            Q(diagnostico__icontains=search_query)
        )

    if risk_filter:
        patients = patients.filter(riesgo=risk_filter)

    if gender_filter:
        patients = patients.filter(sexo=gender_filter)

    # Paginación
    paginator = Paginator(patients, 10)  # 10 pacientes por página
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    uploads = UploadedDataset.objects.all().order_by("-uploaded_at")
    filtered_count = patients.count()

    context = {
        "patients": page_obj,  # Usar el objeto paginado
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
    return render(request, "patients/patient_list.html", context)
