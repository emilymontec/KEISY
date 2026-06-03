from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Count
from patients.models import Patient
import pandas as pd
import numpy as np
from scipy import stats
import json

@login_required
def clinical_analytics(request):
    patients_qs = Patient.objects.all()
    total_patients = patients_qs.count()
    
    if total_patients == 0:
        return render(request, 'analytics/clinical_analytics.html', {'total_patients': 0})

    # KPIs
    hypertensive_count = patients_qs.filter(es_hipertenso=True).count()
    diabetic_count = patients_qs.filter(es_diabetico=True).count()
    smoker_count = patients_qs.filter(es_fumador=True).count()
    
    # Convert to DataFrame for complex stats
    df = pd.DataFrame(list(patients_qs.values('edad', 'imc', 'glucosa', 'colesterol', 'sexo', 'riesgo')))
    
    # Risk average (mapping risk to numeric for average)
    risk_map = {'BAJO': 1, 'MEDIO': 2, 'ALTO': 3, 'CRITICO': 4}
    df['riesgo_num'] = df['riesgo'].map(risk_map)
    avg_risk_num = df['riesgo_num'].mean()
    avg_risk_label = [k for k, v in risk_map.items() if v == round(avg_risk_num)][0]

    # Statistics function
    def get_stats(series):
        return {
            'mean': round(series.mean(), 2),
            'median': round(series.median(), 2),
            'mode': round(series.mode()[0], 2) if not series.mode().empty else 0,
            'std': round(series.std(), 2)
        }

    stats_data = {
        'edad': get_stats(df['edad']),
        'imc': get_stats(df['imc']),
        'glucosa': get_stats(df['glucosa']),
        'colesterol': get_stats(df['colesterol']),
    }

    # Segmentation
    # By Age
    age_bins = [0, 18, 30, 50, 70, 100]
    age_labels = ['0-18', '19-30', '31-50', '51-70', '71+']
    df['age_group'] = pd.cut(df['edad'], bins=age_bins, labels=age_labels)
    age_segmentation = df['age_group'].value_counts().to_dict()

    # By Sex
    sex_segmentation = df['sexo'].value_counts().to_dict()

    # By IMC
    imc_bins = [0, 18.5, 25, 30, 100]
    imc_labels = ['Bajo peso', 'Normal', 'Sobrepeso', 'Obesidad']
    df['imc_group'] = pd.cut(df['imc'], bins=imc_bins, labels=imc_labels)
    imc_segmentation = df['imc_group'].value_counts().to_dict()

    # By Risk
    risk_segmentation = df['riesgo'].value_counts().to_dict()

    chart_data = {
        'age': {'labels': list(age_segmentation.keys()), 'data': list(age_segmentation.values())},
        'sex': {'labels': list(sex_segmentation.keys()), 'data': list(sex_segmentation.values())},
        'imc': {'labels': list(imc_segmentation.keys()), 'data': list(imc_segmentation.values())},
        'risk': {'labels': list(risk_segmentation.keys()), 'data': list(risk_segmentation.values())},
    }

    context = {
        'total_patients': total_patients,
        'hypertensive_count': hypertensive_count,
        'diabetic_count': diabetic_count,
        'smoker_count': smoker_count,
        'avg_risk_label': avg_risk_label,
        'stats_data': stats_data,
        'chart_data_json': json.dumps(chart_data)
    }

    return render(request, 'analytics/clinical_analytics.html', context)

@login_required
def analytical_chat(request):
    answer = None
    query = request.GET.get('q', '').lower().strip()
    
    if query:
        # Lógica de respuestas predefinidas (Chat Analítico sin LLM)
        if 'cuántos pacientes críticos' in query or 'cuantos pacientes criticos' in query:
            count = Patient.objects.filter(riesgo='CRITICO').count()
            answer = f"Actualmente existen {count} pacientes críticos."
        elif 'cuántos pacientes hay' in query or 'cuantos pacientes hay' in query or 'total de pacientes' in query:
            count = Patient.objects.count()
            answer = f"El sistema tiene registrados un total de {count} pacientes."
        elif 'riesgo alto' in query:
            count = Patient.objects.filter(riesgo='ALTO').count()
            answer = f"Hay {count} pacientes clasificados con riesgo alto."
        elif 'diabéticos' in query or 'diabeticos' in query:
            count = Patient.objects.filter(es_diabetico=True).count()
            answer = f"Se han identificado {count} pacientes con diagnóstico de diabetes."
        elif 'hipertensos' in query:
            count = Patient.objects.filter(es_hipertenso=True).count()
            answer = f"Contamos con {count} pacientes hipertensos registrados."
        elif 'promedio de edad' in query or 'edad promedio' in query:
            avg_age = Patient.objects.aggregate(Avg('edad'))['edad__avg']
            answer = f"La edad promedio de los pacientes es de {round(avg_age, 1)} años."
        elif 'imc promedio' in query or 'promedio de imc' in query:
            avg_imc = Patient.objects.aggregate(Avg('imc'))['imc__avg']
            answer = f"El índice de masa corporal (IMC) promedio es de {round(avg_imc, 2)}."
        else:
            answer = "Lo siento, no tengo una respuesta predefinida para esa consulta. Prueba preguntando por pacientes críticos, hipertensos, diabéticos o promedios generales."

    return render(request, 'analytics/analytical_chat.html', {'answer': answer, 'query': query})
