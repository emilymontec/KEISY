import pandas as pd
import numpy as np
import unicodedata
import re
import hashlib
from pathlib import Path

from patients.models import Patient


class ETLService:
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
    def extract(file_path):
        ext = Path(file_path).suffix.lower()
        try:
            if ext == '.csv':
                return pd.read_csv(file_path)
            elif ext == '.xlsx':
                return pd.read_excel(file_path, engine='openpyxl')
            elif ext == '.json':
                # Intentar leer como lista de registros primero
                try:
                    return pd.read_json(file_path)
                except Exception:
                    return pd.read_json(file_path, orient='records')
            else:
                raise ValueError(f"Formato de archivo no soportado: {ext}")
        except Exception as e:
            raise ValueError(f"Error al leer el archivo {ext}: {str(e)}")

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
        
        # 0. Validar que existan las columnas requeridas
        cls._validate_columns(df)

        # 2. Renombrado específico solicitado
        rename_map = {
            "imc_column": "imc", # En caso de que venga como IMC (ya limpiado a imc)
            "presion_sistolica_column": "presion_sistolica",
            "riesgo_enfermedad": "riesgo",
            "diagnostico_preliminar": "diagnostico",
            "saturacion_oxigeno_column": "saturacion_oxigeno",
            "id_paciente": "documento"
        }
        # Aplicar renombrado manual para casos específicos que no sigan la limpieza simple
        df = df.rename(columns={
            "imc": "imc", 
            "presion_sistolica": "presion_sistolica",
            "riesgo_enfermedad": "riesgo",
            "diagnostico_preliminar": "diagnostico"
        })

        # 3. Eliminar duplicados
        initial_len = len(df)
        df = df.drop_duplicates().reset_index(drop=True)
        logs["duplicates_removed"] = initial_len - len(df)

        # 4. Convertir tipos numéricos (coerce)
        for col in cls.NUMERIC_COLUMNS:
            if col in df.columns:
                # Contar cuántos fallarán la conversión para el log
                pre_nulls = df[col].isna().sum()
                df[col] = pd.to_numeric(df[col], errors='coerce')
                post_nulls = df[col].isna().sum()
                logs["errors_coerced"] += (post_nulls - pre_nulls)

        # 5. Imputar valores nulos con la mediana
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

        # 6. Generar documento si no existe o es nulo
        if "documento" not in df.columns:
            df["documento"] = [f"GEN-{1000000 + i}" for i in range(len(df))]
        else:
            # Rellenar solo los nulos
            null_docs = df["documento"].isna()
            if null_docs.any():
                df.loc[null_docs, "documento"] = [f"GEN-{2000000 + i}" for i in range(null_docs.sum())]
        
        # 7. Recalcular IMC: peso / (altura^2)
        # Asegurar que altura no sea 0 para evitar error
        df["altura"] = df["altura"].replace(0, 1.70)
        df["imc"] = (df["peso"] / (df["altura" ] ** 2)).round(2)

        # 8. Normalizar Sexo
        if "sexo" in df.columns:
            df["sexo"] = df["sexo"].apply(cls._normalize_sex)

        # 9. Corregir diagnósticos (Hipertensión)
        if "diagnostico" in df.columns:
            df["diagnostico"] = df["diagnostico"].apply(cls._normalize_diagnosis)
        else:
            df["diagnostico"] = "Pendiente de evaluación"

        # 10. Clasificar riesgo automáticamente
        df["riesgo"] = df.apply(cls.classify_risk, axis=1)

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
        name = re.sub(r'[^\w\s]', '', name)
        name = re.sub(r'\s+', '_', name)
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
        for idx, row in df.iterrows():
            try:
                documento = str(row["documento"]) if pd.notna(row["documento"]) else None
                
                # Usar update_or_create para manejar modificaciones de datos si el documento ya existe
                obj, created = Patient.objects.update_or_create(
                    documento=documento,
                    defaults={
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
                )
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

    @staticmethod
    def generate_simulated_dataset(n_rows=50):
        import random
        data = []
        nombres = ["Juan", "Maria", "Pedro", "Ana", "Luis", "Carmen", "Jose", "Elena", "Carlos", "Lucia"]
        apellidos = ["Garcia", "Rodriguez", "Lopez", "Martinez", "Perez", "Gonzalez", "Sanchez", "Romero", "Torres", "Ruiz"]
        diagnosticos = ["Diabetes Melitus", "Hipertension", "HTA", "Obesisad", "Asma", "Sano", "Gastritis", "Anemia"]
        
        for i in range(n_rows):
            peso = random.uniform(50, 110)
            altura = random.uniform(1.50, 1.95)
            diag = random.choice(diagnosticos)
            
            # Simular signos vitales
            presion_sis = random.randint(90, 200)
            glucosa = random.randint(70, 350)
            saturacion = random.randint(80, 100)
            frecuencia = random.randint(50, 120)
            
            data.append({
                "nombres": random.choice(nombres),
                "apellidos": random.choice(apellidos),
                "documento": f"10{random.randint(1000000, 9999999)}",
                "edad": random.randint(18, 85),
                "sexo": random.choice(["M", "F", "Masculino", "Femenino", "m", "f"]),
                "peso": round(peso, 1),
                "altura": round(altura, 2),
                "glucosa": glucosa,
                "colesterol": random.randint(150, 300),
                "presion_sistolica": presion_sis,
                "presion_diastolica": random.randint(60, 110),
                "saturacion_oxigeno": saturacion,
                "frecuencia_cardiaca": frecuencia,
                "diagnostico": diag,
                "es_hipertenso": "Hiper" in diag or presion_sis > 140 or random.random() < 0.1,
                "es_diabetico": "Diabet" in diag or glucosa > 126 or random.random() < 0.1,
                "es_fumador": random.random() < 0.25,
            })
        
        # Agregar algunos duplicados y nulos para probar transform
        df = pd.DataFrame(data)
        return df

