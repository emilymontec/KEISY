import pandas as pd
import numpy as np
import unicodedata
import re
import hashlib
import json
from pathlib import Path

from patients.models import Patient
from django.db import transaction


class ETLService:
    COLUMN_ALIASES = {
        "nombre": "nombres",
        "nombres_paciente": "nombres",
        "first_name": "nombres",
        "apellido": "apellidos",
        "last_name": "apellidos",
        "genero": "sexo",
        "gender": "sexo",
        "sex": "sexo",
        "id_paciente": "documento",
        "patient_id": "documento",
        "identificacion": "documento",
        "numero_documento": "documento",
        "num_documento": "documento",
        "peso_kg": "peso",
        "height": "altura",
        "altura_m": "altura",
        "glucose": "glucosa",
        "cholesterol": "colesterol",
        "systolic_pressure": "presion_sistolica",
        "presion_arterial_sistolica": "presion_sistolica",
        "diastolic_pressure": "presion_diastolica",
        "presion_arterial_diastolica": "presion_diastolica",
        "spo2": "saturacion_oxigeno",
        "sat_oxigeno": "saturacion_oxigeno",
        "saturacion_de_oxigeno": "saturacion_oxigeno",
        "heart_rate": "frecuencia_cardiaca",
        "fc": "frecuencia_cardiaca",
        "diagnostico_preliminar": "diagnostico",
        "diagnosis": "diagnostico",
        "riesgo_enfermedad": "riesgo",
    }

    @staticmethod
    def calculate_hash(file_path):
        """Calcula el hash SHA-256 de un archivo."""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    REQUIRED_COLUMNS = [
        "nombres",
        "apellidos",
        "edad",
        "sexo",
        "peso",
        "altura",
        "glucosa",
        "colesterol",
    ]
    
    NUMERIC_COLUMNS = [
        "edad", "peso", "altura", "glucosa", "colesterol", 
        "presion_sistolica", "presion_diastolica", "frecuencia_cardiaca", 
        "saturacion_oxigeno", "imc"
    ]

    @staticmethod
    def _read_csv(file_path):
        read_attempts = (
            {"sep": ",", "encoding": "utf-8-sig"},
            {"sep": ",", "encoding": "latin1"},
            {"sep": ";", "encoding": "utf-8-sig"},
            {"sep": ";", "encoding": "latin1"},
            {"sep": "\t", "encoding": "utf-8-sig"},
            {"sep": "\t", "encoding": "latin1"},
        )
        last_error = None
        for options in read_attempts:
            try:
                return pd.read_csv(file_path, **options)
            except Exception as exc:
                last_error = exc
        raise last_error

    @staticmethod
    def _read_json(file_path):
        try:
            json_df = pd.read_json(file_path)
            if isinstance(json_df, pd.DataFrame):
                if len(json_df.columns) == 1 and json_df.columns[0] in {
                    "records",
                    "data",
                    "patients",
                    "result",
                }:
                    nested_records = json_df.iloc[:, 0].tolist()
                    if nested_records and all(
                        isinstance(record, dict) for record in nested_records
                    ):
                        return pd.DataFrame(nested_records)
                    if nested_records and isinstance(nested_records[0], list):
                        return pd.DataFrame(nested_records[0])
                return json_df
        except ValueError:
            pass

        with open(file_path, "r", encoding="utf-8-sig") as source:
            payload = json.load(source)

        if isinstance(payload, dict):
            for key in ("records", "data", "patients", "result"):
                nested_records = payload.get(key)
                if isinstance(nested_records, list):
                    return pd.DataFrame(nested_records)
            return pd.DataFrame([payload])

        if isinstance(payload, list):
            return pd.DataFrame(payload)

        raise ValueError("El JSON debe contener una lista de registros o un objeto con datos tabulares.")

    @staticmethod
    def extract(file_path):
        ext = Path(file_path).suffix.lower()
        try:
            if ext == '.csv':
                return ETLService._read_csv(file_path)
            elif ext == '.xlsx':
                return pd.read_excel(file_path, engine='openpyxl')
            elif ext == '.json':
                return ETLService._read_json(file_path)
            else:
                raise ValueError(f"Formato de archivo no soportado: {ext}")
        except Exception as e:
            raise ValueError(f"Error al leer el archivo {ext}: {str(e)}")

    @classmethod
    def _standardize_columns(cls, df):
        """Mapea encabezados equivalentes al esquema interno sin perder datos."""
        df = df.copy()
        for column in list(df.columns):
            target_column = cls.COLUMN_ALIASES.get(column, column)
            if target_column == column:
                continue

            if target_column in df.columns:
                df[target_column] = df[target_column].combine_first(df[column])
                df = df.drop(columns=[column])
            else:
                df = df.rename(columns={column: target_column})
        return df

    @classmethod
    def transform(cls, df):
        logs = {
            "total_received": len(df),
            "duplicates_removed": 0,
            "nulls_imputed": 0,
            "errors_coerced": 0,
            "transformed": 0
        }

        # 1. Normalizar nombres de columnas (quitar acentos, espacios, lowercase)
        df.columns = [cls._clean_column_name(col) for col in df.columns]
        
        # 2. Aplicar aliases de columnas
        df = cls._standardize_columns(df)
        
        # 3. Validar que existan las columnas requeridas
        cls._validate_columns(df)

        # 4. Eliminar duplicados
        initial_len = len(df)
        df = df.drop_duplicates().reset_index(drop=True)
        logs["duplicates_removed"] = initial_len - len(df)

        # 5. Convertir tipos numéricos (coerce)
        for col in cls.NUMERIC_COLUMNS:
            if col in df.columns:
                # Contar cuántos fallarán la conversión para el log
                pre_nulls = df[col].isna().sum()
                df[col] = pd.to_numeric(df[col], errors='coerce')
                post_nulls = df[col].isna().sum()
                logs["errors_coerced"] += (post_nulls - pre_nulls)

        # 6. Imputar valores nulos con la mediana
        for col in cls.NUMERIC_COLUMNS:
            if col in df.columns:
                null_count = df[col].isna().sum()
                if null_count > 0:
                    median_val = df[col].median()
                    # Si la mediana es NaN (toda la columna nula), usar un valor por defecto
                    if pd.isna(median_val):
                        defaults = {"altura": 1.70, "peso": 70, "edad": 40, "glucosa": 100, "presion_sistolica": 120}
                        median_val = defaults.get(col, 0)
                    df[col] = df[col].fillna(median_val)
                    logs["nulls_imputed"] += null_count

        # 7. Generar documento si no existe o es nulo
        if "documento" not in df.columns:
            df["documento"] = [f"GEN-{1000000 + i}" for i in range(len(df))]
        else:
            # Rellenar solo los nulos
            null_docs = df["documento"].isna()
            if null_docs.any():
                df.loc[null_docs, "documento"] = [f"GEN-{2000000 + i}" for i in range(null_docs.sum())]
        
        # 8. Recalcular IMC: peso / (altura^2)
        # Asegurar que altura no sea 0 para evitar error
        df["altura"] = df["altura"].replace(0, 1.70)
        df["imc"] = (df["peso"] / (df["altura" ] ** 2)).round(2)

        # 9. Normalizar Sexo
        if "sexo" in df.columns:
            df["sexo"] = df["sexo"].apply(cls._normalize_sex)

        # 10. Corregir diagnósticos (Hipertensión)
        if "diagnostico" in df.columns:
            df["diagnostico"] = df["diagnostico"].apply(cls._normalize_diagnosis)
        else:
            df["diagnostico"] = "Pendiente de evaluación"

        # 11. Clasificar riesgo automáticamente
        df["riesgo"] = df.apply(cls.classify_risk, axis=1)

        # Convertir todos los valores de logs a tipos nativos de Python (evitar numpy.int64, etc.)
        for key in logs:
            if hasattr(logs[key], "item"):
                logs[key] = logs[key].item()
            else:
                logs[key] = int(logs[key]) if isinstance(logs[key], (int, float)) else logs[key]
                
        logs["transformed"] = len(df)
        print(f"ETL LOGS: {logs}") # Opcional: usar un logger real
        return df, logs

    @staticmethod
    def _clean_column_name(name):
        """Elimina acentos, caracteres especiales y normaliza a lowercase."""
        if not isinstance(name, str):
            return str(name)
        # Quitar acentos
        nfkd_form = unicodedata.normalize('NFKD', name)
        name = "".join([c for c in nfkd_form if not unicodedata.combining(c)])
        # A minúsculas y reemplazar espacios/especiales por guion bajo
        name = name.lower().strip()
        name = re.sub(r'[^\w]', '_', name)
        name = re.sub(r'_+', '_', name).strip('_')
        return name

    @staticmethod
    def classify_risk(row):
        # Prioridad CRITICO
        if (row.get("glucosa", 0) > 300 or 
            row.get("presion_sistolica", 0) > 180):
            return "CRITICO"
        
        # ALTO
        if (row.get("glucosa", 0) > 200 or 
            row.get("presion_sistolica", 0) > 140 or
            row.get("saturacion_oxigeno", 100) < 90):
            return "ALTO"
        
        # MEDIO
        if (row.get("imc", 0) > 30 or 
            row.get("colesterol", 0) > 240 or
            row.get("frecuencia_cardiaca", 75) > 100):
            return "MEDIO"
            
        return "BAJO"

    @staticmethod
    def load(df):
        total_upserted = 0
        errors = []
        
        with transaction.atomic():
            existing_docs = set(Patient.objects.values_list("documento", flat=True))
            
            for idx, row in df.iterrows():
                try:
                    documento = str(row["documento"]) if pd.notna(row["documento"]) else None
                    
                    patient_data = {
                        "nombres": str(row["nombres"]) if pd.notna(row["nombres"]) else "",
                        "apellidos": str(row["apellidos"]) if pd.notna(row["apellidos"]) else "",
                        "edad": int(float(row["edad"])) if pd.notna(row["edad"]) else 0,
                        "sexo": str(row["sexo"]) if pd.notna(row["sexo"]) else "M",
                        "peso": float(row["peso"]) if pd.notna(row["peso"]) else 70.0,
                        "altura": float(row["altura"]) if pd.notna(row["altura"]) else 1.70,
                        "imc": float(row["imc"]) if pd.notna(row["imc"]) else 24.0,
                        "glucosa": float(row["glucosa"]) if pd.notna(row["glucosa"]) else 100.0,
                        "colesterol": float(row["colesterol"]) if pd.notna(row["colesterol"]) else 200.0,
                        "presion_sistolica": int(float(row.get("presion_sistolica", 120))) if pd.notna(row.get("presion_sistolica", 120)) else 120,
                        "presion_diastolica": int(float(row.get("presion_diastolica", 80))) if pd.notna(row.get("presion_diastolica", 80)) else 80,
                        "saturacion_oxigeno": float(row.get("saturacion_oxigeno", 95)) if pd.notna(row.get("saturacion_oxigeno", 95)) else 95.0,
                        "frecuencia_cardiaca": int(float(row.get("frecuencia_cardiaca", 75))) if pd.notna(row.get("frecuencia_cardiaca", 75)) else 75,
                        "diagnostico": str(row["diagnostico"]) if pd.notna(row["diagnostico"]) else "Pendiente de evaluación",
                        "es_hipertenso": bool(row.get("es_hipertenso", False)) if pd.notna(row.get("es_hipertenso", False)) else False,
                        "es_diabetico": bool(row.get("es_diabetico", False)) if pd.notna(row.get("es_diabetico", False)) else False,
                        "es_fumador": bool(row.get("es_fumador", False)) if pd.notna(row.get("es_fumador", False)) else False,
                        "riesgo": str(row["riesgo"]) if pd.notna(row["riesgo"]) else "BAJO",
                    }
                    
                    if documento and documento in existing_docs:
                        Patient.objects.filter(documento=documento).update(**patient_data)
                    else:
                        Patient.objects.create(documento=documento, **patient_data)
                        existing_docs.add(documento)
                        
                    total_upserted += 1
                except Exception as e:
                    errors.append(f"Fila {idx+2}: {str(e)}")
        
        if errors:
            raise ValueError(f"Errores al cargar datos: {'; '.join(errors)}")

        return total_upserted

    @staticmethod
    def reset_all_data():
        """Elimina todos los pacientes de la base de datos."""
        from .models import UploadedDataset
        Patient.objects.all().delete()
        UploadedDataset.objects.all().delete()
        return True

    @classmethod
    def _validate_columns(cls, df):
        missing_columns = [
            column
            for column in cls.REQUIRED_COLUMNS
            if column not in df.columns
        ]
        if missing_columns:
            missing_as_text = ", ".join(missing_columns)
            raise ValueError(
                f"Faltan columnas requeridas: {missing_as_text}"
            )

    @staticmethod
    def _normalize_sex(value):
        val = str(value).strip().upper()
        if val in ['M', 'MASCULINO', 'HOMBRE', 'MALE']:
            return 'M'
        if val in ['F', 'FEMENINO', 'MUJER', 'FEMALE']:
            return 'F'
        return 'M' # Default robusto

    @staticmethod
    def _normalize_diagnosis(value):
        if pd.isna(value): return "Sin diagnóstico"
        val = str(value).strip().lower()
        # Eliminar acentos para comparación
        val = "".join([c for c in unicodedata.normalize('NFKD', val) if not unicodedata.combining(c)])
        
        if 'hipertencion' in val or 'hipertension' in val:
            return "Hipertensión"
        if 'diabetes' in val:
            return "Diabetes"
        
        return str(value).strip().capitalize()



