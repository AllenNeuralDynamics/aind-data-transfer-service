"""Tests server module."""

import json
import os
import unittest
import warnings
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from io import BytesIO
from pathlib import Path, PurePosixPath
from unittest.mock import AsyncMock, MagicMock, patch

from aind_data_schema_models.modalities import Modality
from aind_data_schema_models.platforms import Platform
from aind_data_transfer_models import (
    __version__ as aind_data_transfer_models_version,
)
from aind_data_transfer_models.core import (
    BasicUploadJobConfigs,
    ModalityConfigs,
    SubmitJobRequest,
    V0036JobProperties,
)
from aind_data_transfer_models.trigger import TriggerConfigModel, ValidJobType
from authlib.integrations.starlette_client import OAuthError
from botocore.exceptions import ClientError
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.testclient import TestClient
from pydantic import SecretStr
from requests import Response

from aind_data_transfer_service import (
    __version__ as aind_data_transfer_service_version,
)
from aind_data_transfer_service.configs.job_upload_template import (
    JobUploadTemplate,
)
from aind_data_transfer_service.models.core import (
    SubmitJobRequestV2,
    Task,
    UploadJobConfigsV2,
)
from aind_data_transfer_service.models.internal import (
    AirflowDagRunsRequestParameters,
    JobParamInfo,
)
from aind_data_transfer_service.server import (
    app,
    get_job_types,
    get_project_names,
)
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

NEW_SAMPLE_CSV = TEST_DIRECTORY / "resources" / "new_sample.csv"
MALFORMED_SAMPLE_CSV_2 = (
    TEST_DIRECTORY / "resources" / "sample_malformed_2.csv"
)
SAMPLE_CSV_EMPTY_ROWS_2 = (
    TEST_DIRECTORY / "resources" / "sample_empty_rows_2.csv"
)

