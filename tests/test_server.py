"""Tests server module."""

import asyncio
import os
import unittest
import io

from bs4 import BeautifulSoup
from fastapi.testclient import TestClient
from starlette.config import environ

from aind_data_transfer_service.server import app

# Set the secret keys for testing
environ["SECRET_KEY"] = os.urandom(32).hex()
environ["CSRF_SECRET_KEY"] = os.urandom(32).hex()

test_directory = os.path.dirname(os.path.abspath(__file__))
templates_directory = os.path.join(
    test_directory, "src/aind_data_transfer_service/templates"
)


class TestServer(unittest.TestCase):
    """Tests main server."""

    client = TestClient(app)
    with open(test_directory+"/resources/sample.csv", "r") as file:
        csv_content = file.read()

    def test_index(self):
        """Tests that form renders at startup as expected."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Upload Job", response.text)

        response = self.client.post("/", files={"file": ("resources/sample.csv", io.BytesIO(self.csv_content.encode("utf-8")), "text/csv")})
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/html", response.headers["content-type"])
        self.assertIn("modality", response.text)
        self.assertIn("some_bucket", response.text)
        self.assertIn("/aind/data/transfer/endpoints", response.text)

        invalid_csv = "invalid,csv\n123,456"  # Invalid CSV content
        response = self.client.post("/", files={"file": ("test.csv", io.BytesIO(invalid_csv.encode("utf-8")), "text/csv")})
        self.assertEqual(response.status_code, 400)
        assert "application/json" in response.headers["content-type"]
        assert "Error processing CSV" in response.json()["error"]


if __name__ == "__main__":
    unittest.main()
