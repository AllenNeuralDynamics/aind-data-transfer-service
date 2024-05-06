"""Tests server module."""

import json
import os
import unittest
from copy import deepcopy
from io import BytesIO
from pathlib import Path, PurePosixPath
from unittest.mock import MagicMock, patch

from fastapi.responses import StreamingResponse
from fastapi.testclient import TestClient
from pydantic import SecretStr
from requests import Response

from aind_data_transfer_service.configs.job_upload_template import (
    JobUploadTemplate,
)
from aind_data_transfer_service.server import app
from tests.test_configs import TestJobConfigs

TEST_DIRECTORY = Path(os.path.dirname(os.path.realpath(__file__)))
SAMPLE_INVALID_EXT = TEST_DIRECTORY / "resources" / "sample_invalid_ext.txt"
SAMPLE_CSV = TEST_DIRECTORY / "resources" / "sample.csv"
SAMPLE_CSV_EMPTY_ROWS = TEST_DIRECTORY / "resources" / "sample_empty_rows.csv"
MALFORMED_SAMPLE_CSV = TEST_DIRECTORY / "resources" / "sample_malformed.csv"
SAMPLE_XLSX = TEST_DIRECTORY / "resources" / "sample.xlsx"
SAMPLE_XLSX_EMPTY_ROWS = (
    TEST_DIRECTORY / "resources" / "sample_empty_rows.xlsx"
)
MALFORMED_SAMPLE_XLSX = TEST_DIRECTORY / "resources" / "sample_malformed.xlsx"
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
        "OPEN_DATA_AWS_SECRET_ACCESS_KEY": "open_data_aws_key",
        "OPEN_DATA_AWS_ACCESS_KEY_ID": "open_data_aws_key_id",
    }

    with open(SAMPLE_CSV, "r") as file:
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
            with open(SAMPLE_CSV, "rb") as f:
                files = {
                    "file": f,
                }
                response = client.post(url="/api/validate_csv", files=files)
        expected_jobs = [
            j.model_dump_json() for j in self.expected_job_configs
        ]
        expected_response = {
            "message": "Valid Data",
            "data": {"jobs": expected_jobs, "errors": []},
        }
        self.assertEqual(response.status_code, 200)
        self.assertEqual(expected_response, response.json())

    @patch.dict(os.environ, EXAMPLE_ENV_VAR1, clear=True)
    def test_validate_csv_xlsx(self):
        """Tests that valid xlsx file is returned."""
        with TestClient(app) as client:
            with open(SAMPLE_XLSX, "rb") as f:
                files = {
                    "file": f,
                }
                response = client.post(url="/api/validate_csv", files=files)
        expected_jobs = [
            j.model_dump_json() for j in self.expected_job_configs
        ]
        expected_response = {
            "message": "Valid Data",
            "data": {"jobs": expected_jobs, "errors": []},
        }
        self.assertEqual(response.status_code, 200)
        self.assertEqual(expected_response, response.json())

    @patch.dict(os.environ, EXAMPLE_ENV_VAR1, clear=True)
    def test_validate_csv_xlsx_empty_rows(self):
        """Tests that empty rows are ignored from valid csv and xlsx files."""
        for file_path in [SAMPLE_CSV_EMPTY_ROWS, SAMPLE_XLSX_EMPTY_ROWS]:
            with TestClient(app) as client:
                with open(file_path, "rb") as f:
                    files = {
                        "file": f,
                    }
                    response = client.post(
                        url="/api/validate_csv", files=files
                    )
            expected_jobs = [
                j.model_dump_json() for j in self.expected_job_configs
            ]
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
            with open(SAMPLE_CSV, "rb") as f:
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
            with open(SAMPLE_CSV, "rb") as f:
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
                    "Error processing behavior_123456_2020-10-13_13-10-10",
                    "Error processing behavior_123456_2020-10-13_13-10-10",
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
                        'Error parsing {"malformed_key": "val"}:'
                        " ValidationError"
                    )
                ],
            },
        }
        self.assertEqual(406, submit_job_response.status_code)
        self.assertEqual(expected_response, submit_job_response.json())
        self.assertEqual(0, mock_sleep.call_count)
        self.assertEqual(0, mock_log_error.call_count)

    @patch.dict(os.environ, EXAMPLE_ENV_VAR1, clear=True)
    def test_validate_null_csv(self):
        """Tests that invalid file type returns FileNotFoundError"""
        with TestClient(app) as client:
            with open(SAMPLE_INVALID_EXT, "rb") as f:
                files = {
                    "file": f,
                }
                response = client.post(url="/api/validate_csv", files=files)
        self.assertEqual(response.status_code, 406)
        self.assertEqual(
            ["Invalid input file type"],
            response.json()["data"]["errors"],
        )

    @patch.dict(os.environ, EXAMPLE_ENV_VAR1, clear=True)
    def test_validate_malformed_csv(self):
        """Tests that invalid csv returns errors"""
        with TestClient(app) as client:
            with open(MALFORMED_SAMPLE_CSV, "rb") as f:
                files = {
                    "file": f,
                }
                response = client.post(url="/api/validate_csv", files=files)
        self.assertEqual(response.status_code, 406)
        self.assertEqual(
            ["AttributeError('Unknown Modality: WRONG_MODALITY_HERE',)"],
            response.json()["data"]["errors"],
        )

    @patch.dict(os.environ, EXAMPLE_ENV_VAR1, clear=True)
    def test_validate_malformed_xlsx(self):
        """Tests that invalid xlsx returns errors"""
        with TestClient(app) as client:
            with open(MALFORMED_SAMPLE_XLSX, "rb") as f:
                files = {
                    "file": f,
                }
                response = client.post(url="/api/validate_csv", files=files)
        self.assertEqual(response.status_code, 406)
        self.assertEqual(
            ["AttributeError('Unknown Modality: WRONG_MODALITY_HERE',)"],
            response.json()["data"]["errors"],
        )

    @patch.dict(os.environ, EXAMPLE_ENV_VAR1, clear=True)
    @patch("aind_data_transfer_service.server.sleep", return_value=None)
    @patch("aind_data_transfer_service.hpc.client.HpcClient.submit_hpc_job")
    def test_submit_hpc_jobs(
        self, mock_submit_job: MagicMock, mock_sleep: MagicMock
    ):
        """Tests submit hpc jobs success."""
        mock_response = Response()
        mock_response.status_code = 200
        mock_response._content = b'{"message": "success"}'
        mock_submit_job.return_value = mock_response
        post_request_content = {
            "jobs": [
                {
                    "hpc_settings": '{"qos":"production", "name": "job1"}',
                    "upload_job_settings": (
                        '{"project_name":"Ephys Platform", '
                        '"process_capsule_id":null, '
                        '"s3_bucket": "private", '
                        '"platform": {"name": "Behavior platform", '
                        '"abbreviation": "behavior"}, '
                        '"modalities": ['
                        '{"modality": {"name": "Behavior videos", '
                        '"abbreviation": "behavior-videos"}, '
                        '"source": "dir/data_set_2", '
                        '"compress_raw_data": true, '
                        '"skip_staging": false}], '
                        '"subject_id": "123456", '
                        '"acq_datetime": "2020-10-13T13:10:10", '
                        '"process_name": "Other", '
                        '"log_level": "WARNING", '
                        '"metadata_dir_force": false, '
                        '"dry_run": false, '
                        '"force_cloud_sync": false}'
                    ),
                    "script": "",
                },
                {
                    "hpc_settings": '{"qos":"production", "name": "job2"}',
                    "upload_job_settings": "{}",
                    "script": "run custom script",
                },
            ]
        }
        with TestClient(app) as client:
            submit_job_response = client.post(
                url="/api/submit_hpc_jobs", json=post_request_content
            )
        expected_response = {
            "message": "Submitted Jobs.",
            "data": {
                "responses": [{"message": "success"}, {"message": "success"}],
                "errors": [],
            },
        }
        self.assertEqual(expected_response, submit_job_response.json())
        self.assertEqual(200, submit_job_response.status_code)
        self.assertEqual(2, mock_sleep.call_count)

    @patch.dict(os.environ, EXAMPLE_ENV_VAR1, clear=True)
    @patch("aind_data_transfer_service.server.sleep", return_value=None)
    @patch("aind_data_transfer_service.hpc.client.HpcClient.submit_hpc_job")
    @patch(
        "aind_data_transfer_service.hpc.models.HpcJobSubmitSettings"
        ".from_upload_job_configs"
    )
    def test_submit_hpc_jobs_open_data(
        self,
        mock_from_upload_configs: MagicMock,
        mock_submit_job: MagicMock,
        mock_sleep: MagicMock,
    ):
        """Tests submit hpc jobs success."""
        mock_response = Response()
        mock_response.status_code = 200
        mock_response._content = b'{"message": "success"}'
        mock_submit_job.return_value = mock_response
        # When a user specifies aind-open-data in the upload_job_settings,
        # use the credentials for that account.
        post_request_content = {
            "jobs": [
                {
                    "hpc_settings": '{"qos":"production", "name": "job1"}',
                    "upload_job_settings": (
                        '{"project_name":"Ephys Platform", '
                        '"process_capsule_id":null, '
                        '"s3_bucket": "open", '
                        '"platform": {"name": "Behavior platform", '
                        '"abbreviation": "behavior"}, '
                        '"modalities": ['
                        '{"modality": {"name": "Behavior videos", '
                        '"abbreviation": "behavior-videos"}, '
                        '"source": "dir/data_set_2", '
                        '"compress_raw_data": true, '
                        '"skip_staging": false}], '
                        '"subject_id": "123456", '
                        '"acq_datetime": "2020-10-13T13:10:10", '
                        '"process_name": "Other", '
                        '"log_level": "WARNING", '
                        '"metadata_dir_force": false, '
                        '"dry_run": false, '
                        '"force_cloud_sync": false}'
                    ),
                    "script": "",
                }
            ]
        }
        with TestClient(app) as client:
            submit_job_response = client.post(
                url="/api/submit_hpc_jobs", json=post_request_content
            )
        expected_response = {
            "message": "Submitted Jobs.",
            "data": {
                "responses": [{"message": "success"}],
                "errors": [],
            },
        }
        self.assertEqual(expected_response, submit_job_response.json())
        self.assertEqual(200, submit_job_response.status_code)
        self.assertEqual(1, mock_sleep.call_count)
        mock_from_upload_configs.assert_called_with(
            logging_directory=PurePosixPath("hpc_logs"),
            aws_secret_access_key=SecretStr("open_data_aws_key"),
            aws_access_key_id="open_data_aws_key_id",
            aws_default_region="aws_region",
            aws_session_token=None,
            qos="production",
            name="behavior_123456_2020-10-13_13-10-10",
        )

    @patch.dict(os.environ, EXAMPLE_ENV_VAR1, clear=True)
    @patch("aind_data_transfer_service.server.sleep", return_value=None)
    @patch("aind_data_transfer_service.hpc.client.HpcClient.submit_hpc_job")
    @patch("logging.error")
    def test_submit_hpc_jobs_error(
        self,
        mock_log_error: MagicMock,
        mock_submit_job: MagicMock,
        mock_sleep: MagicMock,
    ):
        """Tests that submit jobs returns error if there's an issue with hpc"""
        mock_response = Response()
        mock_response.status_code = 200
        mock_submit_job.return_value = mock_response
        post_request_content = {
            "jobs": [
                {
                    "hpc_settings": '{"qos":"production"}',
                    "upload_job_settings": '{"temp_directory":"tmp"}',
                    "script": "run script",
                },
                {
                    "hpc_settings": '{"qos":"production", "name": "job2"}',
                    "upload_job_settings": '{"temp_directory":"tmp"}',
                    "script": "run script",
                },
            ]
        }
        with TestClient(app) as client:
            submit_job_response = client.post(
                url="/api/submit_hpc_jobs", json=post_request_content
            )
        expected_response = {
            "message": "There were errors parsing the job configs",
            "data": {
                "responses": [],
                "errors": [
                    'Error parsing {"temp_directory":"tmp"}: '
                    "KeyError('name')"
                ],
            },
        }
        self.assertEqual(expected_response, submit_job_response.json())
        self.assertEqual(406, submit_job_response.status_code)
        self.assertEqual(0, mock_sleep.call_count)
        self.assertEqual(0, mock_log_error.call_count)

    @patch.dict(os.environ, EXAMPLE_ENV_VAR1, clear=True)
    @patch("aind_data_transfer_service.server.sleep", return_value=None)
    @patch("aind_data_transfer_service.hpc.client.HpcClient.submit_hpc_job")
    @patch("logging.error")
    def test_submit_hpc_jobs_server_error(
        self,
        mock_log_error: MagicMock,
        mock_submit_job: MagicMock,
        mock_sleep: MagicMock,
    ):
        """Tests that submit jobs returns error if there's an issue with hpc"""
        mock_response = Response()
        mock_response.status_code = 500
        mock_submit_job.return_value = mock_response
        post_request_content = {
            "jobs": [
                {
                    "hpc_settings": '{"qos":"production", "name": "job1"}',
                    "upload_job_settings": '{"temp_directory":"tmp"}',
                    "script": "run script",
                },
                {
                    "hpc_settings": '{"qos":"production", "name": "job2"}',
                    "upload_job_settings": '{"temp_directory":"tmp"}',
                    "script": "run script",
                },
            ]
        }
        with TestClient(app) as client:
            submit_job_response = client.post(
                url="/api/submit_hpc_jobs", json=post_request_content
            )
        expected_response = {
            "message": "There were errors submitting jobs to the hpc.",
            "data": {
                "responses": [],
                "errors": ["Error processing job1", "Error processing job2"],
            },
        }
        self.assertEqual(expected_response, submit_job_response.json())
        self.assertEqual(500, submit_job_response.status_code)
        self.assertEqual(0, mock_sleep.call_count)
        self.assertEqual(2, mock_log_error.call_count)

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

    def test_download_job_template(self):
        """Tests that job template downloads as xlsx file."""

        with TestClient(app) as client:
            response = client.get("/api/job_upload_template")

        expected_job_template = JobUploadTemplate()
        expected_file_stream = expected_job_template.excel_sheet_filestream
        expected_streaming_response = StreamingResponse(
            BytesIO(expected_file_stream.getvalue()),
            media_type=(
                "application/"
                "vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            ),
            headers={
                "Content-Disposition": (
                    f"attachment; filename={expected_job_template.FILE_NAME}"
                )
            },
            status_code=200,
        )

        self.assertEqual(
            expected_streaming_response.headers.items(),
            list(response.headers.items()),
        )
        self.assertEqual(200, response.status_code)

    @patch("aind_data_transfer_service.server.JobUploadTemplate")
    @patch("logging.error")
    def test_download_invalid_job_template(
        self, mock_log_error: MagicMock, mock_job_template: MagicMock
    ):
        """Tests that download invalid job template returns errors."""
        mock_job_template.side_effect = Exception("mock invalid job template")
        with TestClient(app) as client:
            response = client.get("/api/job_upload_template")
        expected_response = {
            "message": "Error creating job template",
            "data": {"error": "Exception('mock invalid job template',)"},
        }
        self.assertEqual(500, response.status_code)
        self.assertEqual(expected_response, response.json())
        mock_log_error.assert_called_once()


if __name__ == "__main__":
    unittest.main()
