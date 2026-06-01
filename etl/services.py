import pandas as pd

from patients.models import Patient


class ETLService:
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

        cleaned_df = df.copy().drop_duplicates().reset_index(drop=True)

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
            raise ValueError(
                "La columna 'altura' necesita al menos un valor valido."
            )

        cleaned_df["edad"] = cleaned_df["edad"].round().astype(int)
        cleaned_df["sexo"] = cleaned_df["sexo"].apply(
            cls._normalize_sex
        )
        cleaned_df["imc"] = (
            cleaned_df["peso"] / (cleaned_df["altura"] ** 2)
        ).round(2)

        return cleaned_df

    @staticmethod
    def classify_risk(row):
        if row["glucosa"] > 300:
            return "CRITICO"

        if row["imc"] > 30:
            return "ALTO"

        if row["glucosa"] > 140:
            return "MEDIO"

        return "BAJO"

    @staticmethod
    def load(df):
        patients = [
            Patient(
                nombres=row["nombres"],
                apellidos=row["apellidos"],
                edad=int(row["edad"]),
                sexo=row["sexo"],
                peso=float(row["peso"]),
                altura=float(row["altura"]),
                imc=float(row["imc"]),
                glucosa=float(row["glucosa"]),
                colesterol=float(row["colesterol"]),
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
            raise ValueError(
                "La columna 'sexo' solo admite M/F o sus equivalentes."
            )

        return sex_map[normalized]
