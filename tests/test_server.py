"""Tests server module."""

import io
import os
import unittest
from unittest.mock import MagicMock, call, patch

from bs4 import BeautifulSoup
from fastapi.testclient import TestClient
from requests import Response

from aind_data_transfer_service.server import app

test_directory = os.path.dirname(os.path.abspath(__file__))
templates_directory = os.path.join(
    test_directory, "src/aind_data_transfer_service/templates"
)


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

    with open(test_directory + "/resources/sample.csv", "r") as file:
        csv_content = file.read()

    @patch.dict(os.environ, EXAMPLE_ENV_VAR1, clear=True)
    def test_index(self):
        """Tests that form renders at startup as expected."""
        with TestClient(app) as client:
            response = client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Upload Job", response.text)

    @patch.dict(os.environ, EXAMPLE_ENV_VAR1, clear=True)
    def test_post_upload_csv(self):
        """Tests that valid csv is posted as expected."""
        with TestClient(app) as client:
            get_response = client.get("/")
            soup = BeautifulSoup(get_response.text, "html.parser")
            csrf_token = soup.find("input", attrs={"name": "csrf_token"})[
                "value"
            ]
            headers = {"X-CSRF-Token": csrf_token}
            response = client.post(
                "/",
                files={
                    "upload_csv": (
                        "resources/sample.csv",
                        io.BytesIO(self.csv_content.encode("utf-8")),
                        "text/csv",
                    )
                },
                headers=headers,
            )
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/html", response.headers["content-type"])

    @patch.dict(os.environ, EXAMPLE_ENV_VAR1, clear=True)
    def test_post_submit_jobs_failure(self):
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
            response = client.post(
                "/",
                files={
                    "upload_csv": (
                        "resources/sample.csv",
                        io.BytesIO(self.csv_content.encode("utf-8")),
                        "text/csv",
                    )
                },
                data={"submit_jobs": "Submit"},
                headers=headers,
            )
        self.assertEqual(response.status_code, 200)
        self.assertIn("Successfully submitted job.", response.text)
        mock_sleep.assert_has_calls([call(1), call(1), call(1)])


if __name__ == "__main__":
    unittest.main()
