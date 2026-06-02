from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .services import MLService
from django.contrib import messages

@login_required
def predict_individual(request):
    result = None
    error = None
    
    if request.method == 'POST':
        try:
            age = int(request.POST.get('edad'))
            weight = float(request.POST.get('peso'))
            height = float(request.POST.get('altura'))
            glucose = float(request.POST.get('glucosa'))
            pressure = int(request.POST.get('presion'))
            
            result, error = MLService.predict_risk(age, weight, height, glucose, pressure)
            if error:
                messages.error(request, error)
        except (ValueError, TypeError):
            messages.error(request, "Por favor, ingresa valores válidos en todos los campos.")
            
    return render(request, 'ml/predict.html', {'result': result})

@login_required
def train_model_view(request):
    success, msg = MLService.train_model()
    if success:
        messages.success(request, msg)
    else:
        messages.error(request, msg)
    return render(request, 'ml/predict.html')
