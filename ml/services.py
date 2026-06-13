import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score, confusion_matrix
)
import joblib
import os
import io
import matplotlib
matplotlib.use("Agg")  # Use non-interactive backend
import matplotlib.pyplot as plt
import seaborn as sns
from patients.models import Patient
from django.conf import settings
from .models import ModelTraining, PredictionHistory
from django.db.models import Avg


class MLService:
    MODEL_PATH = os.path.join(settings.BASE_DIR, "ml", "risk_model.joblib")
    FEATURES = [
        "edad", "imc", "glucosa", "colesterol", "presion_sistolica", "frecuencia_cardiaca"
    ]
    RISK_CLASSES = ["BAJO", "MEDIO", "ALTO", "CRITICO"]
    RISK_MAP = {"BAJO": 0, "MEDIO": 1, "ALTO": 2, "CRITICO": 3}

    @classmethod
    def train_model(cls):
        patients = Patient.objects.all()
        if patients.count() < 10:
            return False, "Insuficientes datos para entrenar (mínimo 10 registros)."

        # Extract data
        data = []
        for p in patients:
            data.append({
                "edad": p.edad,
                "imc": p.imc,
                "glucosa": p.glucosa,
                "colesterol": p.colesterol,
                "presion_sistolica": p.presion_sistolica,
                "frecuencia_cardiaca": p.frecuencia_cardiaca,
                "riesgo": p.riesgo
            })

        df = pd.DataFrame(data)
        df = df.dropna()

        if len(df) < 10:
            return False, "Insuficientes registros completos después de limpiar datos."

        # Train-test split
        X = df[cls.FEATURES]
        y = df["riesgo"].map(cls.RISK_MAP)

        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )

        # Train model
        model = RandomForestClassifier(n_estimators=100, random_state=42, class_weight='balanced')
        model.fit(X_train, y_train)

        # Predict on test set
        y_pred = model.predict(X_test)

        # Calculate metrics
        accuracy = accuracy_score(y_test, y_pred)
        precision = precision_score(y_test, y_pred, average="macro", zero_division=0)
        recall = recall_score(y_test, y_pred, average="macro", zero_division=0)
        f1 = f1_score(y_test, y_pred, average="macro", zero_division=0)

        # Generate confusion matrix
        cm = confusion_matrix(y_test, y_pred)
        img_buffer = cls._plot_confusion_matrix(cm, cls.RISK_CLASSES)

        # Save model
        joblib.dump(model, cls.MODEL_PATH)

        # Save training record
        ModelTraining.objects.filter(is_active=True).update(is_active=False)
        training_record = ModelTraining.objects.create(
            model_type="Random Forest Classifier",
            total_records=len(df),
            training_records=len(X_train),
            test_records=len(X_test),
            accuracy=accuracy,
            precision_macro=precision,
            recall_macro=recall,
            f1_macro=f1,
            is_active=True
        )
        training_record.save_confusion_matrix(img_buffer)

        return True, "Modelo entrenado exitosamente."

    @classmethod
    def _plot_confusion_matrix(cls, cm, class_names):
        plt.figure(figsize=(8, 6))
        sns.heatmap(
            cm, annot=True, fmt="d", cmap="Blues",
            xticklabels=class_names,
            yticklabels=class_names
        )
        plt.title("Matriz de Confusión")
        plt.xlabel("Predicción")
        plt.ylabel("Valor Real")

        buf = io.BytesIO()
        plt.savefig(buf, format="png", bbox_inches="tight", dpi=100)
        plt.close()
        return buf

    @classmethod
    def get_latest_training(cls):
        return ModelTraining.objects.filter(is_active=True).first()

    @classmethod
    def predict_risk(cls, age, weight, height, glucose, pressure, patient=None):
        if not os.path.exists(cls.MODEL_PATH):
            success, msg = cls.train_model()
            if not success:
                return None, msg

        model = joblib.load(cls.MODEL_PATH)
        imc = round(weight / (height ** 2), 2)

        avg_colesterol = Patient.objects.aggregate(Avg("colesterol"))["colesterol__avg"] or 200
        avg_frecuencia = Patient.objects.aggregate(Avg("frecuencia_cardiaca"))["frecuencia_cardiaca__avg"] or 75

        X_input = pd.DataFrame([{
            "edad": age,
            "imc": imc,
            "glucosa": glucose,
            "colesterol": avg_colesterol,
            "presion_sistolica": pressure,
            "frecuencia_cardiaca": avg_frecuencia
        }])

        prediction = model.predict(X_input)[0]
        probabilities = model.predict_proba(X_input)[0]
        riesgo_final = cls.RISK_CLASSES[int(prediction)]
        max_prob = round(max(probabilities) * 100, 2)

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

        if riesgos_especificos:
            diagnostico_riesgo = f"Riesgo de: {', '.join(set(riesgos_especificos))}"
        else:
            diagnostico_riesgo = "Sin riesgos patológicos específicos detectados"

        # Save prediction history if patient is provided
        input_data = {
            "edad": age,
            "peso": weight,
            "altura": height,
            "imc": imc,
            "glucosa": glucose,
            "colesterol": avg_colesterol,
            "presion_sistolica": pressure,
            "frecuencia_cardiaca": avg_frecuencia
        }

        PredictionHistory.objects.create(
            patient=patient,
            predicted_risk=riesgo_final,
            actual_risk=patient.riesgo if patient else None,
            probability=max_prob,
            input_data=input_data
        )

        return {
            "riesgo": riesgo_final,
            "probabilidad": max_prob,
            "imc": imc,
            "factores": factores,
            "diagnostico_riesgo": diagnostico_riesgo
        }, None

    @classmethod
    def get_recent_predictions(cls, limit=10):
        return PredictionHistory.objects.select_related("patient").all()[:limit]