LIST_DAG_RUNS_RESPONSE = (
    TEST_DIRECTORY / "resources" / "airflow_dag_runs_response.json"
)
GET_DAG_RUN_RESPONSE = (
    TEST_DIRECTORY / "resources" / "airflow_dag_run_response.json"
)
LIST_TASK_INSTANCES_RESPONSE = (
    TEST_DIRECTORY / "resources" / "airflow_task_instances_response.json"
)
DESCRIBE_PARAMETERS_RESPONSE = (
    TEST_DIRECTORY / "resources" / "describe_parameters_response.json"
)
GET_PARAMETER_RESPONSE = (
    TEST_DIRECTORY / "resources" / "get_parameter_response.json"
)
GET_SECRETS_RESPONSE = (
    TEST_DIRECTORY / "resources" / "get_secrets_response.json"
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
        "HPC_STAGING_DIRECTORY": "stage/dir",
        "HPC_AWS_PARAM_STORE_NAME": "/some/param/store",
        "OPEN_DATA_AWS_SECRET_ACCESS_KEY": "open_data_aws_key",
        "OPEN_DATA_AWS_ACCESS_KEY_ID": "open_data_aws_key_id",
        "AIND_AIRFLOW_SERVICE_JOBS_URL": "airflow_jobs_url",
        "AIND_AIRFLOW_SERVICE_USER": "airflow_user",
        "AIND_AIRFLOW_SERVICE_PASSWORD": "airflow_password",
        "AIND_AIRFLOW_PARAM_PREFIX": "/param_prefix",
        "AIND_SSO_SECRET_NAME": "/secret/name",
    }

    with open(SAMPLE_CSV, "r") as file:
        csv_content = file.read()

    with open(MOCK_DB_FILE) as f:
        json_contents = json.load(f)

    with open(LIST_DAG_RUNS_RESPONSE) as f:
        list_dag_runs_response = json.load(f)

    with open(GET_DAG_RUN_RESPONSE) as f:
        get_dag_run_response = json.load(f)

    with open(LIST_TASK_INSTANCES_RESPONSE) as f:
        list_task_instances_response = json.load(f)

    with open(DESCRIBE_PARAMETERS_RESPONSE) as f:
        describe_parameters_response = json.load(f)

    with open(GET_PARAMETER_RESPONSE) as f:
        get_parameter_response = json.load(f)

    with open(GET_SECRETS_RESPONSE) as f:
        get_secrets_response = json.load(f)

    expected_job_configs = deepcopy(TestJobConfigs.expected_job_configs)
    for config in expected_job_configs:
        config.aws_param_store_name = None

    @classmethod
    def setUpClass(cls) -> None:
        """Set up test class"""
        # create example UploadJobConfigsV2
        job_type = "ecephys"
        project_name = "Ephys Platform"
        platform = Platform.ECEPHYS
        subject_id = "690165"
        acq_datetime = datetime(2024, 2, 19, 11, 25, 17)
        ephys_source_dir = PurePosixPath("shared_drive/ephys_data/690165")
        ephys_config = Task(
            dynamic_parameters_settings={
                "modality": Modality.ECEPHYS.model_dump(mode="json"),
                "source": ephys_source_dir.as_posix(),
            }
        )
        example_configs_v2 = UploadJobConfigsV2(
            job_type=job_type,
            project_name=project_name,
            platform=platform,
            subject_id=subject_id,
            acq_datetime=acq_datetime,
            modalities=[Modality.ECEPHYS],
            tasks={"make_modality_list": ephys_config},
        )
        cls.example_configs_v2 = example_configs_v2

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
    @patch("logging.Logger.error")
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
    @patch("logging.Logger.error")
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
    @patch("logging.Logger.error")
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
    @patch("logging.Logger.error")
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

    @patch("requests.get")
    def test_get_project_names(self, mock_get: MagicMock):
        """Tests get_project_names method"""
        mock_response = Response()
        mock_response.status_code = 200
        mock_response._content = json.dumps(
            {"data": ["project_name_0", "project_name_1"]}
        ).encode("utf-8")
        mock_get.return_value = mock_response
        project_names = get_project_names()
        self.assertEqual(["project_name_0", "project_name_1"], project_names)

    @patch("aind_data_transfer_service.server.get_parameter_infos")
    def test_get_job_types(self, mock_get_parameter_infos: MagicMock):
        """Tests get_job_types method"""
        tasks = [
            ("job1", "task1", None),
            ("job1", "task2", None),
            ("job2", "task1", "modality1"),
        ]
        mock_get_parameter_infos.return_value = [
            JobParamInfo(
                name=f"/param_prefix/v2/{t[0]}/tasks/{t[1]}",
                job_type=t[0],
                task_id=t[1],
                modality=t[2],
                last_modified=None,
            )
            for t in tasks
        ]
        job_types = get_job_types("v2")
        mock_get_parameter_infos.assert_called_once_with("v2")
        self.assertCountEqual(["job1", "job2"], job_types)

    @patch.dict(os.environ, EXAMPLE_ENV_VAR1, clear=True)
    @patch("httpx.AsyncClient.post")
    def test_get_job_status_list_default(
        self,
        mock_post,
    ):
        """Tests get_job_status_list gets paginated dagRuns from airflow using
        default limit and offset."""
        mock_dag_runs_response = Response()
        mock_dag_runs_response.status_code = 200
        mock_dag_runs_response._content = json.dumps(
            self.list_dag_runs_response
        ).encode("utf-8")
        mock_post.return_value = mock_dag_runs_response
        expected_message = "Retrieved job status list from airflow"
        expected_default_params = {
            "dag_ids": ["transform_and_upload", "transform_and_upload_v2"],
            "page_limit": 100,
            "page_offset": 0,
            "states": [],
            "execution_date_gte": "mock_execution_date_gte",
            "order_by": "-execution_date",
        }
        expected_job_status_list = [
            {
                "dag_id": "transform_and_upload",
                "end_time": "2024-05-18T22:09:28.530534Z",
                "job_id": "manual__2024-05-18T22:08:52.286765+00:00",
                "job_state": "failed",
                "name": "",
                "job_type": "",
                "comment": None,
                "start_time": "2024-05-18T22:08:52.637098Z",
                "submit_time": "2024-05-18T22:08:52.286765Z",
            },
            {
                "dag_id": "transform_and_upload",
                "end_time": "2024-05-18T22:09:38.581375Z",
                "job_id": "manual__2024-05-18T22:08:53.931985+00:00",
                "job_state": "failed",
                "name": "",
                "job_type": "",
                "comment": None,
                "start_time": "2024-05-18T22:08:54.712420Z",
                "submit_time": "2024-05-18T22:08:53.931985Z",
            },
            {
                "dag_id": "transform_and_upload",
                "end_time": "2024-05-18T22:47:49.080108Z",
                "job_id": "manual__2024-05-18T22:32:50.569083+00:00",
                "job_state": "success",
                "name": "ecephys_655019_2000-01-01_01-40-03",
                "job_type": "",
                "comment": None,
                "start_time": "2024-05-18T22:32:50.996318Z",
                "submit_time": "2024-05-18T22:32:50.569083Z",
            },
            {
                "dag_id": "transform_and_upload",
                "end_time": "2024-05-18T22:47:58.559508Z",
                "job_id": "manual__2024-05-18T22:32:52.804228+00:00",
                "job_state": "success",
                "name": "ecephys_655019_2000-01-01_01-40-04",
                "job_type": "",
                "comment": None,
                "start_time": "2024-05-18T22:32:53.493901Z",
                "submit_time": "2024-05-18T22:32:52.804228Z",
            },
            {
                "dag_id": "transform_and_upload",
                "end_time": "2024-05-18T23:51:17.716003Z",
                "job_id": "manual__2024-05-18T23:43:19.184853+00:00",
                "job_state": "failed",
                "name": "ecephys_655019_2000-10-10_01-00-24",
                "job_type": "",
                "comment": None,
                "start_time": "2024-05-18T23:43:19.428659Z",
                "submit_time": "2024-05-18T23:43:19.184853Z",
            },
        ]
        with TestClient(app) as client:
            response = client.get("/api/v1/get_job_status_list")
        response_content = response.json()
        # small hack to mock the date
        response_content["data"]["params"][
            "execution_date_gte"
        ] = "mock_execution_date_gte"
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response_content,
            {
                "message": expected_message,
                "data": {
                    "params": expected_default_params,
                    "total_entries": self.list_dag_runs_response[
                        "total_entries"
                    ],
                    "job_status_list": expected_job_status_list,
                },
            },
        )
        mock_post.assert_called_once()
        self.assertEqual(
            mock_post.call_args_list[0][0][0],
            "airflow_jobs_url/~/dagRuns/list",
        )

    @patch.dict(os.environ, EXAMPLE_ENV_VAR1, clear=True)
    @patch("httpx.AsyncClient.post")
    def test_get_job_status_list_query_params(
        self,
        mock_post,
    ):
        """Tests get_job_status_list gets paginated dagRuns from airflow using
        query_params."""
        mock_dag_runs_response = Response()
        mock_dag_runs_response.status_code = 200
        mock_dag_runs_response._content = json.dumps(
            self.list_dag_runs_response
        ).encode("utf-8")
        mock_post.return_value = mock_dag_runs_response
        expected_message = "Retrieved job status list from airflow"
        with TestClient(app) as client:
            response = client.get(
                "/api/v1/get_job_status_list",
                params={
                    "page_limit": 10,
                    "page_offset": 5,
                    "execution_date_gte": (
                        datetime.now(timezone.utc) - timedelta(days=2)
                    ).strftime("%Y-%m-%dT%H:%M:%SZ"),
                },
            )
        response_content = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response_content["message"], expected_message)
        self.assertEqual(response_content["data"]["params"]["page_limit"], 10)
        self.assertEqual(response_content["data"]["params"]["page_offset"], 5)
        mock_post.assert_called_once()
        self.assertEqual(
            mock_post.call_args_list[0][0][0],
            "airflow_jobs_url/~/dagRuns/list",
        )

    @patch.dict(os.environ, EXAMPLE_ENV_VAR1, clear=True)
    @patch("httpx.AsyncClient.post")
    @patch("logging.Logger.warning")
    def test_get_job_status_list_validation_error(
        self,
        mock_log_warning: MagicMock,
        mock_post,
    ):
        """Tests get_job_status_list when query_params are invalid."""
        invalid_queries = [
            {"page_limit": "invalid", "page_offset": 5},
            {"page_limit": 5, "page_offset": "invalid"},
            {
                "execution_date_gte": (
                    datetime.now(timezone.utc)
                    - timedelta(weeks=2)
                    - timedelta(minutes=1)
                ).strftime("%Y-%m-%dT%H:%M:%SZ")
            },
        ]
        for query in invalid_queries:
            with TestClient(app) as client:
                response = client.get(
                    "/api/v1/get_job_status_list", params=query
                )
            response_content = response.json()
            self.assertEqual(response.status_code, 406)
            self.assertEqual(
                response_content["message"],
                "Error validating request parameters",
            )
        mock_log_warning.assert_called()
        mock_post.assert_not_called()

    @patch.dict(os.environ, EXAMPLE_ENV_VAR1, clear=True)
    @patch("httpx.AsyncClient.post")
    def test_get_job_status_list_get_all_jobs(
        self,
        mock_post,
    ):
        """Tests get_job_status_list when there are many jobs."""

        def mock_airflow_dags(url, **kwargs):
            """Mocks the response from airflow."""
            limit = int(kwargs["json"].get("page_limit"))
            mock_dag_runs_response = Response()
            mock_dag_runs_response.status_code = 200
            mock_dag_runs_response._content = json.dumps(
                {
                    "total_entries": 300,
                    "dag_runs": [
                        self.get_dag_run_response for _ in range(limit)
                    ],
                }
            ).encode("utf-8")
            return mock_dag_runs_response

        mock_post.side_effect = mock_airflow_dags
        expected_message = "Retrieved job status list from airflow"
        with TestClient(app) as client:
            response = client.get("/api/v1/get_job_status_list")
        response_content = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response_content["message"], expected_message)
        self.assertEqual(response_content["data"]["total_entries"], 300)
        self.assertEqual(len(response_content["data"]["job_status_list"]), 300)

    @patch.dict(os.environ, EXAMPLE_ENV_VAR1, clear=True)
    @patch("logging.Logger.exception")
    @patch("httpx.AsyncClient.post")
    def test_get_job_status_list_error(
        self,
        mock_post: MagicMock,
        mock_log_error: MagicMock,
    ):
        """Tests get_job_status_list when there is an error sending request."""
        mock_post.side_effect = Exception("mock error")
        with TestClient(app) as client:
            response = client.get("/api/v1/get_job_status_list")
        response_content = response.json()
        self.assertEqual(response.status_code, 500)
        self.assertEqual(
            response_content["message"],
            "Unable to retrieve job status list from airflow",
        )
        mock_log_error.assert_called_once()
        mock_post.assert_called_once()
        self.assertEqual(
            mock_post.call_args_list[0][0][0],
            "airflow_jobs_url/~/dagRuns/list",
        )

    @patch.dict(os.environ, EXAMPLE_ENV_VAR1, clear=True)
    @patch("requests.get")
    def test_get_tasks_list_query_params(
        self,
        mock_get,
    ):
        """Tests get_tasks_list gets tasks from airflow using query_params."""
        mock_task_instances_response = Response()
        mock_task_instances_response.status_code = 200
        mock_task_instances_response._content = json.dumps(
            self.list_task_instances_response
        ).encode("utf-8")
        mock_get.return_value = mock_task_instances_response
        expected_message = "Retrieved job tasks list from airflow"
        expected_params = {
            "dag_id": "transform_and_upload",
            "dag_run_id": "mock_dag_run_id",
        }
        expected_task_list = [
            {
                "dag_id": "transform_and_upload",
                "job_id": "manual__2024-08-21T16:16:54.302335+00:00",
                "task_id": "send_job_start_email",
                "try_number": 1,
                "task_state": "success",
                "priority_weight": 13,
                "map_index": -1,
                "submit_time": "2024-08-21T16:16:54.302335Z",
                "start_time": "2024-08-21T16:17:10.821126Z",
                "end_time": "2024-08-21T16:17:11.720301Z",
                "duration": 0.899175,
                "comment": None,
            },
            {
                "dag_id": "transform_and_upload",
                "job_id": "manual__2024-08-21T16:16:54.302335+00:00",
                "task_id": "create_default_settings",
                "try_number": 1,
                "task_state": "success",
                "priority_weight": 12,
                "map_index": -1,
                "submit_time": "2024-08-21T16:16:54.302335Z",
                "start_time": "2024-08-21T16:17:26.235462Z",
                "end_time": "2024-08-21T16:17:27.278459Z",
                "duration": 1.042997,
                "comment": None,
            },
            {
                "dag_id": "transform_and_upload",
                "job_id": "manual__2024-08-21T16:16:54.302335+00:00",
                "task_id": "check_s3_folder_exist",
                "try_number": 1,
                "task_state": "success",
                "priority_weight": 11,
                "map_index": -1,
                "submit_time": "2024-08-21T16:16:54.302335Z",
                "start_time": "2024-08-21T16:17:43.401342Z",
                "end_time": "2024-08-21T16:17:44.463969Z",
                "duration": 1.062627,
                "comment": None,
            },
            {
                "dag_id": "transform_and_upload",
                "job_id": "manual__2024-08-21T16:16:54.302335+00:00",
                "task_id": "create_default_slurm_environment",
                "try_number": 1,
                "task_state": "success",
                "priority_weight": 10,
                "map_index": -1,
                "submit_time": "2024-08-21T16:16:54.302335Z",
                "start_time": "2024-08-21T16:17:59.685662Z",
                "end_time": "2024-08-21T16:18:00.491290Z",
                "duration": 0.805628,
                "comment": None,
            },
            {
                "dag_id": "transform_and_upload",
                "job_id": "manual__2024-08-21T16:16:54.302335+00:00",
                "task_id": "check_source_folders_exist",
                "try_number": 1,
                "task_state": "success",
                "priority_weight": 9,
                "map_index": -1,
                "submit_time": "2024-08-21T16:16:54.302335Z",
                "start_time": "2024-08-21T16:18:15.464289Z",
                "end_time": "2024-08-21T16:18:47.027590Z",
                "duration": 31.563301,
                "comment": None,
            },
            {
                "dag_id": "transform_and_upload",
                "job_id": "manual__2024-08-21T16:16:54.302335+00:00",
                "task_id": "create_folder",
                "try_number": 1,
                "task_state": "success",
                "priority_weight": 8,
                "map_index": -1,
                "submit_time": "2024-08-21T16:16:54.302335Z",
                "start_time": "2024-08-21T16:19:02.513498Z",
                "end_time": "2024-08-21T16:20:04.200273Z",
                "duration": 61.686775,
                "comment": None,
            },
            {
                "dag_id": "transform_and_upload",
                "job_id": "manual__2024-08-21T16:16:54.302335+00:00",
                "task_id": "make_modality_list",
                "try_number": 1,
                "task_state": "success",
                "priority_weight": 7,
                "map_index": -1,
                "submit_time": "2024-08-21T16:16:54.302335Z",
                "start_time": "2024-08-21T16:17:13.130978Z",
                "end_time": "2024-08-21T16:17:13.886610Z",
                "duration": 0.755632,
                "comment": None,
            },
            {
                "dag_id": "transform_and_upload",
                "job_id": "manual__2024-08-21T16:16:54.302335+00:00",
                "task_id": "gather_preliminary_metadata",
                "try_number": 1,
                "task_state": "success",
                "priority_weight": 7,
                "map_index": -1,
                "submit_time": "2024-08-21T16:16:54.302335Z",
                "start_time": "2024-08-21T16:20:19.088935Z",
                "end_time": "2024-08-21T16:22:20.807546Z",
                "duration": 121.718611,
                "comment": None,
            },
            {
                "dag_id": "transform_and_upload",
                "job_id": "manual__2024-08-21T16:16:54.302335+00:00",
                "task_id": "compress_data",
                "try_number": 1,
                "task_state": "success",
                "priority_weight": 6,
                "map_index": 0,
                "submit_time": "2024-08-21T16:16:54.302335Z",
                "start_time": "2024-08-21T16:22:36.503206Z",
                "end_time": "2024-08-21T16:24:38.400648Z",
                "duration": 121.897442,
                "comment": None,
            },
            {
                "dag_id": "transform_and_upload",
                "job_id": "manual__2024-08-21T16:16:54.302335+00:00",
                "task_id": "gather_final_metadata",
                "try_number": 1,
                "task_state": "success",
                "priority_weight": 5,
                "map_index": -1,
                "submit_time": "2024-08-21T16:16:54.302335Z",
                "start_time": "2024-08-21T16:24:52.639358Z",
                "end_time": "2024-08-21T16:26:54.539535Z",
                "duration": 121.900177,
                "comment": None,
            },
            {
                "dag_id": "transform_and_upload",
                "job_id": "manual__2024-08-21T16:16:54.302335+00:00",
                "task_id": "upload_data_to_s3",
                "try_number": 1,
                "task_state": "success",
                "priority_weight": 4,
                "map_index": -1,
                "submit_time": "2024-08-21T16:16:54.302335Z",
                "start_time": "2024-08-21T16:27:10.130605Z",
                "end_time": "2024-08-21T16:29:11.984181Z",
                "duration": 121.853576,
                "comment": None,
            },
            {
                "dag_id": "transform_and_upload",
                "job_id": "manual__2024-08-21T16:16:54.302335+00:00",
                "task_id": "send_codeocean_request",
                "try_number": 1,
                "task_state": "success",
                "priority_weight": 2,
                "map_index": -1,
                "submit_time": "2024-08-21T16:16:54.302335Z",
                "start_time": "2024-08-21T16:29:29.069360Z",
                "end_time": "2024-08-21T16:29:39.612352Z",
                "duration": 10.542992,
                "comment": None,
            },
            {
                "dag_id": "transform_and_upload",
                "job_id": "manual__2024-08-21T16:16:54.302335+00:00",
                "task_id": "remove_folder",
                "try_number": 1,
                "task_state": "success",
                "priority_weight": 2,
                "map_index": -1,
                "submit_time": "2024-08-21T16:16:54.302335Z",
                "start_time": "2024-08-21T16:29:27.847630Z",
                "end_time": "2024-08-21T16:31:29.653235Z",
                "duration": 121.805605,
                "comment": None,
            },
            {
                "dag_id": "transform_and_upload",
                "job_id": "manual__2024-08-21T16:16:54.302335+00:00",
                "task_id": "send_job_end_email",
                "try_number": 1,
                "task_state": "success",
                "priority_weight": 1,
                "map_index": -1,
                "submit_time": "2024-08-21T16:16:54.302335Z",
                "start_time": "2024-08-21T16:31:45.560918Z",
                "end_time": "2024-08-21T16:31:46.502387Z",
                "duration": 0.941469,
                "comment": None,
            },
        ]
        with TestClient(app) as client:
            response = client.get(
                "/api/v1/get_tasks_list",
                params={
                    "dag_id": "transform_and_upload",
                    "dag_run_id": "mock_dag_run_id",
                },
            )
        response_content = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response_content,
            {
                "message": expected_message,
                "data": {
                    "params": expected_params,
                    "total_entries": self.list_task_instances_response[
                        "total_entries"
                    ],
                    "job_tasks_list": expected_task_list,
                },
            },
        )

    @patch.dict(os.environ, EXAMPLE_ENV_VAR1, clear=True)
    @patch("requests.get")
    @patch("logging.Logger.warning")
    def test_get_tasks_list_validation_error(
        self,
        mock_log_error: MagicMock,
        mock_get,
    ):
        """Tests get_tasks_list when query_params are invalid."""
        invalid_params = {
            "job_id": "mock_dag_run_id",
        }
        with TestClient(app) as client:
            response = client.get(
                "/api/v1/get_tasks_list", params=invalid_params
            )
        response_content = response.json()
        self.assertEqual(response.status_code, 406)
        self.assertEqual(
            response_content["message"],
            "Error validating request parameters",
        )
        mock_log_error.assert_called()
        mock_get.assert_not_called()

    @patch.dict(os.environ, EXAMPLE_ENV_VAR1, clear=True)
    @patch("logging.Logger.exception")
    @patch("requests.get")
    def test_get_tasks_list_error(
        self,
        mock_get: MagicMock,
        mock_log_error: MagicMock,
    ):
        """Tests get_tasks_list when there is an error sending request."""
        mock_get.side_effect = Exception("mock error")
        with TestClient(app) as client:
            response = client.get(
                "/api/v1/get_tasks_list",
                params={
                    "dag_id": "transform_and_upload",
                    "dag_run_id": "mock_dag_run_id",
                },
            )
        response_content = response.json()
        self.assertEqual(response.status_code, 500)
        self.assertEqual(
            response_content["message"],
            "Unable to retrieve job tasks list from airflow",
        )
        mock_log_error.assert_called_once()

    @patch.dict(os.environ, EXAMPLE_ENV_VAR1, clear=True)
    @patch("requests.get")
    def test_get_task_logs_query_params(
        self,
        mock_get,
    ):
        """Tests get_task_logs gets logs from airflow using query_params."""
        mock_logs_response = Response()
        mock_logs_response.status_code = 200
        mock_logs_response._content = b"mock logs"
        mock_get.return_value = mock_logs_response
        expected_message = "Retrieved task logs from airflow"
        expected_default_params = {
            "dag_id": "mock_dag_id",
            "dag_run_id": "mock_dag_run_id",
            "task_id": "mock_task_id",
            "try_number": 1,
            "map_index": -1,
            "full_content": True,
        }
        with TestClient(app) as client:
            response = client.get(
                "/api/v1/get_task_logs",
                params={
                    "dag_id": "mock_dag_id",
                    "dag_run_id": "mock_dag_run_id",
                    "task_id": "mock_task_id",
                    "try_number": 1,
                    "map_index": -1,
                },
            )
        response_content = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response_content,
            {
                "message": expected_message,
                "data": {
                    "params": expected_default_params,
                    "logs": "mock logs",
                },
            },
        )

    @patch.dict(os.environ, EXAMPLE_ENV_VAR1, clear=True)
    @patch("requests.get")
    @patch("logging.Logger.warning")
    def test_get_task_logs_validation_error(
        self,
        mock_log_error: MagicMock,
        mock_get,
    ):
        """Tests get_task_logs when query_params are invalid."""
        invalid_params = {
            "dag_id": "mock_dag_id",
            "dag_run_id": "mock_dag_run_id",
            "task_id": "mock_task_id",
            "try_number": "invalid",
        }
        with TestClient(app) as client:
            response = client.get(
                "/api/v1/get_task_logs", params=invalid_params
            )
        response_content = response.json()
        self.assertEqual(response.status_code, 406)
        self.assertEqual(
            response_content["message"],
            "Error validating request parameters",
        )
        mock_log_error.assert_called()
        mock_get.assert_not_called()

    @patch.dict(os.environ, EXAMPLE_ENV_VAR1, clear=True)
    @patch("logging.Logger.exception")
    @patch("requests.get")
    def test_get_task_logs_error(
        self,
        mock_get: MagicMock,
        mock_log_error: MagicMock,
    ):
        """Tests get_task_logs when there is an error sending request."""
        mock_get.side_effect = Exception("mock error")
        with TestClient(app) as client:
            response = client.get(
                "/api/v1/get_task_logs",
                params={
                    "dag_id": "transform_and_upload",
                    "dag_run_id": "mock_dag_run_id",
                    "task_id": "mock_task_id",
                    "try_number": 1,
                    "map_index": -1,
                },
            )
        response_content = response.json()
        self.assertEqual(response.status_code, 500)
        self.assertEqual(
            response_content["message"],
            "Unable to retrieve task logs from airflow",
        )
        mock_log_error.assert_called_once()

    @patch("logging.Logger.info")
    @patch.dict(os.environ, EXAMPLE_ENV_VAR1, clear=True)
    @patch("boto3.client")
    def test_list_parameters(
        self,
        mock_ssm_client,
        mock_log_info: MagicMock,
    ):
        """Tests list_parameters gets parameter info from aws param store."""
        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = (
            self.describe_parameters_response
        )
        mock_ssm_client.return_value.get_paginator.return_value = (
            mock_paginator
        )
        expected_params = {
            "v1": [
                {
                    "job_type": "job1",
                    "last_modified": "2025-01-23T11:50:04.535000-08:00",
                    "name": "/param_prefix/job1/tasks/task1",
                    "task_id": "task1",
                    "modality": None,
                },
                {
                    "job_type": "job2",
                    "last_modified": "2025-01-23T11:50:04.605000-08:00",
                    "name": "/param_prefix/job2/tasks/task2",
                    "task_id": "task2",
                    "modality": None,
                },
            ],
            "v2": [
                {
                    "job_type": "job1",
                    "last_modified": "2025-01-23T11:50:04.605000-08:00",
                    "name": "/param_prefix/v2/job1/tasks/task1",
                    "task_id": "task1",
                    "modality": None,
                },
                {
                    "job_type": "job1",
                    "last_modified": "2025-01-23T11:50:04.605000-08:00",
                    "name": "/param_prefix/v2/job1/tasks/task2/modality1",
                    "task_id": "task2",
                    "modality": "modality1",
                },
            ],
        }
        for version, params_list in expected_params.items():
            with TestClient(app) as client:
                response = client.get(f"/api/{version}/parameters")
            mock_ssm_client.assert_called_with("ssm")
            mock_ssm_client.return_value.get_paginator.assert_called_with(
                "describe_parameters"
            )
            if version == "v1":
                expected_filter = "/param_prefix"
            else:
                expected_filter = f"/param_prefix/{version}"
            mock_paginator.paginate.assert_called_with(
                ParameterFilters=[
                    {
                        "Key": "Path",
                        "Option": "Recursive",
                        "Values": [expected_filter],
                    }
                ]
            )
            response_content = response.json()
            self.assertEqual(response.status_code, 200)
            self.assertEqual(
                response_content,
                {
                    "message": "Retrieved job parameters",
                    "data": params_list,
                },
            )
            # params that do not match expected format are ignored
            mock_log_info.assert_any_call(
                "Ignoring /param_prefix/unexpected_param"
            )

    @patch.dict(os.environ, EXAMPLE_ENV_VAR1, clear=True)
    @patch("boto3.client")
    def test_get_parameter(
        self,
        mock_ssm_client,
    ):
        """Tests get_parameter retrieves values from aws param store."""
        mock_ssm_client.return_value.get_parameter.return_value = (
            self.get_parameter_response
        )
        expected_params = {
            "v1": "/param_prefix/ecephys/tasks/task1",
            "v2": "/param_prefix/v2/ecephys/tasks/task1",
        }
        for version, param_name in expected_params.items():
            with TestClient(app) as client:
                response = client.get(
                    f"/api/{version}/parameters/job_types/ecephys/tasks/task1"
                )
            mock_ssm_client.assert_called_with("ssm")
            mock_ssm_client.return_value.get_parameter.assert_called_with(
                Name=param_name, WithDecryption=True
            )
            response_content = response.json()
            self.assertEqual(response.status_code, 200)
            self.assertEqual(
                response_content,
                {
                    "message": f"Retrieved parameter for {param_name}",
                    "data": {"foo": "bar"},
                },
            )

    @patch("logging.Logger.exception")
    @patch.dict(os.environ, EXAMPLE_ENV_VAR1, clear=True)
    @patch("boto3.client")
    def test_get_parameter_error(
        self,
        mock_ssm_client,
        mock_log_error: MagicMock,
    ):
        """Tests get_parameter when there is a client error."""
        mock_ssm_client.return_value.get_parameter.side_effect = ClientError(
            {
                "Error": {
                    "Code": "ParameterNotFound",
                    "Message": "Parameter not found",
                }
            },
            "GetParameter",
        )
        expected_params = {
            "v1": "/param_prefix/foo/tasks/bar",
            "v2": "/param_prefix/v2/foo/tasks/bar",
        }
        for version, param_name in expected_params.items():
            with TestClient(app) as client:
                response = client.get(
                    f"/api/{version}/parameters/job_types/foo/tasks/bar"
                )
            response_content = response.json()
            self.assertEqual(response.status_code, 500)
            self.assertEqual(
                response_content["message"],
                f"Error retrieving parameter {param_name}",
            )
            mock_log_error.assert_called()

    @patch.dict(os.environ, EXAMPLE_ENV_VAR1, clear=True)
    def test_index(self):
        """Tests that form renders at startup as expected."""
        with TestClient(app) as client:
            response = client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Submit Jobs", response.text)

    @patch.dict(os.environ, EXAMPLE_ENV_VAR1, clear=True)
    def test_jobs(self):
        """Tests that job status page renders at startup as expected."""
        with TestClient(app) as client:
            response = client.get("/jobs")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Jobs Submitted:", response.text)

    @patch("requests.get")
    def test_tasks_table_success(self, mock_get: MagicMock):
        """Tests that job tasks table renders as expected."""
        mock_response = Response()
        mock_response.status_code = 200
        mock_response._content = json.dumps(
            self.list_task_instances_response
        ).encode("utf-8")
        mock_get.return_value = mock_response
        with TestClient(app) as client:
            response = client.get(
                "/job_tasks_table",
                params={"dag_id": "dag_id", "dag_run_id": "dag_run_id"},
            )
        self.assertEqual(response.status_code, 200)
        self.assertIn("Task ID", response.text)
        self.assertIn("Try Number", response.text)

    @patch.dict(os.environ, EXAMPLE_ENV_VAR1, clear=True)
    @patch("requests.get")
    def test_tasks_table_failure(self, mock_get: MagicMock):
        """Tests that job status table renders error message from airflow."""
        mock_response = Response()
        mock_response.status_code = 500
        mock_response._content = json.dumps(
            {"message": "test airflow error"}
        ).encode("utf-8")
        mock_get.return_value = mock_response
        with TestClient(app) as client:
            response = client.get(
                "/job_tasks_table",
                params={
                    "dag_id": "transform_and_upload",
                    "dag_run_id": "dag_run_id",
                },
            )
        self.assertEqual(response.status_code, 200)
        self.assertIn("Task ID", response.text)
        self.assertIn("Try Number", response.text)
        self.assertIn(
            "Error retrieving job tasks list from airflow", response.text
        )
        self.assertIn("test airflow error", response.text)

    @patch("requests.get")
    def test_logs_success(self, mock_get: MagicMock):
        """Tests that task logs page renders as expected."""
        mock_response = Response()
        mock_response.status_code = 200
        mock_response._content = b"mock log content"
        mock_get.return_value = mock_response
        with TestClient(app) as client:
            response = client.get(
                "/task_logs",
                params={
                    "dag_id": "transform_and_upload",
                    "dag_run_id": "dag_run_id",
                    "task_id": "task_id",
                    "try_number": 1,
                    "map_index": -1,
                },
            )
        self.assertEqual(response.status_code, 200)
        self.assertIn("mock log content", response.text)

    @patch.dict(os.environ, EXAMPLE_ENV_VAR1, clear=True)
    @patch("requests.get")
    def test_logs_failure(self, mock_get: MagicMock):
        """Tests that task logs page renders error message from airflow."""
        mock_response = Response()
        mock_response.status_code = 500
        mock_response._content = json.dumps(
            {"message": "test airflow error"}
        ).encode("utf-8")
        mock_get.return_value = mock_response
        with TestClient(app) as client:
            response = client.get(
                "/task_logs",
                params={
                    "dag_id": "transform_and_upload",
                    "dag_run_id": "dag_run_id",
                    "task_id": "task_id",
                    "try_number": 1,
                    "map_index": -1,
                },
            )
        self.assertEqual(response.status_code, 200)
        self.assertIn("Error retrieving task logs from airflow", response.text)
        self.assertIn("test airflow error", response.text)

    def test_download_job_template(self):
        """Tests that job template downloads as xlsx file."""

        with TestClient(app) as client:
            response = client.get("/api/job_upload_template")

        expected_file_stream = (
            JobUploadTemplate.create_excel_sheet_filestream()
        )
        expected_streaming_response = StreamingResponse(
            BytesIO(expected_file_stream.getvalue()),
            media_type=(
                "application/"
                "vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            ),
            headers={
                "Content-Disposition": (
                    f"attachment; filename={JobUploadTemplate.FILE_NAME}"
                )
            },
            status_code=200,
        )

        self.assertEqual(
            expected_streaming_response.headers.items(),
            list(response.headers.items()),
        )
        self.assertEqual(200, response.status_code)

    @patch.dict(os.environ, EXAMPLE_ENV_VAR1, clear=True)
    def test_job_params(self):
        """Tests that job params page renders at startup as expected."""
        with TestClient(app) as client:
            response = client.get("/job_params")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Job Parameters", response.text)

    @patch.dict(os.environ, EXAMPLE_ENV_VAR1, clear=True)
    @patch("fastapi.Request.session")
    def test_admin(self, mock_session: MagicMock):
        """Tests that the admin page renders when user is authenticated."""
        expected_user = {"name": "test_user", "email": "test_email"}
        mock_session.get.return_value = expected_user
        with TestClient(app) as client:
            response = client.get("/admin")
        mock_session.get.assert_called_once_with("user")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Admin", response.text)
        self.assertIn("test_user", response.text)

    @patch.dict(
        os.environ, {**EXAMPLE_ENV_VAR1, "ENV_NAME": "local"}, clear=True
    )
    def test_admin_local(self):
        """Tests that the admin page renders when user is authenticated."""
        with TestClient(app) as client:
            response = client.get("/admin")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Admin", response.text)
        self.assertIn("local user", response.text)

    @patch.dict(os.environ, EXAMPLE_ENV_VAR1, clear=True)
    @patch("fastapi.Request.session")
    @patch("aind_data_transfer_service.server.RedirectResponse")
    def test_admin_unauthenticated(
        self, mock_redirect_response: MagicMock, mock_session: MagicMock
    ):
        """Tests that the admin page redirects to login if user is not
        authenticated."""
        expected_user = None
        mock_session.get.return_value = expected_user
        mock_redirect_response.return_value = JSONResponse(
            content={
                "message": "Redirecting to login page",
                "data": None,
            },
            status_code=307,
        )
        with TestClient(app) as client:
            response = client.get("/admin")
        mock_redirect_response.assert_called_once_with(url="/login")
        self.assertEqual(response.status_code, 307)

    @patch("aind_data_transfer_service.server.JobUploadTemplate")
    @patch("logging.Logger.exception")
    def test_download_invalid_job_template(
        self, mock_log_error: MagicMock, mock_job_template: MagicMock
    ):
        """Tests that download invalid job template returns errors."""
        mock_job_template.create_excel_sheet_filestream.side_effect = (
            Exception("mock invalid job template")
        )
        with TestClient(app) as client:
            response = client.get("/api/job_upload_template")
        expected_response = {
            "message": "Error creating job template",
            "data": {"error": "Exception('mock invalid job template',)"},
        }
        self.assertEqual(500, response.status_code)
        self.assertEqual(expected_response, response.json())
        mock_log_error.assert_called_once()

    @patch.dict(os.environ, EXAMPLE_ENV_VAR1, clear=True)
    @patch("aind_data_transfer_service.server.get_airflow_jobs")
    @patch("aind_data_transfer_service.server.get_job_types")
    @patch("aind_data_transfer_service.server.get_project_names")
    def test_validate_v2_csv(
        self,
        mock_get_project_names: MagicMock,
        mock_get_job_types: MagicMock,
        mock_get_airflow_jobs: MagicMock,
    ):
        """Tests that valid csv file is returned."""
        mock_get_project_names.return_value = [
            "Ephys Platform",
            "Behavior Platform",
        ]
        mock_get_job_types.return_value = ["default", "ecephys", "custom"]
        mock_get_airflow_jobs.return_value = (0, list())
        with TestClient(app) as client:
            with open(NEW_SAMPLE_CSV, "rb") as f:
                files = {
                    "file": f,
                }
                response = client.post(url="/api/v2/validate_csv", files=files)

        expected_airflow_params = AirflowDagRunsRequestParameters(
            dag_ids=["transform_and_upload_v2", "run_list_of_jobs"],
            states=["running", "queued"],
        )
        mock_get_airflow_jobs.assert_called_once_with(
            params=expected_airflow_params, get_confs=True
        )
        self.assertEqual(200, response.status_code)

    @patch.dict(os.environ, EXAMPLE_ENV_VAR1, clear=True)
    @patch("aind_data_transfer_service.server.get_project_names")
    def test_validate_v2_null_csv(self, mock_get_project_names: MagicMock):
        """Tests that invalid file type returns FileNotFoundError"""
        mock_get_project_names.return_value = [
            "Ephys Platform",
            "Behavior Platform",
        ]
        with TestClient(app) as client:
            with open(SAMPLE_INVALID_EXT, "rb") as f:
                files = {
                    "file": f,
                }
                response = client.post(url="/api/v2/validate_csv", files=files)
        self.assertEqual(response.status_code, 406)
        self.assertEqual(
            ["Invalid input file type"],
            response.json()["data"]["errors"],
        )

    @patch.dict(os.environ, EXAMPLE_ENV_VAR1, clear=True)
    @patch("aind_data_transfer_service.server.get_airflow_jobs")
    @patch("aind_data_transfer_service.server.get_job_types")
    @patch("aind_data_transfer_service.server.get_project_names")
    def test_validate_v2_malformed_xlsx(
        self,
        mock_get_project_names: MagicMock,
        mock_get_job_types: MagicMock,
        mock_get_airflow_jobs: MagicMock,
    ):
        """Tests that invalid xlsx returns errors"""
        mock_get_project_names.return_value = [
            "Ephys Platform",
            "Behavior Platform",
        ]
        mock_get_job_types.return_value = ["default", "custom"]
        mock_get_airflow_jobs.return_value = (0, list())
        with TestClient(app) as client:
            with open(MALFORMED_SAMPLE_XLSX, "rb") as f:
                files = {
                    "file": f,
                }
                response = client.post(url="/api/v2/validate_csv", files=files)
        self.assertEqual(response.status_code, 406)
        self.assertEqual(3, len(response.json()["data"]["errors"]))

    @patch.dict(os.environ, EXAMPLE_ENV_VAR1, clear=True)
    @patch("aind_data_transfer_service.server.get_airflow_jobs")
    @patch("aind_data_transfer_service.server.get_job_types")
    @patch("aind_data_transfer_service.server.get_project_names")
    def test_validate_v2_csv_empty_rows(
        self,
        mock_get_project_names: MagicMock,
        mock_get_job_types: MagicMock,
        mock_get_airflow_jobs: MagicMock,
    ):
        """Tests that empty rows are ignored from valid csv and xlsx files."""
        mock_get_project_names.return_value = [
            "Ephys Platform",
            "Behavior Platform",
        ]
        mock_get_job_types.return_value = ["default", "ecephys", "custom"]
        mock_get_airflow_jobs.return_value = (0, list())
        with TestClient(app) as client:
            with open(SAMPLE_CSV_EMPTY_ROWS_2, "rb") as f:
                files = {
                    "file": f,
                }
                response = client.post(url="/api/v2/validate_csv", files=files)
        self.assertEqual(200, response.status_code)

    @patch.dict(os.environ, EXAMPLE_ENV_VAR1, clear=True)
    @patch("aind_data_transfer_service.server.get_airflow_jobs")
    @patch("aind_data_transfer_service.server.get_job_types")
    @patch("aind_data_transfer_service.server.get_project_names")
    def test_validate_v2_malformed_csv2(
        self,
        mock_get_project_names: MagicMock,
        mock_get_job_types: MagicMock,
        mock_get_airflow_jobs: MagicMock,
    ):
        """Tests that invalid csv returns errors"""
        mock_get_project_names.return_value = ["Ephys Platform"]
        mock_get_job_types.return_value = ["default"]
        mock_get_airflow_jobs.return_value = (0, list())
        with TestClient(app) as client:
            with open(MALFORMED_SAMPLE_CSV_2, "rb") as f:
                files = {
                    "file": f,
                }
                response = client.post(url="/api/v2/validate_csv", files=files)
        self.assertEqual(response.status_code, 406)

    @patch.dict(os.environ, EXAMPLE_ENV_VAR1, clear=True)
    @patch("logging.Logger.warning")
    @patch("requests.post")
    @patch("aind_data_transfer_service.server.get_airflow_jobs")
    @patch("aind_data_transfer_service.server.get_project_names")
    @patch("aind_data_transfer_service.server.get_job_types")
    def test_submit_v1_v2_jobs_406(
        self,
        mock_get_job_types: MagicMock,
        mock_get_project_names: MagicMock,
        mock_get_airflow_jobs: MagicMock,
        mock_post: MagicMock,
        mock_log_warning: MagicMock,
    ):
        """Tests submit jobs 406 response."""
        mock_get_job_types.return_value = ["ecephys"]
        mock_get_project_names.return_value = ["Ephys Platform"]
        mock_get_airflow_jobs.return_value = (0, list())
        for version in ["v1", "v2"]:
            with TestClient(app) as client:
                submit_job_response = client.post(
                    url=f"/api/{version}/submit_jobs", json={}
                )
            self.assertEqual(406, submit_job_response.status_code)
            mock_post.assert_not_called()
            mock_log_warning.assert_called_with(
                "There were validation errors processing {}"
            )
        mock_get_job_types.assert_called_once_with("v2")
        mock_get_airflow_jobs.assert_called_once()
        self.assertEqual(2, mock_get_project_names.call_count)

    @patch.dict(os.environ, EXAMPLE_ENV_VAR1, clear=True)
    @patch("requests.post")
    @patch("aind_data_transfer_service.server.get_airflow_jobs")
    @patch("aind_data_transfer_service.server.get_project_names")
    @patch("aind_data_transfer_service.server.get_job_types")
    def test_submit_v1_v2_jobs_200(
        self,
        mock_get_job_types: MagicMock,
        mock_get_project_names: MagicMock,
        mock_get_airflow_jobs: MagicMock,
        mock_post: MagicMock,
    ):
        """Tests submit jobs success."""
        mock_get_project_names.return_value = ["Ephys Platform"]
        mock_get_job_types.return_value = ["ecephys"]
        mock_get_airflow_jobs.return_value = (0, list())
        mock_response = Response()
        mock_response.status_code = 200
        mock_response._content = json.dumps({"message": "sent"}).encode(
            "utf-8"
        )
        mock_post.return_value = mock_response
        request_json_v1 = {
            "user_email": None,
            "email_notification_types": ["fail"],
            "upload_jobs": [
                {
                    "project_name": "Ephys Platform",
                    "process_capsule_id": None,
                    "s3_bucket": "private",
                    "platform": {
                        "name": "Electrophysiology platform",
                        "abbreviation": "ecephys",
                    },
                    "modalities": [
                        {
                            "modality": {
                                "name": "Extracellular electrophysiology",
                                "abbreviation": "ecephys",
                            },
                            "source": "dir/source1",
                            "compress_raw_data": True,
                            "extra_configs": None,
                            "slurm_settings": None,
                        },
                    ],
                    "subject_id": "655019",
                    "acq_datetime": "2000-01-01T01:40:04",
                    "metadata_dir": None,
                    "metadata_dir_force": False,
                    "force_cloud_sync": False,
                },
            ],
        }
        job_request_v2 = SubmitJobRequestV2(
            upload_jobs=[self.example_configs_v2]
        )
        request_json_v2 = job_request_v2.model_dump(mode="json")
        jobs = {
            "v1": request_json_v1,
            "v2": request_json_v2,
        }
        for version, request_json in jobs.items():
            with TestClient(app) as client:
                submit_job_response = client.post(
                    url=f"/api/{version}/submit_jobs", json=request_json
                )
            self.assertEqual(200, submit_job_response.status_code)
        mock_get_job_types.assert_called_once_with("v2")
        expected_airflow_params = AirflowDagRunsRequestParameters(
            dag_ids=["transform_and_upload_v2", "run_list_of_jobs"],
            states=["running", "queued"],
        )
        mock_get_airflow_jobs.assert_called_once_with(
            params=expected_airflow_params, get_confs=True
        )
        self.assertEqual(2, mock_get_project_names.call_count)

    @patch.dict(os.environ, EXAMPLE_ENV_VAR1, clear=True)
    @patch("requests.post")
    @patch("logging.Logger.exception")
    @patch("aind_data_transfer_service.server.get_airflow_jobs")
    @patch("aind_data_transfer_service.server.get_project_names")
    @patch("aind_data_transfer_service.server.get_job_types")
    def test_submit_v1_v2_jobs_500(
        self,
        mock_get_job_types: MagicMock,
        mock_get_project_names: MagicMock,
        mock_get_airflow_jobs: MagicMock,
        mock_log_exception: MagicMock,
        mock_post: MagicMock,
    ):
        """Tests submit jobs 500 response."""
        mock_get_job_types.return_value = ["ecephys"]
        mock_get_project_names.return_value = ["Ephys Platform"]
        mock_get_airflow_jobs.return_value = (0, list())
        mock_post.side_effect = Exception("Something went wrong")
        request_json_v1 = {
            "user_email": None,
            "email_notification_types": ["fail"],
            "upload_jobs": [
                {
                    "project_name": "Ephys Platform",
                    "process_capsule_id": None,
                    "s3_bucket": "private",
                    "platform": {
                        "name": "Electrophysiology platform",
                        "abbreviation": "ecephys",
                    },
                    "modalities": [
                        {
                            "modality": {
                                "name": "Extracellular electrophysiology",
                                "abbreviation": "ecephys",
                            },
                            "source": "dir/source1",
                            "compress_raw_data": True,
                            "extra_configs": None,
                            "slurm_settings": None,
                        },
                    ],
                    "subject_id": "655019",
                    "acq_datetime": "2000-01-01T01:40:04",
                    "metadata_dir": None,
                    "metadata_dir_force": False,
                    "force_cloud_sync": False,
                },
            ],
        }
        request_json_v2 = {
            "user_email": None,
            "email_notification_types": ["fail"],
            "upload_jobs": [
                {
                    "job_type": "ecephys",
                    "project_name": "Ephys Platform",
                    "platform": {
                        "name": "Electrophysiology platform",
                        "abbreviation": "ecephys",
                    },
                    "modalities": [
                        {
                            "name": "Extracellular electrophysiology",
                            "abbreviation": "ecephys",
                        }
                    ],
                    "subject_id": "655019",
                    "acq_datetime": "2000-01-01T01:40:04",
                    "tasks": {
                        "make_modality_list": {
                            "dynamic_parameters_settings": {
                                "modality": "ecephys",
                                "source": "dir/source1",
                            },
                        }
                    },
                },
            ],
        }
        jobs = {
            "v1": request_json_v1,
            "v2": request_json_v2,
        }
        for version, request_json in jobs.items():
            with TestClient(app) as client:
                submit_job_response = client.post(
                    url=f"/api/{version}/submit_jobs", json=request_json
                )
            self.assertEqual(500, submit_job_response.status_code)
            mock_log_exception.assert_called()
        mock_get_job_types.assert_called_once_with("v2")
        mock_get_airflow_jobs.assert_called_once()
        self.assertEqual(2, mock_get_project_names.call_count)

    @patch.dict(os.environ, EXAMPLE_ENV_VAR1, clear=True)
    @patch("requests.post")
    @patch("aind_data_transfer_service.server.get_project_names")
    def test_submit_v1_jobs_200_slurm_settings(
        self,
        mock_get_project_names: MagicMock,
        mock_post: MagicMock,
    ):
        """Tests submit jobs success when user adds custom slurm settings."""
        mock_get_project_names.return_value = ["Ephys Platform"]
        mock_response = Response()
        mock_response.status_code = 200
        mock_response._content = json.dumps({"message": "sent"}).encode(
            "utf-8"
        )
        mock_post.return_value = mock_response
        ephys_source_dir = PurePosixPath("shared_drive/ephys_data/690165")

        s3_bucket = "private"
        subject_id = "690165"
        acq_datetime = datetime(2024, 2, 19, 11, 25, 17)
        platform = Platform.ECEPHYS

        slurm_settings = V0036JobProperties(
            environment=dict(),
            time_limit=720,
            minimum_cpus_per_node=16,
        )

        ephys_config = ModalityConfigs(
            modality=Modality.ECEPHYS,
            source=ephys_source_dir,
            slurm_settings=slurm_settings,
        )
        project_name = "Ephys Platform"

        upload_job_configs = BasicUploadJobConfigs(
            project_name=project_name,
            s3_bucket=s3_bucket,
            platform=platform,
            subject_id=subject_id,
            acq_datetime=acq_datetime,
            modalities=[ephys_config],
        )

        upload_jobs = [upload_job_configs]
        submit_request = SubmitJobRequest(upload_jobs=upload_jobs)

        post_request_content = json.loads(
            submit_request.model_dump_json(round_trip=True)
        )

        with TestClient(app) as client:
            submit_job_response = client.post(
                url="/api/v1/submit_jobs", json=post_request_content
            )
        self.assertEqual(200, submit_job_response.status_code)

    @patch.dict(os.environ, EXAMPLE_ENV_VAR1, clear=True)
    @patch("requests.post")
    @patch("aind_data_transfer_service.server.get_project_names")
    def test_submit_v1_jobs_200_session_settings_config_file(
        self,
        mock_get_project_names: MagicMock,
        mock_post: MagicMock,
    ):
        """Tests submit jobs success when user adds aind-metadata-mapper
        settings pointing to a config file."""

        mock_get_project_names.return_value = ["Ephys Platform"]
        session_settings = {
            "session_settings": {
                "job_settings": {
                    "user_settings_config_file": "test_bergamo_settings.json",
                    "job_settings_name": "Bergamo",
                }
            }
        }

        mock_response = Response()
        mock_response.status_code = 200
        mock_response._content = json.dumps({"message": "sent"}).encode(
            "utf-8"
        )
        mock_post.return_value = mock_response
        ephys_source_dir = PurePosixPath("shared_drive/ephys_data/690165")

        s3_bucket = "private"
        subject_id = "690165"
        acq_datetime = datetime(2024, 2, 19, 11, 25, 17)
        platform = Platform.ECEPHYS

        ephys_config = ModalityConfigs(
            modality=Modality.ECEPHYS,
            source=ephys_source_dir,
        )
        project_name = "Ephys Platform"

        upload_job_configs = BasicUploadJobConfigs(
            project_name=project_name,
            s3_bucket=s3_bucket,
            platform=platform,
            subject_id=subject_id,
            acq_datetime=acq_datetime,
            modalities=[ephys_config],
            metadata_configs=session_settings,
        )

        upload_jobs = [upload_job_configs]
        # Suppress serializer warning when using a dict instead of an object
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            submit_request = SubmitJobRequest(upload_jobs=upload_jobs)

            post_request_content = json.loads(
                submit_request.model_dump_json(
                    round_trip=True, warnings=False, exclude_none=True
                )
            )

            with TestClient(app) as client:
                submit_job_response = client.post(
                    url="/api/v1/submit_jobs", json=post_request_content
                )
            self.assertEqual(200, submit_job_response.status_code)

    @patch.dict(os.environ, EXAMPLE_ENV_VAR1, clear=True)
    @patch("requests.post")
    @patch("aind_data_transfer_service.server.get_project_names")
    def test_submit_v1_jobs_200_trigger_capsule_configs(
        self,
        mock_get_project_names: MagicMock,
        mock_post: MagicMock,
    ):
        """Tests submission when user adds trigger_capsule_configs"""

        mock_get_project_names.return_value = ["Ephys Platform"]

        mock_response = Response()
        mock_response.status_code = 200
        mock_response._content = json.dumps({"message": "sent"}).encode(
            "utf-8"
        )
        mock_post.return_value = mock_response
        ephys_source_dir = PurePosixPath("shared_drive/ephys_data/690165")

        s3_bucket = "private"
        subject_id = "690165"
        acq_datetime = datetime(2024, 2, 19, 11, 25, 17)
        platform = Platform.ECEPHYS

        trigger_capsule_settings = TriggerConfigModel(
            job_type=ValidJobType.RUN_GENERIC_PIPELINE, capsule_id="abc-123"
        )
        ephys_config = ModalityConfigs(
            modality=Modality.ECEPHYS,
            source=ephys_source_dir,
        )
        project_name = "Ephys Platform"

        upload_job_configs = BasicUploadJobConfigs(
            project_name=project_name,
            s3_bucket=s3_bucket,
            platform=platform,
            subject_id=subject_id,
            acq_datetime=acq_datetime,
            modalities=[ephys_config],
            trigger_capsule_configs=trigger_capsule_settings,
        )

        upload_jobs = [upload_job_configs]
        submit_request = SubmitJobRequest(upload_jobs=upload_jobs)

        post_request_content = json.loads(
            submit_request.model_dump_json(round_trip=True)
        )

        with TestClient(app) as client:
            submit_job_response = client.post(
                url="/api/v1/submit_jobs", json=post_request_content
            )
        self.assertEqual(200, submit_job_response.status_code)

    @patch.dict(os.environ, EXAMPLE_ENV_VAR1, clear=True)
    @patch("requests.post")
    @patch("aind_data_transfer_service.server.get_airflow_jobs")
    @patch("aind_data_transfer_service.server.get_project_names")
    @patch("aind_data_transfer_service.server.get_job_types")
    def test_submit_v2_jobs_200_basic_serialization(
        self,
        mock_get_job_types: MagicMock,
        mock_get_project_names: MagicMock,
        mock_get_airflow_jobs: MagicMock,
        mock_post: MagicMock,
    ):
        """Tests submission when user posts standard pydantic json"""

        mock_get_project_names.return_value = ["Ephys Platform"]
        mock_get_job_types.return_value = ["ecephys"]
        mock_get_airflow_jobs.return_value = (0, list())

        mock_response = Response()
        mock_response.status_code = 200
        mock_response._content = json.dumps({"message": "sent"}).encode(
            "utf-8"
        )
        mock_post.return_value = mock_response
        ephys_source_dir = PurePosixPath("shared_drive/ephys_data/690165")

        s3_bucket = "private"
        subject_id = "690165"
        acq_datetime = datetime(2024, 2, 19, 11, 25, 17)
        platform = Platform.ECEPHYS

        ephys_config = ModalityConfigs(
            modality=Modality.ECEPHYS,
            source=ephys_source_dir,
        )
        project_name = "Ephys Platform"

        upload_job_configs = BasicUploadJobConfigs(
            project_name=project_name,
            s3_bucket=s3_bucket,
            platform=platform,
            subject_id=subject_id,
            acq_datetime=acq_datetime,
            modalities=[ephys_config],
        )

        upload_jobs = [upload_job_configs]
        submit_request = SubmitJobRequest(upload_jobs=upload_jobs)

        post_request_content_v1 = json.loads(submit_request.model_dump_json())
        job_request_v2 = SubmitJobRequestV2(
            upload_jobs=[self.example_configs_v2]
        )
        post_request_content_v2 = job_request_v2.model_dump(mode="json")
        jobs = {
            "v1": post_request_content_v1,
            "v2": post_request_content_v2,
        }

        for version, request_json in jobs.items():
            with TestClient(app) as client:
                submit_job_response = client.post(
                    url=f"/api/{version}/submit_jobs", json=request_json
                )
            self.assertEqual(200, submit_job_response.status_code)
        mock_get_job_types.assert_called_once_with("v2")
        mock_get_airflow_jobs.assert_called_once()
        self.assertEqual(2, mock_get_project_names.call_count)

    @patch("aind_data_transfer_service.server.get_airflow_jobs")
    @patch("aind_data_transfer_service.server.get_job_types")
    @patch("aind_data_transfer_service.server.get_project_names")
    def test_validate_json(
        self,
        mock_get_project_names: MagicMock,
        mock_get_job_types: MagicMock,
        mock_get_airflow_jobs: MagicMock,
    ):
        """Tests validate_json when json is valid."""

        mock_get_project_names.return_value = ["Ephys Platform"]
        mock_get_job_types.return_value = ["ecephys"]
        mock_get_airflow_jobs.return_value = (0, list())

        # v1
        ephys_source_dir = PurePosixPath("shared_drive/ephys_data/690165")
        s3_bucket = "private"
        subject_id = "690165"
        acq_datetime = datetime(2024, 2, 19, 11, 25, 17)
        platform = Platform.ECEPHYS
        project_name = "Ephys Platform"
        ephys_config = ModalityConfigs(
            modality=Modality.ECEPHYS,
            source=ephys_source_dir,
        )
        upload_job = BasicUploadJobConfigs(
            project_name=project_name,
            s3_bucket=s3_bucket,
            platform=platform,
            subject_id=subject_id,
            acq_datetime=acq_datetime,
            modalities=[ephys_config],
        )
        submit_job_request_v1 = SubmitJobRequest(upload_jobs=[upload_job])
        # v2
        upload_job = self.example_configs_v2
        submit_job_request_v2 = SubmitJobRequestV2(upload_jobs=[upload_job])

        expected_jobs = {
            "v1": {
                "request": submit_job_request_v1,
                "version": aind_data_transfer_models_version,
            },
            "v2": {
                "request": submit_job_request_v2,
                "version": aind_data_transfer_service_version,
            },
        }
        for version, job in expected_jobs.items():
            post_request_content = json.loads(job["request"].model_dump_json())
            with TestClient(app) as client:
                response = client.post(
                    f"/api/{version}/validate_json",
                    json=post_request_content,
                )
                response_json = response.json()
            self.assertEqual(200, response.status_code)
            self.assertEqual("Valid model", response_json["message"])
            self.assertEqual(
                post_request_content, response_json["data"]["model_json"]
            )
            self.assertEqual(job["version"], response_json["data"]["version"])
        expected_airflow_params = AirflowDagRunsRequestParameters(
            dag_ids=["transform_and_upload_v2", "run_list_of_jobs"],
            states=["running", "queued"],
        )
        mock_get_airflow_jobs.assert_called_once_with(
            params=expected_airflow_params, get_confs=True
        )
        mock_get_job_types.assert_called_once_with("v2")
        self.assertEqual(2, mock_get_project_names.call_count)

    @patch("logging.Logger.warning")
    @patch("aind_data_transfer_service.server.get_airflow_jobs")
    @patch("aind_data_transfer_service.server.get_project_names")
    @patch("aind_data_transfer_service.server.get_job_types")
    def test_validate_json_invalid(
        self,
        mock_get_job_types: MagicMock,
        mock_get_project_names: MagicMock,
        mock_get_airflow_jobs: MagicMock,
        mock_log_warning: MagicMock,
    ):
        """Tests validate_json when json is invalid."""
        mock_get_job_types.return_value = ["ecephys"]
        mock_get_project_names.return_value = ["Ephys Platform"]
        mock_get_airflow_jobs.return_value = (0, list())
        content = {"foo": "bar"}
        versions = {
            "v1": aind_data_transfer_models_version,
            "v2": aind_data_transfer_service_version,
        }
        for version, response_version in versions.items():
            with TestClient(app) as client:
                response = client.post(
                    f"/api/{version}/validate_json", json=content
                )
            response_json = response.json()
            self.assertEqual(406, response.status_code)
            self.assertEqual(
                "There were validation errors", response_json["message"]
            )
            self.assertEqual(content, response_json["data"]["model_json"])
            self.assertEqual(
                response_version, response_json["data"]["version"]
            )
            mock_log_warning.assert_called_with(
                f"There were validation errors processing {content}"
            )
        mock_get_airflow_jobs.assert_called_once()
        mock_get_job_types.assert_called_once_with("v2")
        self.assertEqual(2, mock_get_project_names.call_count)

    @patch.dict(os.environ, EXAMPLE_ENV_VAR1, clear=True)
    @patch("logging.Logger.warning")
    @patch("httpx.AsyncClient.post")
    @patch("aind_data_transfer_service.server.get_project_names")
    @patch("aind_data_transfer_service.server.get_job_types")
    def test_validate_json_v2_invalid_current(
        self,
        mock_get_job_types: MagicMock,
        mock_get_project_names: MagicMock,
        mock_post: MagicMock,
        mock_log_warning: MagicMock,
    ):
        """Tests validate_json_v2 when there is a duplicate job running."""

        mock_get_project_names.return_value = ["Ephys Platform"]
        mock_get_job_types.return_value = ["ecephys"]
        # assume a job is already running
        job_request = SubmitJobRequestV2(
            upload_jobs=[self.example_configs_v2]
        ).model_dump(mode="json", exclude_none=True)
        current_job = job_request["upload_jobs"][0]
        airflow_response = {
            "dag_runs": [{**self.get_dag_run_response, "conf": current_job}],
            "total_entries": 1,
        }
        mock_dag_runs_response = Response()
        mock_dag_runs_response.status_code = 200
        mock_dag_runs_response._content = json.dumps(airflow_response).encode(
            "utf-8"
        )
        mock_post.return_value = mock_dag_runs_response
        # now submit same job again
        with TestClient(app) as client:
            resp = client.post("/api/v2/validate_json", json=job_request)
            resp_json = resp.json()
        self.assertEqual(406, resp.status_code)
        self.assertEqual("There were validation errors", resp_json["message"])
        self.assertIn(
            "Job is already running/queued for "
            "ecephys_690165_2024-02-19_11-25-17",
            resp_json["data"]["errors"],
        )
        mock_log_warning.assert_called_once_with(
            f"There were validation errors processing {job_request}"
        )

    @patch("logging.Logger.exception")
    @patch("pydantic.BaseModel.model_validate_json")
    @patch("aind_data_transfer_service.server.get_airflow_jobs")
    @patch("aind_data_transfer_service.server.get_project_names")
    @patch("aind_data_transfer_service.server.get_job_types")
    def test_validate_json_error(
        self,
        mock_get_job_types: MagicMock,
        mock_get_project_names: MagicMock,
        mock_get_airflow_jobs: MagicMock,
        mock_model_validate_json: MagicMock,
        mock_log_error: MagicMock,
    ):
        """Tests validate_json when there is an unknown error."""

        mock_get_job_types.return_value = ["ecephys"]
        mock_get_project_names.return_value = ["Ephys Platform"]
        mock_get_airflow_jobs.return_value = (0, list())
        mock_model_validate_json.side_effect = Exception("Unknown error")
        versions = {
            "v1": aind_data_transfer_models_version,
            "v2": aind_data_transfer_service_version,
        }
        for version, response_version in versions.items():
            with TestClient(app) as client:
                response = client.post(
                    f"/api/{version}/validate_json",
                    json={"foo": "bar"},
                )
            response_json = response.json()
            self.assertEqual(500, response.status_code)
            self.assertEqual(
                "There was an internal server error", response_json["message"]
            )
            self.assertEqual(
                {"foo": "bar"}, response_json["data"]["model_json"]
            )
            self.assertEqual(
                "('Unknown error',)", response_json["data"]["errors"]
            )
            self.assertEqual(
                response_version, response_json["data"]["version"]
            )
            mock_model_validate_json.assert_called()
            mock_log_error.assert_called_with("Internal Server Error.")
        mock_get_airflow_jobs.assert_called_once()
        mock_get_job_types.assert_called_once_with("v2")
        self.assertEqual(2, mock_get_project_names.call_count)

    @patch.dict(os.environ, EXAMPLE_ENV_VAR1, clear=True)
    @patch("boto3.client")
    @patch("aind_data_transfer_service.server.OAuth")
    def test_login(
        self, mock_set_oauth: MagicMock, mock_secrets_client: MagicMock
    ):
        """Tests the login function."""
        mock_set_oauth.return_value.azure.authorize_redirect = AsyncMock(
            return_value=JSONResponse(
                content={
                    "message": "mock_redirect_url",
                },
                status_code=200,
            )
        )
        mock_secrets_client.return_value.get_secret_value.return_value = (
            self.get_secrets_response
        )
        with TestClient(app) as client:
            response = client.get("/login")
        mock_secrets_client.assert_called_with("secretsmanager")
        mock_secrets_client.return_value.get_secret_value.assert_called_with(
            SecretId="/secret/name"
        )
        mock_set_oauth.return_value.register.assert_called_with(
            name="azure",
            client_id="client_id",
            client_secret="client_secret",
            server_metadata_url="https://authority",
            client_kwargs={"scope": "openid email profile"},
        )
        mock_oauth = mock_set_oauth.return_value
        mock_azure = mock_oauth.azure
        mock_azure.authorize_redirect.assert_called_once()
        self.assertEqual(response.status_code, 200)

    @patch.dict(os.environ, EXAMPLE_ENV_VAR1, clear=True)
    @patch("aind_data_transfer_service.server.RedirectResponse")
    @patch("fastapi.Request.session")
    def test_logout(self, mock_session: MagicMock, mock_redirect: MagicMock):
        """Tests logout clears user from session and redirects to index."""
        expected_user = {"name": "test_user", "email": "test_email"}
        mock_session.get.return_value = expected_user
        mock_redirect.return_value = JSONResponse(
            content={"message": "Redirecting to index"},
            status_code=307,
        )
        with TestClient(app) as client:
            response = client.get("/logout")
        mock_redirect.assert_called_once_with(url="/")
        self.assertEqual(response.status_code, 307)

    @patch.dict(os.environ, EXAMPLE_ENV_VAR1, clear=True)
    @patch("boto3.client")
    @patch("aind_data_transfer_service.server.OAuth")
    def test_auth(
        self, mock_set_oauth: MagicMock, mock_secrets_client: MagicMock
    ):
        """Tests the auth callback function."""
        mock_set_oauth.return_value.azure.authorize_access_token = AsyncMock(
            return_value={"userinfo": {"some_user": "info"}}
        )
        mock_secrets_client.return_value.get_secret_value.return_value = (
            self.get_secrets_response
        )
        with TestClient(app) as client:
            response = client.get("/auth")
        mock_oauth = mock_set_oauth.return_value
        mock_azure = mock_oauth.azure
        mock_azure.authorize_access_token.assert_called_once()
        self.assertEqual(response.status_code, 200)

    @patch.dict(os.environ, EXAMPLE_ENV_VAR1, clear=True)
    @patch("boto3.client")
    @patch("aind_data_transfer_service.server.OAuth")
    def test_auth_error(
        self, mock_set_oauth: MagicMock, mock_secrets_client: MagicMock
    ):
        """Tests an error in the auth callback function."""
        mock_set_oauth.return_value.azure.authorize_access_token = AsyncMock(
            side_effect=OAuthError("Error Logging In")
        )
        mock_secrets_client.return_value.get_secret_value.return_value = (
            self.get_secrets_response
        )
        with TestClient(app) as client:
            response = client.get("/auth")
        expected_response = {
            "message": "Error Logging In",
            "data": {"error": "OAuthError('Error Logging In: ',)"},
        }
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json(), expected_response)

    @patch.dict(os.environ, EXAMPLE_ENV_VAR1, clear=True)
    @patch("boto3.client")
    @patch("aind_data_transfer_service.server.OAuth")
    def test_auth_error_userinfo(
        self, mock_set_oauth: MagicMock, mock_secrets_client: MagicMock
    ):
        """Tests the auth callback function when userinfo is not provided."""
        mock_set_oauth.return_value.azure.authorize_access_token = AsyncMock(
            return_value={"invalid": {"some_user": "info"}}
        )
        mock_secrets_client.return_value.get_secret_value.return_value = (
            self.get_secrets_response
        )
        with TestClient(app) as client:
            response = client.get("/auth")
        expected_response = {
            "message": "Error Logging In",
            "data": {
                "error": "ValueError('User info not found in access token.',)"
            },
        }
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json(), expected_response)


if __name__ == "__main__":
    unittest.main()
