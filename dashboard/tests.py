from django.test import TestCase
from django.urls import reverse

from etl.models import UploadedDataset
from patients.models import Patient


class DashboardViewTests(TestCase):
    def test_home_shows_real_counts(self):
        Patient.objects.create(
            nombres="Ana",
            apellidos="Perez",
            edad=31,
            sexo="F",
            peso=60,
            altura=1.65,
            imc=22.04,
            glucosa=118,
            colesterol=180,
            riesgo="BAJO",
        )
        UploadedDataset.objects.create(
            file_name="mayo.csv",
            stored_path="datasets/mayo.csv",
            rows_received=20,
            rows_processed=18,
            rows_inserted=18,
            status="SUCCESS",
        )

        response = self.client.get(reverse("home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Pacientes guardados")
        self.assertEqual(response.context["total_patients"], 1)
        self.assertEqual(response.context["total_uploads"], 1)

    def test_admin_login_uses_custom_branding(self):
        response = self.client.get("/admin/login/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Ingreso administrativo")
        self.assertContains(response, "Keisy Medical Control")
