"""Tests server module."""

import io
import os
import unittest

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
    with open(test_directory + "/resources/sample.csv", "r") as file:
        csv_content = file.read()

    def test_index(self):
        """Tests that form renders at startup as expected."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Upload Job", response.text)

    def test_post_upload_csv(self):
        """Tests that valid csv is posted as expected."""
        response = self.client.post(
            "/",
            files={
                "upload_csv": (
                    "resources/sample.csv",
                    io.BytesIO(self.csv_content.encode("utf-8")),
                    "text/csv",
                )
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/html", response.headers["content-type"])
        self.assertIn("modality", response.text)
        self.assertIn("some_bucket", response.text)
        self.assertIn("/aind/data/transfer/endpoints", response.text)

    def test_post_submit_jobs_failure(self):
        """Tests that form fails to submit when there's no data as expected."""
        response = self.client.post("/", data={"submit_jobs": "Submit"})
        self.assertEqual(response.status_code, 400)
        self.assertIn("Error collecting csv data.", response.text)

    def test_post_submit_jobs_success(self):
        """Tests that form successfully submits as expected."""
        response = self.client.post(
            "/",
            files={
                "upload_csv": (
                    "resources/sample.csv",
                    io.BytesIO(self.csv_content.encode("utf-8")),
                    "text/csv",
                )
            },
            data={"submit_jobs": "Submit"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("Successfully submitted job.", response.text)
        self.assertIn("modality", response.text)


if __name__ == "__main__":
    unittest.main()
