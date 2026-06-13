from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .services import MLService
from .models import ModelTraining


@login_required
def ml_dashboard(request):
    latest_training = MLService.get_latest_training()
    recent_predictions = MLService.get_recent_predictions(limit=10)
    
    # Map features to nice titles
    feature_mapping = {
        "edad": "Edad",
        "imc": "Índice de Masa Corporal (IMC)",
        "glucosa": "Glucosa (mg/dL)",
        "colesterol": "Colesterol (mg/dL)",
        "presion_sistolica": "Presión Sistólica (mmHg)",
        "frecuencia_cardiaca": "Frecuencia Cardíaca (lpm)"
    }
    nice_features = [feature_mapping.get(f, f) for f in MLService.FEATURES]
    
    context = {
        "training": latest_training,
        "predictions": recent_predictions,
        "features": nice_features
    }
    return render(request, "ml/dashboard.html", context)


@login_required
def predict_individual(request):
    result = None
    error = None
    inputs = None

    if request.method == "POST":
        try:
            age = int(request.POST.get("edad"))
            weight = float(request.POST.get("peso"))
            height = float(request.POST.get("altura"))
            glucose = float(request.POST.get("glucosa"))
            pressure = int(request.POST.get("presion"))

            inputs = {
                "edad": age,
                "peso": weight,
                "altura": height,
                "glucosa": glucose,
                "presion": pressure
            }

            result, error = MLService.predict_risk(age, weight, height, glucose, pressure)
            if error:
                messages.error(request, error)
        except (ValueError, TypeError):
            messages.error(request, "Por favor, ingresa valores válidos en todos los campos.")

    return render(request, "ml/predict_individual.html", {"result": result, "inputs": inputs})


@login_required
def train_model_view(request):
    if request.method == "POST":
        success, msg = MLService.train_model()
        if success:
            messages.success(request, msg)
        else:
            messages.error(request, msg)
    return redirect("ml_dashboard")
