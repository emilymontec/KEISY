import pandas as pd

from patients.models import Patient


class ETLService:
    REQUIRED_COLUMNS = [
        "nombres",
        "apellidos",
        "documento",
        "edad",
        "sexo",
        "peso",
        "altura",
        "glucosa",
        "colesterol",
        "diagnostico",
    ]
    NUMERIC_COLUMNS = [
        "edad",
        "peso",
        "altura",
        "glucosa",
        "colesterol",
    ]

    @staticmethod
    def extract(file_path):
        return pd.read_csv(file_path)

    @classmethod
    def transform(cls, df):
        cls._validate_columns(df)

        # 1. Eliminar duplicados
        cleaned_df = df.copy().drop_duplicates().reset_index(drop=True)

        # 2. Convertir tipos de datos y Corregir valores nulos
        for column in cls.NUMERIC_COLUMNS:
            cleaned_df[column] = pd.to_numeric(
                cleaned_df[column],
                errors="coerce",
            )

        numeric_medians = cleaned_df[cls.NUMERIC_COLUMNS].median(
            numeric_only=True
        )
        cleaned_df[cls.NUMERIC_COLUMNS] = cleaned_df[
            cls.NUMERIC_COLUMNS
        ].fillna(numeric_medians).fillna(0)

        # Evita divisiones por cero al calcular el IMC.
        cleaned_df["altura"] = cleaned_df["altura"].replace(0, pd.NA)
        cleaned_df["altura"] = cleaned_df["altura"].fillna(
            cleaned_df["altura"].median()
        )
        if cleaned_df["altura"].isna().any():
            cleaned_df["altura"] = cleaned_df["altura"].fillna(1.70) # Valor por defecto seguro

        cleaned_df["edad"] = cleaned_df["edad"].round().astype(int)
        
        # 3. Estandarizar sexo
        cleaned_df["sexo"] = cleaned_df["sexo"].apply(
            cls._normalize_sex
        )

        # 4. Corregir diagnósticos comunes
        cleaned_df["diagnostico"] = cleaned_df["diagnostico"].apply(
            cls._normalize_diagnosis
        )

        # Calcular IMC
        cleaned_df["imc"] = (
            cleaned_df["peso"] / (cleaned_df["altura"] ** 2)
        ).round(2)

        return cleaned_df

    @staticmethod
    def classify_risk(row):
        # Reglas Críticas
        if (row.get("presion_sistolica", 0) > 180 or 
            row.get("glucosa", 0) > 300 or 
            row.get("saturacion_oxigeno", 100) < 85):
            return "CRITICO"

        # Reglas Altas
        if (row.get("presion_sistolica", 0) > 140 or 
            row.get("glucosa", 0) > 126): # Umbral médico común para glucosa alta
            return "ALTO"

        # Reglas Medias
        if (row.get("imc", 0) > 25 or # Sobrepeso
            row.get("es_hipertenso", False) or 
            row.get("es_diabetico", False) or 
            row.get("es_fumador", False)):
            return "MEDIO"

        # Regla Bajo
        return "BAJO"

    @staticmethod
    def load(df):
        patients = [
            Patient(
                nombres=row["nombres"],
                apellidos=row["apellidos"],
                documento=str(row["documento"]) if pd.notna(row["documento"]) else None,
                edad=int(row["edad"]),
                sexo=row["sexo"],
                peso=float(row["peso"]),
                altura=float(row["altura"]),
                imc=float(row["imc"]),
                glucosa=float(row["glucosa"]),
                colesterol=float(row["colesterol"]),
                presion_sistolica=int(row.get("presion_sistolica", 120)),
                presion_diastolica=int(row.get("presion_diastolica", 80)),
                saturacion_oxigeno=float(row.get("saturacion_oxigeno", 95)),
                frecuencia_cardiaca=int(row.get("frecuencia_cardiaca", 75)),
                diagnostico=row["diagnostico"],
                es_hipertenso=row.get("es_hipertenso", False),
                es_diabetico=row.get("es_diabetico", False),
                es_fumador=row.get("es_fumador", False),
                riesgo=row["riesgo"],
            )
            for _, row in df.iterrows()
        ]

        created = Patient.objects.bulk_create(patients)
        return len(created)

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
                f"Faltan columnas requeridas en el CSV: {missing_as_text}"
            )

    @staticmethod
    def _normalize_sex(value):
        normalized = str(value).strip().upper()
        sex_map = {
            "M": "M",
            "MASCULINO": "M",
            "MALE": "M",
            "F": "F",
            "FEMENINO": "F",
            "FEMALE": "F",
        }

        if normalized not in sex_map:
            return "M" # Default or handle error

        return sex_map[normalized]

    @staticmethod
    def _normalize_diagnosis(value):
        if pd.isna(value) or str(value).strip() == "":
            return "Pendiente de evaluación"
        
        diag = str(value).strip().lower()
        # Corregir diagnósticos comunes
        corrections = {
            "diabetes melitus": "Diabetes Mellitus",
            "hipertension": "Hipertensión Arterial",
            "hta": "Hipertensión Arterial",
            "obesisad": "Obesidad",
            "asms": "Asma",
            "gastritis ": "Gastritis",
        }
        
        for key, correct in corrections.items():
            if key in diag:
                return correct
        
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

