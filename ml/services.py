import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
import joblib
import os
from patients.models import Patient
from django.conf import settings

from django.db.models import Avg

class MLService:
    MODEL_PATH = os.path.join(settings.BASE_DIR, 'ml', 'risk_model.joblib')
    
    @classmethod
    def train_model(cls):
        patients = Patient.objects.all()
        if patients.count() < 10:
            return False, "Insuficientes datos para entrenar (mínimo 10 registros)."
        
        data = []
        for p in patients:
            data.append({
                'edad': p.edad,
                'imc': p.imc,
                'glucosa': p.glucosa,
                'colesterol': p.colesterol,
                'presion_sistolica': p.presion_sistolica,
                'frecuencia_cardiaca': p.frecuencia_cardiaca,
                'riesgo': p.riesgo
            })
        
        df = pd.DataFrame(data)
        
        # Mapear riesgo a numérico
        risk_map = {'BAJO': 0, 'MEDIO': 1, 'ALTO': 2, 'CRITICO': 3}
        df['target'] = df['riesgo'].map(risk_map)
        
        # Eliminar nulos si los hay
        df = df.dropna()
        
        X = df[['edad', 'imc', 'glucosa', 'colesterol', 'presion_sistolica', 'frecuencia_cardiaca']]
        y = df['target']
        
        # Entrenar Random Forest
        model = RandomForestClassifier(n_estimators=100, random_state=42)
        model.fit(X, y)
        
        # Guardar modelo
        joblib.dump(model, cls.MODEL_PATH)
        return True, "Modelo entrenado exitosamente."

    @classmethod
    def predict_risk(cls, age, weight, height, glucose, pressure):
        if not os.path.exists(cls.MODEL_PATH):
            success, msg = cls.train_model()
            if not success:
                return None, msg
        
        model = joblib.load(cls.MODEL_PATH)
        imc = round(weight / (height ** 2), 2)
        
        avg_colesterol = Patient.objects.aggregate(Avg('colesterol'))['colesterol__avg'] or 200
        avg_frecuencia = Patient.objects.aggregate(Avg('frecuencia_cardiaca'))['frecuencia_cardiaca__avg'] or 75
        
        X_input = pd.DataFrame([{
            'edad': age,
            'imc': imc,
            'glucosa': glucose,
            'colesterol': avg_colesterol,
            'presion_sistolica': pressure,
            'frecuencia_cardiaca': avg_frecuencia
        }])
        
        prediction = model.predict(X_input)[0]
        probabilities = model.predict_proba(X_input)[0]
        
        risk_labels = {0: 'BAJO', 1: 'MEDIO', 2: 'ALTO', 3: 'CRITICO'}
        riesgo_final = risk_labels[prediction]
        
        # Identificar factores de riesgo específicos
        factores = []
        riesgos_especificos = []
        
        if glucose > 126: 
            factores.append("Hiperglucemia (Glucosa elevada)")
            riesgos_especificos.append("Diabetes Tipo 2")
        if pressure > 140: 
            factores.append("Hipertensión Arterial")
            riesgos_especificos.append("Enfermedad Cardiovascular")
        if imc > 30: 
            factores.append("Obesidad (IMC elevado)")
            riesgos_especificos.append("Síndrome Metabólico")
        if age > 65: 
            factores.append("Edad Avanzada (Factor de riesgo)")
            riesgos_especificos.append("Complicaciones Geriátricas")
        
        # Determinar diagnóstico principal de riesgo
        if riesgos_especificos:
            diagnostico_riesgo = f"Riesgo de: {', '.join(set(riesgos_especificos))}"
        else:
            diagnostico_riesgo = "Sin riesgos patológicos específicos detectados"
        
        return {
            'riesgo': riesgo_final,
            'probabilidad': round(max(probabilities) * 100, 2),
            'imc': imc,
            'factores': factores,
            'diagnostico_riesgo': diagnostico_riesgo
        }, None
