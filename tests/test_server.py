"""Tests server module."""

import json
import os
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient
from requests import Response

from aind_data_transfer_service.server import app
from tests.test_configs import TestJobConfigs

TEST_DIRECTORY = Path(os.path.dirname(os.path.realpath(__file__)))
SAMPLE_FILE = TEST_DIRECTORY / "resources" / "sample.csv"
MALFORMED_SAMPLE_FILE = TEST_DIRECTORY / "resources" / "sample_malformed.csv"
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

    with open(SAMPLE_FILE, "r") as file:
        csv_content = file.read()

    with open(MOCK_DB_FILE) as f:
        json_contents = json.load(f)

    expected_job_configs = deepcopy(TestJobConfigs.expected_job_configs)
    for config in expected_job_configs:
        config.aws_param_store_name = None

    @patch.dict(os.environ, EXAMPLE_ENV_VAR1, clear=True)
    def test_validate_csv(self):
        """Tests that valid csv file is returned."""
        with TestClient(app) as client:
            with open(SAMPLE_FILE, "rb") as f:
                files = {
                    "file": f,
                }
                response = client.post(url="/api/validate_csv", files=files)
        expected_jobs = [j.json() for j in self.expected_job_configs]
        expected_response = {
            "message": "Valid Data",
            "data": {"jobs": expected_jobs, "errors": []},
        }
        self.assertEqual(response.status_code, 200)
        self.assertEqual(expected_response, response.json())

    @patch.dict(os.environ, EXAMPLE_ENV_VAR1, clear=True)
    @patch("aind_data_transfer_service.server.sleep", return_value=None)
    @patch("aind_data_transfer_service.hpc.client.HpcClient.submit_job")
    def test_submit_jobs(
        self, mock_submit_job: MagicMock, mock_sleep: MagicMock
    ):
        """Tests submit jobs success."""
        mock_response = Response()
        mock_response.status_code = 200
        mock_response._content = b'{"message": "success"}'
        mock_submit_job.return_value = mock_response
        with TestClient(app) as client:
            with open(SAMPLE_FILE, "rb") as f:
                files = {
                    "file": f,
                }
                response = client.post(url="/api/validate_csv", files=files)
                basic_jobs = response.json()["data"]
                submit_job_response = client.post(
                    url="/api/submit_basic_jobs", json=basic_jobs
                )
        expected_response = {
            "message": "Submitted Jobs.",
            "data": {
                "responses": [
                    {"message": "success"},
                    {"message": "success"},
                    {"message": "success"},
                ],
                "errors": [],
            },
        }
        self.assertEqual(expected_response, submit_job_response.json())
        self.assertEqual(200, submit_job_response.status_code)
        self.assertEqual(3, mock_sleep.call_count)

    @patch.dict(os.environ, EXAMPLE_ENV_VAR1, clear=True)
    @patch("aind_data_transfer_service.server.sleep", return_value=None)
    @patch("aind_data_transfer_service.hpc.client.HpcClient.submit_job")
    @patch("logging.error")
    def test_submit_jobs_server_error(
        self,
        mock_log_error: MagicMock,
        mock_submit_job: MagicMock,
        mock_sleep: MagicMock,
    ):
        """Tests that submit jobs returns error if there's an issue with hpc"""
        mock_response = Response()
        mock_response.status_code = 500
        mock_submit_job.return_value = mock_response
        with TestClient(app) as client:
            with open(SAMPLE_FILE, "rb") as f:
                files = {
                    "file": f,
                }
                response = client.post(url="/api/validate_csv", files=files)
                basic_jobs = response.json()["data"]
                submit_job_response = client.post(
                    url="/api/submit_basic_jobs", json=basic_jobs
                )
        expected_response = {
            "message": "There were errors submitting jobs to the hpc.",
            "data": {
                "responses": [],
                "errors": [
                    "Error processing ecephys_123454_2020-10-10_14-10-10",
                    "Error processing Other_123456_2020-10-13_13-10-10",
                    "Error processing Other_123456_2020-10-13_13-10-10",
                ],
            },
        }
        self.assertEqual(expected_response, submit_job_response.json())
        self.assertEqual(500, submit_job_response.status_code)
        self.assertEqual(0, mock_sleep.call_count)
        self.assertEqual(3, mock_log_error.call_count)

    @patch.dict(os.environ, EXAMPLE_ENV_VAR1, clear=True)
    @patch("aind_data_transfer_service.server.sleep", return_value=None)
    @patch("aind_data_transfer_service.hpc.client.HpcClient.submit_job")
    @patch("logging.error")
    def test_submit_jobs_malformed_json(
        self,
        mock_log_error: MagicMock,
        mock_submit_job: MagicMock,
        mock_sleep: MagicMock,
    ):
        """Tests that submit jobs returns parsing errors."""
        mock_response = Response()
        mock_response.status_code = 500
        mock_submit_job.return_value = mock_response
        with TestClient(app) as client:
            basic_jobs = {"jobs": ['{"malformed_key": "val"}']}
            submit_job_response = client.post(
                url="/api/submit_basic_jobs", json=basic_jobs
            )
        expected_response = {
            "message": "There were errors parsing the basic job configs",
            "data": {
                "responses": [],
                "errors": [
                    (
                        'Error parsing {"malformed_key": "val"}: '
                        "<class 'pydantic.error_wrappers.ValidationError'>"
                    )
                ],
            },
        }
        self.assertEqual(406, submit_job_response.status_code)
        self.assertEqual(expected_response, submit_job_response.json())
        self.assertEqual(0, mock_sleep.call_count)
        self.assertEqual(0, mock_log_error.call_count)

    @patch.dict(os.environ, EXAMPLE_ENV_VAR1, clear=True)
    def test_validate_malformed_csv(self):
        """Tests that invalid csv returns errors"""
        with TestClient(app) as client:
            with open(MALFORMED_SAMPLE_FILE, "rb") as f:
                files = {
                    "file": f,
                }
                response = client.post(url="/api/validate_csv", files=files)
        self.assertEqual(response.status_code, 406)
        self.assertEqual(
            ["AttributeError('WRONG_MODALITY_HERE')"],
            response.json()["data"]["errors"],
        )

    @patch.dict(os.environ, EXAMPLE_ENV_VAR1, clear=True)
    def test_index(self):
        """Tests that form renders at startup as expected."""
        with TestClient(app) as client:
            response = client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Submit Jobs", response.text)

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
