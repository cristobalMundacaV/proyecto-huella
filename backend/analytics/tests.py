from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import status
from rest_framework.test import APITestCase


class AnalyticsApiIntegrationTest(APITestCase):
	def test_dashboard_endpoint_returns_summary(self):
		response = self.client.get("/api/dashboard/")

		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertIn("total_emisiones", response.data)
		self.assertIn("datos", response.data)
		self.assertIn("emisiones_por_empresa", response.data)

	def test_upload_endpoint_requires_file(self):
		response = self.client.post("/api/upload/", data={}, format="multipart")

		self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
		self.assertIn("error", response.data)

	def test_upload_endpoint_accepts_valid_csv(self):
		csv_content = (
			"empresa,actividad,cantidad\n"
			"Empresa A,diesel,100\n"
			"Empresa B,electricidad,200\n"
		).encode("utf-8")
		uploaded_file = SimpleUploadedFile(
			"dataset.csv",
			csv_content,
			content_type="text/csv",
		)

		response = self.client.post(
			"/api/upload/",
			data={"file": uploaded_file},
			format="multipart",
		)

		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertIn("total_emisiones", response.data)
		self.assertEqual(len(response.data.get("datos", [])), 2)

	def test_risk_score_endpoint_returns_profile(self):
		payload = {
			"summary": {
				"total_emisiones": 350,
				"emisiones_por_actividad": {
					"diesel": 268,
					"electricidad": 82,
				},
				"emisiones_por_empresa": {
					"Empresa A": 268,
					"Empresa B": 82,
				},
				"datos": [
					{"actividad": "diesel", "emisiones": 268},
					{"actividad": "electricidad", "emisiones": 82},
				],
			}
		}

		response = self.client.post("/api/risk-score/", data=payload, format="json")

		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertIn("score", response.data)
		self.assertIn("label", response.data)
