import json
import tempfile
import pandas as pd
from django.test import SimpleTestCase
from .services import ETLService


class ETLServiceTests(SimpleTestCase):
    def test_transform_accepts_common_column_aliases(self):
        df = pd.DataFrame(
            [
                {
                    "Nombre": "Ana",
                    "Apellido": "Lopez",
                    "Edad": "35",
                    "Genero": "Femenino",
                    "Peso (kg)": "64.5",
                    "Altura (m)": "1.65",
                    "Glucose": "118",
                    "Cholesterol": "210",
                    "SPO2": "97",
                    "ID Paciente": "ABC-001",
                }
            ]
        )

        transformed_df, logs = ETLService.transform(df)

        self.assertEqual(logs["transformed"], 1)
        self.assertEqual(transformed_df.loc[0, "nombres"], "Ana")
        self.assertEqual(transformed_df.loc[0, "apellidos"], "Lopez")
        self.assertEqual(transformed_df.loc[0, "documento"], "ABC-001")
        self.assertEqual(transformed_df.loc[0, "sexo"], "F")
        self.assertIn("riesgo", transformed_df.columns)

    def test_read_json_accepts_nested_record_payloads(self):
        payload = {
            "records": [
                {
                    "nombres": "Luis",
                    "apellidos": "Perez",
                    "edad": 42,
                    "sexo": "M",
                    "peso": 78,
                    "altura": 1.74,
                    "glucosa": 110,
                    "colesterol": 190,
                }
            ]
        }

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", encoding="utf-8", delete=False
        ) as temp_file:
            json.dump(payload, temp_file)
            temp_path = temp_file.name

        df = ETLService._read_json(temp_path)

        self.assertEqual(len(df), 1)
        self.assertEqual(df.loc[0, "nombres"], "Luis")
