import pandas as pd
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from patients.models import Patient
from .models import UploadedDataset
from .services import ETLService


class ETLServiceTests(SimpleTestCase):
    def test_transform_cleans_duplicates_and_calculates_imc(self):
        df = pd.DataFrame(
            [
                {
                    "nombres": "Ana",
                    "apellidos": "Perez",
                    "edad": "30",
                    "sexo": "F",
                    "peso": "60",
                    "altura": "1.65",
                    "glucosa": "120",
                    "colesterol": "190",
                },
                {
                    "nombres": "Ana",
                    "apellidos": "Perez",
                    "edad": "30",
                    "sexo": "F",
                    "peso": "60",
                    "altura": "1.65",
                    "glucosa": "120",
                    "colesterol": "190",
                },
                {
                    "nombres": "Luis",
                    "apellidos": "Gomez",
                    "edad": None,
                    "sexo": "masculino",
                    "peso": "80",
                    "altura": "1.80",
                    "glucosa": None,
                    "colesterol": "210",
                },
            ]
        )

        transformed = ETLService.transform(df)

        self.assertEqual(len(transformed), 2)
        self.assertEqual(transformed.loc[1, "edad"], 30)
        self.assertEqual(transformed.loc[1, "glucosa"], 120)
        self.assertEqual(transformed.loc[1, "sexo"], "M")
        self.assertAlmostEqual(transformed.loc[0, "imc"], 22.04, places=2)

    def test_transform_requires_expected_columns(self):
        df = pd.DataFrame([{"nombres": "Ana"}])

        with self.assertRaisesMessage(
            ValueError,
            "Faltan columnas requeridas en el CSV",
        ):
            ETLService.transform(df)


class UploadCsvViewTests(TestCase):
    def test_upload_creates_patients_and_upload_record(self):
        csv_content = "\n".join(
            [
                "nombres,apellidos,edad,sexo,peso,altura,glucosa,colesterol",
                "Ana,Perez,30,F,60,1.65,120,180",
                "Ana,Perez,30,F,60,1.65,120,180",
                "Luis,Gomez,,masculino,82,1.82,,210",
            ]
        ).encode("utf-8")
        uploaded_file = SimpleUploadedFile(
            "pacientes.csv",
            csv_content,
            content_type="text/csv",
        )

        response = self.client.post(
            reverse("upload_csv"),
            {"file": uploaded_file},
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Patient.objects.count(), 2)
        self.assertEqual(UploadedDataset.objects.count(), 1)

        upload_record = UploadedDataset.objects.get()
        self.assertEqual(upload_record.status, "SUCCESS")
        self.assertEqual(upload_record.rows_received, 3)
        self.assertEqual(upload_record.rows_processed, 2)
        self.assertEqual(upload_record.rows_inserted, 2)
