"""Tests server module."""

import io
import json
import os
import unittest
from pathlib import Path
from unittest.mock import MagicMock, call, patch

from bs4 import BeautifulSoup
from fastapi.testclient import TestClient
from requests import Response

from aind_data_transfer_service.server import app

TEST_DIRECTORY = Path(os.path.dirname(os.path.realpath(__file__)))
RESOURCES_DIR = TEST_DIRECTORY / "resources"
MOCK_DB_FILE = TEST_DIRECTORY / "test_server" / "db.json"


class TestServer(unittest.TestCase):
    """Tests main server."""

    EXAMPLE_ENV_VAR1 = {
        "HPC_HOST": "hpc_host",
        "HPC_USERNAME": "hpc_user",
        "HPC_PASSWORD": "hpc_password",
        "HPC_TOKEN": "hpc_jwt",
        "HPC_PARTITION": "hpc_part",
        "HPC_SIF_LOCATION": "hpc_sif_location",
        "HPC_CURRENT_WORKING_DIRECTORY": "hpc_cwd",
        "HPC_LOGGING_DIRECTORY": "hpc_logs",
        "HPC_AWS_ACCESS_KEY_ID": "aws_key",
        "HPC_AWS_SECRET_ACCESS_KEY": "aws_secret_key",
        "HPC_AWS_DEFAULT_REGION": "aws_region",
        "APP_CSRF_SECRET_KEY": "test_csrf_key",
        "APP_SECRET_KEY": "test_app_key",
        "HPC_STAGING_DIRECTORY": "/stage/dir",
        "HPC_AWS_PARAM_STORE_NAME": "/some/param/store",
    }

    with open(TEST_DIRECTORY / "resources" / "sample.csv", "r") as file:
        csv_content = file.read()

    with open(RESOURCES_DIR / "sample_malformed.csv", "r") as file:
        malformed_csv_content = file.read()

    with open(MOCK_DB_FILE) as f:
        json_contents = json.load(f)

    @patch.dict(os.environ, EXAMPLE_ENV_VAR1, clear=True)
    def test_index(self):
        """Tests that form renders at startup as expected."""
        with TestClient(app) as client:
            response = client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Submit Jobs", response.text)

    @patch.dict(os.environ, EXAMPLE_ENV_VAR1, clear=True)
    @patch("requests.post")
    def test_post_submit_jobs_failure(self, mock_post: MagicMock):
        """Tests that form fails to submit when there's no data as expected."""
        with TestClient(app) as client:
            get_response = client.get("/")
            soup = BeautifulSoup(get_response.text, "html.parser")
            csrf_token = soup.find("input", attrs={"name": "csrf_token"})[
                "value"
            ]
            headers = {"X-CSRF-Token": csrf_token}
            response = client.post(
                "/", data={"submit_jobs": "Submit"}, headers=headers
            )
        mock_post.assert_not_called()
        self.assertEqual(response.status_code, 400)
        self.assertIn("Error collecting csv data.", response.text)

    @patch.dict(os.environ, EXAMPLE_ENV_VAR1, clear=True)
    @patch("requests.post")
    @patch("aind_data_transfer_service.server.sleep", return_value=None)
    def test_post_submit_jobs_success(
        self, mock_sleep: MagicMock, mock_post: MagicMock
    ):
        """Tests that form successfully submits as expected."""
        mock_response = Response()
        mock_response.status_code = 200
        mock_response._content = b'{"message": "success"}'
        mock_post.return_value = mock_response

        with TestClient(app) as client:
            get_response = client.get("/")
            soup = BeautifulSoup(get_response.text, "html.parser")
            csrf_token = soup.find("input", attrs={"name": "csrf_token"})[
                "value"
            ]
            headers = {"X-CSRF-Token": csrf_token}
            response0 = client.post(
                "/",
                files={
                    "upload_csv": (
                        "resources/sample.csv",
                        io.BytesIO(self.csv_content.encode("utf-8")),
                        "text/csv",
                    )
                },
                data={"preview_jobs": "Submit"},
                headers=headers,
            )
            response1 = client.post(
                "/",
                data={"preview_jobs": "Submit", "submit_jobs": "Submit"},
                headers=headers,
            )
        self.assertEqual(response0.status_code, 200)
        self.assertEqual(response1.status_code, 200)
        self.assertIn("Successfully submitted job.", response1.text)
        mock_sleep.assert_has_calls([call(1), call(1), call(1)])

    @patch.dict(os.environ, EXAMPLE_ENV_VAR1, clear=True)
    @patch("requests.get")
    def test_jobs_success(self, mock_get: MagicMock):
        """Tests that job status page renders at startup as expected."""
        mock_response = Response()
        mock_response.status_code = 200
        mock_response._content = json.dumps(self.json_contents["jobs"]).encode(
            "utf-8"
        )
        mock_get.return_value = mock_response
        with TestClient(app) as client:
            response = client.get("/jobs")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Submit Jobs", response.text)

    @patch.dict(os.environ, EXAMPLE_ENV_VAR1, clear=True)
    @patch("requests.get")
    def test_jobs_failure(self, mock_get: MagicMock):
        """Tests that job status page renders at startup as expected."""
        mock_response = Response()
        mock_response.status_code = 500
        mock_response._content = json.dumps({"message": "error"}).encode(
            "utf-8"
        )
        mock_get.return_value = mock_response
        with TestClient(app) as client:
            response = client.get("/jobs")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Submit Jobs", response.text)


if __name__ == "__main__":
    unittest.main()
