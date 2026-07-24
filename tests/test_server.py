"""Tests server module."""

import json
import os
from datetime import datetime, timedelta, timezone
from io import BytesIO
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from authlib.integrations.starlette_client import OAuthError
from botocore.exceptions import ClientError
from fastapi.responses import JSONResponse, StreamingResponse
from requests import Response

from aind_data_transfer_service import (
    __version__ as aind_data_transfer_service_version,
)
from aind_data_transfer_service.configs.job_upload_template import (
    JobUploadTemplate,
)
from aind_data_transfer_service.models.core import (
    SubmitJobRequestV2,
)
from aind_data_transfer_service.models.internal import (
    JobParamInfo,
)
from aind_data_transfer_service.server import (
    get_job_types,
    get_project_names,
)

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
NEW_SAMPLE_CSV = TEST_DIRECTORY / "resources" / "new_sample.csv"
MALFORMED_SAMPLE_CSV_2 = (
    TEST_DIRECTORY / "resources" / "sample_malformed_2.csv"
)
SAMPLE_CSV_EMPTY_ROWS_2 = (
    TEST_DIRECTORY / "resources" / "sample_empty_rows_2.csv"
)


@pytest.mark.asyncio
class TestServer:
    """Tests main server."""

    @patch("httpx.AsyncClient.get")
    async def test_get_project_names(self, mock_get: MagicMock):
        """Tests get_project_names method"""
        mock_response = Response()
        mock_response.status_code = 200
        mock_response._content = json.dumps(
            {"data": ["project_name_0", "project_name_1"]}
        ).encode("utf-8")
        mock_get.return_value = mock_response
        project_names = await get_project_names()
        assert ["project_name_0", "project_name_1"] == project_names

    @patch("aind_data_transfer_service.server.get_parameter_infos")
    async def test_get_job_types(self, mock_get_parameter_infos: MagicMock):
        """Tests get_job_types method"""
        tasks = [
            ("job1", "task1", None),
            ("job1", "task2", None),
            ("job2", "modality_transformation_settings", "ecephys"),
        ]
        mock_get_parameter_infos.return_value = [
            JobParamInfo(
                name=f"/param_prefix/v2/{t[0]}/tasks/{t[1]}",
                job_type=t[0],
                task_id=t[1],
                modality=t[2],
                last_modified=None,
                version="v2",
            )
            for t in tasks
        ]
        job_types = get_job_types("v2")
        mock_get_parameter_infos.assert_called_once_with("v2")
        assert {"job1", "job2"} == set(job_types)

    @patch("httpx.AsyncClient.post")
    async def test_get_job_status_list_default(
        self, mock_post, client, list_dag_runs_response, caplog
    ):
        """Tests get_job_status_list gets paginated dagRuns from airflow using
        default limit and offset."""
        mock_dag_runs_response = Response()
        mock_dag_runs_response.status_code = 200
        mock_dag_runs_response._content = json.dumps(
            list_dag_runs_response
        ).encode("utf-8")
        mock_post.return_value = mock_dag_runs_response
        expected_message = "Retrieved job status list from airflow"
        expected_default_params = {
            "dag_ids": ["transform_and_upload", "transform_and_upload_v2"],
            "page_limit": 250,
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
        response = client.get("/api/v1/get_job_status_list")
        response_content = response.json()
        # small hack to mock the date
        response_content["data"]["params"][
            "execution_date_gte"
        ] = "mock_execution_date_gte"
        assert response.status_code == 200
        assert response_content == {
            "message": expected_message,
            "data": {
                "params": expected_default_params,
                "total_entries": list_dag_runs_response["total_entries"],
                "job_status_list": expected_job_status_list,
            },
        }
        mock_post.assert_called_once()
        assert (
            mock_post.call_args_list[0][0][0]
            == "airflow_jobs_url/~/dagRuns/list"
        )
        posted_body = mock_post.call_args_list[0].kwargs["json"]
        assert "execution_date_lte" not in posted_body
        assert all(v is not None for v in posted_body.values())
        assert 1 == len(caplog.messages)

    @patch("httpx.AsyncClient.post")
    async def test_get_job_status_list_query_params(
        self, mock_post, client, list_dag_runs_response, caplog
    ):
        """Tests get_job_status_list gets paginated dagRuns from airflow using
        query_params."""
        mock_dag_runs_response = Response()
        mock_dag_runs_response.status_code = 200
        mock_dag_runs_response._content = json.dumps(
            list_dag_runs_response
        ).encode("utf-8")
        mock_post.return_value = mock_dag_runs_response
        expected_message = "Retrieved job status list from airflow"
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
        assert 1 == len(caplog.messages)
        assert response.status_code == 200
        assert response_content["message"] == expected_message
        assert response_content["data"]["params"]["page_limit"] == 10
        assert response_content["data"]["params"]["page_offset"] == 5
        mock_post.assert_called_once()
        assert (
            mock_post.call_args_list[0][0][0]
            == "airflow_jobs_url/~/dagRuns/list"
        )

    @patch("httpx.AsyncClient.post")
    async def test_get_job_status_list_validation_error(
        self, mock_post, client, caplog
    ):
        """Tests get_job_status_list when query_params are invalid."""
        invalid_queries = [
            {"page_limit": "invalid", "page_offset": 5},
            {"page_limit": 5, "page_offset": "invalid"},
            {
                "execution_date_gte": (
                    datetime.now(timezone.utc)
                    - timedelta(weeks=2)
                    - timedelta(minutes=30)
                ).strftime("%Y-%m-%dT%H:%M:%SZ")
            },
        ]

        for query in invalid_queries:
            response = client.get("/api/v1/get_job_status_list", params=query)
            response_content = response.json()
            assert response.status_code == 406
            assert (
                response_content["message"]
                == "Error validating request parameters"
            )
        assert 3 == len(caplog.messages)
        mock_post.assert_not_called()

    @patch("httpx.AsyncClient.post")
    async def test_get_job_status_list_get_all_jobs(
        self, mock_post, client, get_dag_run_response, caplog
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
                    "dag_runs": [get_dag_run_response for _ in range(limit)],
                }
            ).encode("utf-8")
            return mock_dag_runs_response

        mock_post.side_effect = mock_airflow_dags
        expected_message = "Retrieved job status list from airflow"

        response = client.get("/api/v1/get_job_status_list")
        response_content = response.json()
        assert 1 == len(caplog.messages)
        assert response.status_code == 200
        assert response_content["message"] == expected_message
        assert response_content["data"]["total_entries"] == 300
        assert len(response_content["data"]["job_status_list"]) == 500

    @patch("httpx.AsyncClient.post")
    async def test_get_job_status_list_error(
        self, mock_post: MagicMock, client, caplog
    ):
        """Tests get_job_status_list when there is an error sending request."""
        mock_post.side_effect = Exception("mock error")
        response = client.get("/api/v1/get_job_status_list")
        response_content = response.json()
        assert response.status_code == 500
        assert (
            response_content["message"]
            == "Unable to retrieve job status list from airflow"
        )
        assert 2 == len(caplog.messages)
        mock_post.assert_called_once()
        assert (
            mock_post.call_args_list[0][0][0]
            == "airflow_jobs_url/~/dagRuns/list"
        )

    @patch("httpx.AsyncClient.get")
    async def test_get_tasks_list_query_params(
        self, mock_get, client, list_task_instances_response, caplog
    ):
        """Tests get_tasks_list gets tasks from airflow using query_params."""
        mock_task_instances_response = Response()
        mock_task_instances_response.status_code = 200
        mock_task_instances_response._content = json.dumps(
            list_task_instances_response
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
        expected_task_list = sorted(
            expected_task_list,
            key=lambda t: (t["priority_weight"], t["map_index"]),
        )

        response = client.get(
            "/api/v1/get_tasks_list",
            params={
                "dag_id": "transform_and_upload",
                "dag_run_id": "mock_dag_run_id",
            },
        )
        response_content = response.json()
        assert 0 == len(caplog.messages)
        assert response.status_code == 200
        assert response_content == {
            "message": expected_message,
            "data": {
                "params": expected_params,
                "total_entries": list_task_instances_response["total_entries"],
                "job_tasks_list": expected_task_list,
            },
        }

    @patch("httpx.AsyncClient.get")
    async def test_get_tasks_list_validation_error(
        self, mock_get, client, caplog
    ):
        """Tests get_tasks_list when query_params are invalid."""
        invalid_params = {
            "job_id": "mock_dag_run_id",
        }

        response = client.get("/api/v1/get_tasks_list", params=invalid_params)
        response_content = response.json()
        assert 1 == len(caplog.messages)
        assert response.status_code == 406
        assert (
            response_content["message"]
            == "Error validating request parameters"
        )
        mock_get.assert_not_called()

    @patch("httpx.AsyncClient.get")
    async def test_get_tasks_list_error(
        self, mock_get: MagicMock, client, caplog
    ):
        """Tests get_tasks_list when there is an error sending request."""
        mock_get.side_effect = Exception("mock error")
        response = client.get(
            "/api/v1/get_tasks_list",
            params={
                "dag_id": "transform_and_upload",
                "dag_run_id": "mock_dag_run_id",
            },
        )
        response_content = response.json()
        assert response.status_code == 500
        assert (
            response_content["message"]
            == "Unable to retrieve job tasks list from airflow"
        )
        assert 1 == len(caplog.messages)

    @patch("httpx.AsyncClient.get")
    async def test_get_task_logs_query_params(self, mock_get, client, caplog):
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
        assert 0 == len(caplog.messages)
        assert response.status_code == 200
        assert response_content == {
            "message": expected_message,
            "data": {
                "params": expected_default_params,
                "logs": "mock logs",
            },
        }

    @patch("httpx.AsyncClient.get")
    async def test_get_task_logs_validation_error(
        self, mock_get, client, caplog
    ):
        """Tests get_task_logs when query_params are invalid."""
        invalid_params = {
            "dag_id": "mock_dag_id",
            "dag_run_id": "mock_dag_run_id",
            "task_id": "mock_task_id",
            "try_number": "invalid",
        }
        response = client.get("/api/v1/get_task_logs", params=invalid_params)
        response_content = response.json()
        assert response.status_code == 406
        assert (
            response_content["message"]
            == "Error validating request parameters"
        )
        assert 1 == len(caplog.messages)
        mock_get.assert_not_called()

    @patch("httpx.AsyncClient.get")
    async def test_get_task_logs_error(
        self, mock_get: MagicMock, client, caplog
    ):
        """Tests get_task_logs when there is an error sending request."""
        mock_get.side_effect = Exception("mock error")
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
        assert response.status_code == 500
        assert (
            response_content["message"]
            == "Unable to retrieve task logs from airflow"
        )
        assert 1 == len(caplog.messages)

    @patch("boto3.client")
    async def test_list_parameters(
        self, mock_ssm_client, client, caplog, describe_parameters_response
    ):
        """Tests list_parameters gets parameter info from aws param store."""
        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = describe_parameters_response
        mock_ssm_client.return_value.get_paginator.return_value = (
            mock_paginator
        )
        expected_params = {
            "v2": [
                {
                    "job_type": "job1",
                    "last_modified": "2025-01-23T11:50:04.605000-08:00",
                    "name": "/param_prefix/v2/job1/tasks/task1",
                    "task_id": "task1",
                    "modality": None,
                    "version": "v2",
                },
                {
                    "job_type": "job1",
                    "last_modified": "2025-01-23T11:50:04.605000-08:00",
                    "name": (
                        "/param_prefix/v2/job1/tasks"
                        "/modality_transformation_settings/ecephys"
                    ),
                    "task_id": "modality_transformation_settings",
                    "modality": "ecephys",
                    "version": "v2",
                },
            ],
        }

        for version, params_list in expected_params.items():
            response = client.get(f"/api/{version}/parameters")
            mock_ssm_client.assert_called_with("ssm")
            (mock_ssm_client.return_value.get_paginator).assert_called_with(
                "describe_parameters"
            )
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
            assert response.status_code == 200
            assert response_content == {
                "message": "Retrieved job parameters",
                "data": params_list,
            }
        assert 3 == len(caplog.messages)

    @patch("boto3.client")
    async def test_get_parameter(
        self, mock_ssm_client, client, caplog, get_parameter_response
    ):
        """Tests get_parameter retrieves values from aws param store."""
        mock_ssm_client.return_value.get_parameter.return_value = (
            get_parameter_response
        )
        expected_params = {
            "v2": "/param_prefix/v2/ecephys/tasks/task1",
        }

        for version, param_name in expected_params.items():
            response = client.get(
                f"/api/{version}/parameters/job_types/" f"ecephys/tasks/task1"
            )
            mock_ssm_client.assert_called_with("ssm")
            (mock_ssm_client.return_value.get_parameter).assert_called_with(
                Name=param_name, WithDecryption=True
            )
            response_content = response.json()
            assert response.status_code == 200
            assert response_content == {
                "message": f"Retrieved parameter for {param_name}",
                "data": {"foo": "bar"},
            }
        assert 0 == len(caplog.messages)

    @patch("boto3.client")
    async def test_get_parameter_error(self, mock_ssm_client, client, caplog):
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
            "v2": "/param_prefix/v2/foo/tasks/bar",
        }

        for version, param_name in expected_params.items():
            response = client.get(
                f"/api/{version}/parameters/job_types/foo/tasks/bar"
            )
            response_content = response.json()
            assert response.status_code == 500
            assert (
                response_content["message"]
                == f"Error retrieving parameter {param_name}"
            )
        assert 1, len(caplog.messages)

    @patch("boto3.client")
    @patch("fastapi.Request.session")
    async def test_put_parameter(
        self,
        mock_session: MagicMock,
        mock_ssm_client: MagicMock,
        client,
        caplog,
        put_parameter_response,
    ):
        """Tests put_parameter sets values in aws param store."""
        mock_user = {"name": "test_user", "email": "test_email"}
        mock_param_name = "/param_prefix/ecephys/tasks/task1"
        mock_param_value = {"foo": "bar"}
        mock_session.get.return_value = mock_user
        mock_ssm_client.return_value.put_parameter.return_value = (
            put_parameter_response
        )
        response = client.put(
            "/api/v1/parameters/job_types/ecephys/tasks/task1",
            json=mock_param_value,
        )
        mock_session.get.assert_called_with("user")
        mock_ssm_client.assert_called_with("ssm")
        mock_ssm_client.return_value.put_parameter.assert_called_with(
            Name=mock_param_name,
            Value=json.dumps(mock_param_value),
            Type="String",
            Overwrite=True,
        )
        assert response.status_code == 200
        assert response.json() == {
            "message": f"Set parameter for {mock_param_name}",
            "data": mock_param_value,
        }
        assert 3 == len(caplog.messages)

    @patch("boto3.client")
    @patch("fastapi.Request.session")
    async def test_put_parameter_modality(
        self,
        mock_session: MagicMock,
        mock_ssm_client: MagicMock,
        client,
        caplog,
        put_parameter_response,
    ):
        """Tests put_parameter sets values in aws param store when modality
        is provided."""
        task = "modality_transformation_settings"
        mock_user = {"name": "test_user", "email": "test_email"}
        mock_param_name = f"/param_prefix/v2/ecephys/tasks/{task}/ecephys"
        mock_param_value = {"foo": "bar"}
        mock_session.get.return_value = mock_user
        mock_ssm_client.return_value.put_parameter.return_value = (
            put_parameter_response
        )
        response = client.put(
            f"/api/v2/parameters/job_types/ecephys/tasks/{task}" f"/ecephys",
            json=mock_param_value,
        )
        mock_session.get.assert_called_with("user")
        mock_ssm_client.assert_called_with("ssm")
        mock_ssm_client.return_value.put_parameter.assert_called_with(
            Name=mock_param_name,
            Value=json.dumps(mock_param_value),
            Type="String",
            Overwrite=True,
        )
        assert 3 == len(caplog.messages)
        assert response.status_code == 200
        assert response.json() == {
            "message": f"Set parameter for {mock_param_name}",
            "data": mock_param_value,
        }

    @patch("boto3.client")
    @patch("fastapi.Request.session")
    async def test_put_parameter_unauthenticated(
        self,
        mock_session: MagicMock,
        mock_ssm_client: MagicMock,
        client,
        caplog,
    ):
        """Tests put_parameter returns 401 Unauthorized error when user is
        not signed in."""
        mock_session.get.return_value = None
        response = client.put(
            "/api/v2/parameters/job_types/ecephys/tasks/task1",
            json={"foo": "bar"},
        )
        mock_ssm_client.assert_not_called()
        assert response.status_code == 401
        assert response.json()["message"] == "User not authenticated"
        assert 0 == len(caplog.messages)

    @patch("boto3.client")
    @patch("fastapi.Request.session")
    async def test_put_parameter_invalid_params(
        self,
        mock_session: MagicMock,
        mock_ssm_client: MagicMock,
        client,
        caplog,
    ):
        """Tests put_parameter is not allowed for invalid param components."""
        mock_session.get.return_value = {"name": "test", "email": "test"}
        request_urls = [
            "/api/v3/parameters/job_types/ecephys/tasks/task1",
            "/api/v2/parameters/job_types/new job/tasks/task1",
            "/api/v2/parameters/job_types/new_job/tasks/new task",
        ]
        for url in request_urls:
            response = client.put(url, json={"foo": "bar"})
            mock_ssm_client.assert_not_called()
            assert response.status_code == 400
            response_content = response.json()
            assert "Invalid parameter" == response_content["message"]
        assert 0 == len(caplog.messages)

    @patch("boto3.client")
    @patch("fastapi.Request.session")
    async def test_put_parameter_error(
        self,
        mock_session: MagicMock,
        mock_ssm_client: MagicMock,
        client,
        caplog,
        put_parameter_response,
    ):
        """Tests put_parameter when there is a client error."""
        mock_params = {
            "v2": "/param_prefix/v2/ecephys/tasks/task1",
        }
        mock_param_value = {"foo": "bar"}
        mock_session.get.return_value = {"name": "test", "email": "test"}
        mock_ssm_client.return_value.put_parameter.return_value = (
            put_parameter_response
        )
        mock_ssm_client.return_value.put_parameter.side_effect = ClientError(
            {
                "Error": {
                    "Code": "ParameterMaxVersionLimitExceeded",
                    "Message": "Parameter max version limit exceeded",
                }
            },
            "PutParameter",
        )
        for version, param_name in mock_params.items():
            response = client.put(
                f"/api/{version}/parameters/job_types/ecephys/tasks" f"/task1",
                json=mock_param_value,
            )
            assert response.status_code == 500
            assert (
                response.json()["message"]
                == f"Error setting parameter {param_name}"
            )
        assert (
            "An error occurred"
            " (ParameterMaxVersionLimitExceeded) when calling the"
            " PutParameter operation: Parameter max version limit exceeded"
        ) in caplog.text

    async def test_index(self, client, caplog):
        """Tests that form renders at startup as expected."""

        response = client.get("/")
        assert 0 == len(caplog.messages)
        assert response.status_code == 200
        assert "Submit Jobs" in response.text

    async def test_jobs(self, client, caplog):
        """Tests that job status page renders at startup as expected."""
        response = client.get("/jobs")
        assert 0 == len(caplog.messages)
        assert response.status_code == 200
        assert "Jobs Submitted:" in response.text

    @patch("httpx.AsyncClient.get")
    async def test_tasks_table_success(
        self, mock_get: MagicMock, client, caplog, list_task_instances_response
    ):
        """Tests that job tasks table renders as expected."""
        mock_response = Response()
        mock_response.status_code = 200
        mock_response._content = json.dumps(
            list_task_instances_response
        ).encode("utf-8")
        mock_get.return_value = mock_response

        response = client.get(
            "/job_tasks_table",
            params={"dag_id": "dag_id", "dag_run_id": "dag_run_id"},
        )
        assert 0 == len(caplog.messages)
        assert response.status_code == 200
        assert "Task ID" in response.text
        assert "Try Number" in response.text

    @patch("httpx.AsyncClient.get")
    async def test_tasks_table_failure(
        self, mock_get: MagicMock, client, caplog
    ):
        """Tests that job status table renders error message from airflow."""
        mock_response = Response()
        mock_response.status_code = 500
        mock_response._content = json.dumps(
            {"message": "test airflow error"}
        ).encode("utf-8")
        mock_get.return_value = mock_response
        response = client.get(
            "/job_tasks_table",
            params={
                "dag_id": "transform_and_upload",
                "dag_run_id": "dag_run_id",
            },
        )
        assert 0 == len(caplog.messages)
        assert response.status_code == 200
        assert "Task ID" in response.text
        assert "Try Number" in response.text
        assert "Error retrieving job tasks list from airflow" in response.text
        assert "test airflow error" in response.text

    @patch("httpx.AsyncClient.get")
    async def test_logs_success(self, mock_get: MagicMock, client, caplog):
        """Tests that task logs page renders as expected."""
        mock_response = Response()
        mock_response.status_code = 200
        mock_response._content = b"mock log content"
        mock_get.return_value = mock_response
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
        assert 0 == len(caplog.messages)
        assert response.status_code == 200
        assert "mock log content" in response.text

    @patch("httpx.AsyncClient.get")
    async def test_logs_failure(self, mock_get: MagicMock, client, caplog):
        """Tests that task logs page renders error message from airflow."""
        mock_response = Response()
        mock_response.status_code = 500
        mock_response._content = json.dumps(
            {"message": "test airflow error"}
        ).encode("utf-8")
        mock_get.return_value = mock_response
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
        assert 0 == len(caplog.messages)
        assert response.status_code == 200
        assert "Error retrieving task logs from airflow" in response.text
        assert "test airflow error" in response.text

    async def test_download_job_template(self, client, caplog):
        """Tests that job template downloads as xlsx file."""

        response = client.get("/api/job_upload_template")
        assert 0 == len(caplog.messages)
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

        assert expected_streaming_response.headers.items() == list(
            response.headers.items()
        )
        assert 200 == response.status_code

    async def test_job_params(self, client, caplog):
        """Tests that job params page renders at startup as expected."""

        response = client.get("/job_params")
        assert 0 == len(caplog.messages)
        assert response.status_code == 200
        assert "Job Parameters" in response.text

    @patch("fastapi.Request.session")
    async def test_admin(self, mock_session: MagicMock, client, caplog):
        """Tests that the admin page renders when user is authenticated."""
        expected_user = {"name": "test_user", "email": "test_email"}
        mock_session.get.return_value = expected_user
        response = client.get("/admin")
        mock_session.get.assert_called_once_with("user")
        assert 0 == len(caplog.messages)
        assert response.status_code == 200
        assert "Admin" in response.text
        assert "test_user" in response.text

    @patch.dict(os.environ, {"ENV_NAME": "local"}, clear=True)
    async def test_admin_local(self, client, caplog):
        """Tests that the admin page renders when user is authenticated."""
        response = client.get("/admin")
        assert 0 == len(caplog.messages)
        assert response.status_code == 200
        assert "Admin" in response.text
        assert "local user" in response.text

    @patch("fastapi.Request.session")
    @patch("aind_data_transfer_service.server.RedirectResponse")
    async def test_admin_unauthenticated(
        self,
        mock_redirect_response: MagicMock,
        mock_session: MagicMock,
        client,
        caplog,
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
        response = client.get("/admin")
        mock_redirect_response.assert_called_once_with(url="/login")
        assert 0 == len(caplog.messages)
        assert response.status_code == 307

    @patch("aind_data_transfer_service.server.JobUploadTemplate")
    async def test_download_invalid_job_template(
        self, mock_job_template: MagicMock, client, caplog
    ):
        """Tests that download invalid job template returns errors."""
        mock_job_template.create_excel_sheet_filestream.side_effect = (
            Exception("mock invalid job template")
        )

        response = client.get("/api/job_upload_template")
        expected_response = {
            "message": "Error creating job template",
            "data": {"error": "Exception('mock invalid job template',)"},
        }
        assert 500 == response.status_code
        assert expected_response == response.json()
        assert 1 == len(caplog.messages)

    @patch("aind_data_transfer_service.server.get_airflow_jobs")
    @patch("aind_data_transfer_service.server.get_job_types")
    @patch("aind_data_transfer_service.server.get_project_names")
    async def test_validate_v2_csv(
        self,
        mock_get_project_names: MagicMock,
        mock_get_job_types: MagicMock,
        mock_get_airflow_jobs: MagicMock,
        client,
        caplog,
    ):
        """Tests that valid csv file is returned."""
        mock_get_project_names.return_value = [
            "Ephys Platform",
            "Behavior Platform",
        ]
        mock_get_job_types.return_value = ["default", "ecephys", "custom"]
        mock_get_airflow_jobs.return_value = (0, list())

        with open(NEW_SAMPLE_CSV, "rb") as f:
            files = {
                "file": f,
            }
            response = client.post(url="/api/v2/validate_csv", files=files)

        mock_get_airflow_jobs.assert_called_once()
        assert 200 == response.status_code
        assert 1 == len(caplog.messages)

    @patch("aind_data_transfer_service.server.get_project_names")
    async def test_validate_v2_null_csv(
        self, mock_get_project_names: MagicMock, client, caplog
    ):
        """Tests that invalid file type returns FileNotFoundError"""
        mock_get_project_names.return_value = [
            "Ephys Platform",
            "Behavior Platform",
        ]
        with open(SAMPLE_INVALID_EXT, "rb") as f:
            files = {
                "file": f,
            }
            response = client.post(url="/api/v2/validate_csv", files=files)
        assert response.status_code == 406
        assert ["Invalid input file type"] == response.json()["data"]["errors"]
        assert 1 == len(caplog.messages)

    @patch("aind_data_transfer_service.server.get_airflow_jobs")
    @patch("aind_data_transfer_service.server.get_job_types")
    @patch("aind_data_transfer_service.server.get_project_names")
    async def test_validate_v2_malformed_xlsx(
        self,
        mock_get_project_names: MagicMock,
        mock_get_job_types: MagicMock,
        mock_get_airflow_jobs: MagicMock,
        client,
        caplog,
    ):
        """Tests that invalid xlsx returns errors"""
        mock_get_project_names.return_value = [
            "Ephys Platform",
            "Behavior Platform",
        ]
        mock_get_job_types.return_value = ["default", "custom"]
        mock_get_airflow_jobs.return_value = (0, list())
        with open(MALFORMED_SAMPLE_XLSX, "rb") as f:
            files = {
                "file": f,
            }
            response = client.post(url="/api/v2/validate_csv", files=files)
        assert 1 == len(caplog.messages)
        assert response.status_code == 406
        assert 3 == len(response.json()["data"]["errors"])

    @patch("aind_data_transfer_service.server.get_airflow_jobs")
    @patch("aind_data_transfer_service.server.get_job_types")
    @patch("aind_data_transfer_service.server.get_project_names")
    async def test_validate_v2_csv_empty_rows(
        self,
        mock_get_project_names: MagicMock,
        mock_get_job_types: MagicMock,
        mock_get_airflow_jobs: MagicMock,
        client,
        caplog,
    ):
        """Tests that empty rows are ignored from valid csv and xlsx files."""
        mock_get_project_names.return_value = [
            "Ephys Platform",
            "Behavior Platform",
        ]
        mock_get_job_types.return_value = ["default", "ecephys", "custom"]
        mock_get_airflow_jobs.return_value = (0, list())
        with open(SAMPLE_CSV_EMPTY_ROWS_2, "rb") as f:
            files = {
                "file": f,
            }
            response = client.post(url="/api/v2/validate_csv", files=files)
        assert 1 == len(caplog.messages)
        assert 200 == response.status_code

    @patch("aind_data_transfer_service.server.get_airflow_jobs")
    @patch("aind_data_transfer_service.server.get_job_types")
    @patch("aind_data_transfer_service.server.get_project_names")
    async def test_validate_v2_malformed_csv2(
        self,
        mock_get_project_names: MagicMock,
        mock_get_job_types: MagicMock,
        mock_get_airflow_jobs: MagicMock,
        client,
        caplog,
    ):
        """Tests that invalid csv returns errors"""
        mock_get_project_names.return_value = ["Ephys Platform"]
        mock_get_job_types.return_value = ["default"]
        mock_get_airflow_jobs.return_value = (0, list())
        with open(MALFORMED_SAMPLE_CSV_2, "rb") as f:
            files = {
                "file": f,
            }
            response = client.post(url="/api/v2/validate_csv", files=files)
        assert response.status_code == 406
        assert 1 == len(caplog.messages)

    @patch("aind_data_transfer_service.server.get_airflow_jobs")
    @patch("aind_data_transfer_service.server.get_job_types")
    @patch("aind_data_transfer_service.server.get_project_names")
    @patch("aind_data_transfer_service.server.map_csv_row_to_job")
    async def test_validate_v2_malformed_csv2_with_exception(
        self,
        mock_map_row_to_job: MagicMock,
        mock_get_project_names: MagicMock,
        mock_get_job_types: MagicMock,
        mock_get_airflow_jobs: MagicMock,
        client,
        caplog,
    ):
        """Tests that invalid csv returns errors"""
        mock_map_row_to_job.side_effect = Exception("Error")
        mock_get_project_names.return_value = ["Ephys Platform"]
        mock_get_job_types.return_value = ["default"]
        mock_get_airflow_jobs.return_value = (0, list())

        with open(MALFORMED_SAMPLE_CSV_2, "rb") as f:
            files = {
                "file": f,
            }
            response = client.post(url="/api/v2/validate_csv", files=files)
        assert response.status_code == 406
        assert 1 == len(caplog.messages)

    @patch("httpx.AsyncClient.post")
    @patch("aind_data_transfer_service.server.get_airflow_jobs")
    @patch("aind_data_transfer_service.server.get_project_names")
    @patch("aind_data_transfer_service.server.get_job_types")
    async def test_submit_v1_v2_jobs_406(
        self,
        mock_get_job_types: MagicMock,
        mock_get_project_names: MagicMock,
        mock_get_airflow_jobs: MagicMock,
        mock_post: MagicMock,
        client,
        caplog,
    ):
        """Tests submit jobs 406 response."""
        mock_get_job_types.return_value = ["ecephys"]
        mock_get_project_names.return_value = ["Ephys Platform"]
        mock_get_airflow_jobs.return_value = (0, list())
        submit_job_response = client.post(url="/api/v2/submit_jobs", json={})
        assert 406 == submit_job_response.status_code
        mock_post.assert_not_called()
        assert "There were validation errors processing {}" in caplog.text
        mock_get_job_types.assert_called_once_with("v2")
        mock_get_airflow_jobs.assert_called_once()
        assert 1 == mock_get_project_names.call_count

    @patch("httpx.AsyncClient.post")
    @patch("aind_data_transfer_service.server.get_airflow_jobs")
    @patch("aind_data_transfer_service.server.get_project_names")
    @patch("aind_data_transfer_service.server.get_job_types")
    async def test_submit_v1_v2_jobs_200(
        self,
        mock_get_job_types: MagicMock,
        mock_get_project_names: MagicMock,
        mock_get_airflow_jobs: MagicMock,
        mock_post: MagicMock,
        client,
        caplog,
        example_configs_v2,
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
        job_request_v2 = SubmitJobRequestV2(
            upload_jobs=[example_configs_v2], user_email="abc@example.com"
        )
        request_json_v2 = job_request_v2.model_dump(mode="json")
        submit_job_response = client.post(
            url="/api/v2/submit_jobs", json=request_json_v2
        )
        assert 200 == submit_job_response.status_code
        mock_get_job_types.assert_called_once_with("v2")
        mock_get_airflow_jobs.assert_called_once()
        assert 1 == mock_get_project_names.call_count
        assert 5 == len(caplog.messages)

    @patch("httpx.AsyncClient.post")
    @patch("aind_data_transfer_service.server.get_airflow_jobs")
    @patch("aind_data_transfer_service.server.get_project_names")
    @patch("aind_data_transfer_service.server.get_job_types")
    async def test_submit_v1_v2_jobs_500(
        self,
        mock_get_job_types: MagicMock,
        mock_get_project_names: MagicMock,
        mock_get_airflow_jobs: MagicMock,
        mock_post: MagicMock,
        client,
        caplog,
        example_configs_v2,
    ):
        """Tests submit jobs failure."""
        mock_get_project_names.return_value = ["Ephys Platform"]
        mock_get_job_types.return_value = ["ecephys"]
        mock_get_airflow_jobs.return_value = (0, list())
        mock_response = Response()
        mock_response.status_code = 500
        mock_response._content = json.dumps({"message": "sent"}).encode(
            "utf-8"
        )
        mock_post.return_value = mock_response
        job_request_v2 = SubmitJobRequestV2(
            upload_jobs=[example_configs_v2],
            user_email="abc@example.com",
        )
        request_json_v2 = job_request_v2.model_dump(mode="json")
        submit_job_response = client.post(
            url="/api/v2/submit_jobs", json=request_json_v2
        )
        assert 500 == submit_job_response.status_code
        mock_get_job_types.assert_called_once_with("v2")
        mock_get_airflow_jobs.assert_called_once()
        assert 1 == mock_get_project_names.call_count
        assert 6 == len(caplog.messages)

    @patch("httpx.AsyncClient.post")
    @patch("aind_data_transfer_service.server.get_airflow_jobs")
    @patch("aind_data_transfer_service.server.get_project_names")
    @patch("aind_data_transfer_service.server.get_job_types")
    async def test_submit_v1_v2_jobs_exception_500(
        self,
        mock_get_job_types: MagicMock,
        mock_get_project_names: MagicMock,
        mock_get_airflow_jobs: MagicMock,
        mock_post: MagicMock,
        client,
        caplog,
    ):
        """Tests submit jobs exception response."""
        mock_get_job_types.return_value = ["ecephys"]
        mock_get_project_names.return_value = ["Ephys Platform"]
        mock_get_airflow_jobs.return_value = (0, list())
        mock_post.side_effect = Exception("Something went wrong")
        request_json_v2 = {
            "user_email": "abc@example.com",
            "email_notification_types": ["fail"],
            "upload_jobs": [
                {
                    "job_type": "ecephys",
                    "user_email": "abc@example.com",
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
        submit_job_response = client.post(
            url="/api/v2/submit_jobs", json=request_json_v2
        )
        assert 500 == submit_job_response.status_code
        assert 6 == len(caplog.messages)
        mock_get_job_types.assert_called_once_with("v2")
        mock_get_airflow_jobs.assert_called_once()
        assert 1 == mock_get_project_names.call_count

    @patch("httpx.AsyncClient.post")
    @patch("aind_data_transfer_service.server.get_airflow_jobs")
    @patch("aind_data_transfer_service.server.get_project_names")
    @patch("aind_data_transfer_service.server.get_job_types")
    async def test_submit_v2_jobs_200_basic_serialization(
        self,
        mock_get_job_types: MagicMock,
        mock_get_project_names: MagicMock,
        mock_get_airflow_jobs: MagicMock,
        mock_post: MagicMock,
        client,
        caplog,
        example_configs_v2,
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

        job_request_v2 = SubmitJobRequestV2(
            upload_jobs=[example_configs_v2],
            user_email="abc@example.com",
        )
        post_request_content_v2 = job_request_v2.model_dump(mode="json")
        submit_job_response = client.post(
            url="/api/v2/submit_jobs", json=post_request_content_v2
        )
        assert 200 == submit_job_response.status_code
        assert 5 == len(caplog.messages)
        mock_get_job_types.assert_called_once_with("v2")
        mock_get_airflow_jobs.assert_called_once()
        assert 1 == mock_get_project_names.call_count

    @patch("aind_data_transfer_service.server.get_airflow_jobs")
    @patch("aind_data_transfer_service.server.get_job_types")
    @patch("aind_data_transfer_service.server.get_project_names")
    async def test_validate_json(
        self,
        mock_get_project_names: MagicMock,
        mock_get_job_types: MagicMock,
        mock_get_airflow_jobs: MagicMock,
        client,
        caplog,
        example_configs_v2,
    ):
        """Tests validate_json when json is valid."""

        mock_get_project_names.return_value = ["Ephys Platform"]
        mock_get_job_types.return_value = ["ecephys"]
        mock_get_airflow_jobs.return_value = (0, list())

        upload_job = example_configs_v2
        submit_job_request_v2 = SubmitJobRequestV2(
            upload_jobs=[upload_job],
            user_email="abc@example.com",
        )
        post_request_content = submit_job_request_v2.model_dump(mode="json")
        response = client.post(
            "/api/v2/validate_json",
            json=post_request_content,
        )
        response_json = response.json()
        assert 200 == response.status_code
        assert "Valid model" == response_json["message"]
        assert post_request_content == response_json["data"]["model_json"]
        assert (
            aind_data_transfer_service_version
            == response_json["data"]["version"]
        )
        mock_get_airflow_jobs.assert_called_once()
        mock_get_job_types.assert_called_once_with("v2")
        assert 1 == mock_get_project_names.call_count
        assert 3 == len(caplog.messages)

    @patch("aind_data_transfer_service.server.get_airflow_jobs")
    @patch("aind_data_transfer_service.server.get_project_names")
    @patch("aind_data_transfer_service.server.get_job_types")
    async def test_validate_json_invalid(
        self,
        mock_get_job_types: MagicMock,
        mock_get_project_names: MagicMock,
        mock_get_airflow_jobs: MagicMock,
        client,
        caplog,
    ):
        """Tests validate_json when json is invalid."""
        mock_get_job_types.return_value = ["ecephys"]
        mock_get_project_names.return_value = ["Ephys Platform"]
        mock_get_airflow_jobs.return_value = (0, list())
        content = {"foo": "bar"}
        response = client.post("/api/v2/validate_json", json=content)
        response_json = response.json()
        assert 406 == response.status_code
        assert "There were validation errors" == response_json["message"]
        assert content == response_json["data"]["model_json"]
        assert (
            aind_data_transfer_service_version
            == response_json["data"]["version"]
        )
        assert (
            f"There were validation errors processing {content}" in caplog.text
        )
        mock_get_airflow_jobs.assert_called_once()
        mock_get_job_types.assert_called_once_with("v2")
        assert 1 == mock_get_project_names.call_count

    @patch("httpx.AsyncClient.post")
    @patch("aind_data_transfer_service.server.get_project_names")
    @patch("aind_data_transfer_service.server.get_job_types")
    async def test_validate_json_v2_invalid_current(
        self,
        mock_get_job_types: MagicMock,
        mock_get_project_names: MagicMock,
        mock_post: MagicMock,
        client,
        caplog,
        get_dag_run_response,
        example_configs_v2,
    ):
        """Tests validate_json_v2 when there is a duplicate job running."""

        mock_get_project_names.return_value = ["Ephys Platform"]
        mock_get_job_types.return_value = ["ecephys"]
        # assume a job is already running
        job_request = SubmitJobRequestV2(
            upload_jobs=[example_configs_v2], user_email="abc@example.com"
        ).model_dump(mode="json", exclude_none=True)
        current_job = job_request["upload_jobs"][0]
        airflow_response = {
            "dag_runs": [{**get_dag_run_response, "conf": current_job}],
            "total_entries": 1,
        }
        mock_dag_runs_response = Response()
        mock_dag_runs_response.status_code = 200
        mock_dag_runs_response._content = json.dumps(airflow_response).encode(
            "utf-8"
        )
        mock_post.return_value = mock_dag_runs_response
        # now submit same job again
        resp = client.post("/api/v2/validate_json", json=job_request)
        resp_json = resp.json()
        assert 406 == resp.status_code
        assert "There were validation errors" == resp_json["message"]
        assert (
            "Job is already running/queued for "
            "ecephys_690165_2024-02-19_11-25-17"
        ) in resp_json["data"]["errors"]
        assert "There were validation errors processing" in caplog.text

    @patch("pydantic.BaseModel.model_validate_json")
    @patch("aind_data_transfer_service.server.get_airflow_jobs")
    @patch("aind_data_transfer_service.server.get_project_names")
    @patch("aind_data_transfer_service.server.get_job_types")
    async def test_validate_json_error(
        self,
        mock_get_job_types: MagicMock,
        mock_get_project_names: MagicMock,
        mock_get_airflow_jobs: MagicMock,
        mock_model_validate_json: MagicMock,
        client,
        caplog,
    ):
        """Tests validate_json when there is an unknown error."""

        mock_get_job_types.return_value = ["ecephys"]
        mock_get_project_names.return_value = ["Ephys Platform"]
        mock_get_airflow_jobs.return_value = (0, list())
        mock_model_validate_json.side_effect = Exception("Unknown error")
        response = client.post(
            "/api/v2/validate_json",
            json={"foo": "bar"},
        )
        response_json = response.json()
        assert 500 == response.status_code
        assert "There was an internal server error" == response_json["message"]
        assert {"foo": "bar"} == response_json["data"]["model_json"]
        assert "('Unknown error',)" == response_json["data"]["errors"]
        assert (
            aind_data_transfer_service_version
            == response_json["data"]["version"]
        )
        mock_model_validate_json.assert_called()
        assert "Unknown error" in caplog.text
        mock_get_airflow_jobs.assert_called_once()
        mock_get_job_types.assert_called_once_with("v2")
        assert 1 == mock_get_project_names.call_count

    @patch.dict(os.environ, {"ENV_NAME": "dev"}, clear=True)
    @patch("boto3.client")
    @patch("aind_data_transfer_service.server.OAuth")
    async def test_login(
        self,
        mock_set_oauth: MagicMock,
        mock_secrets_client: MagicMock,
        client,
        caplog,
        get_secrets_response,
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
            get_secrets_response
        )
        response = client.get("/login")
        assert response.status_code == 200
        assert 0 == len(caplog.messages)

    @patch("aind_data_transfer_service.server.RedirectResponse")
    @patch("fastapi.Request.session")
    async def test_logout(
        self, mock_session: MagicMock, mock_redirect: MagicMock, client, caplog
    ):
        """Tests logout clears user from session and redirects to index."""
        expected_user = {"name": "test_user", "email": "test_email"}
        mock_session.get.return_value = expected_user
        mock_redirect.return_value = JSONResponse(
            content={"message": "Redirecting to index"},
            status_code=307,
        )
        response = client.get("/logout")
        mock_redirect.assert_called_once_with(url="/")
        assert 0 == len(caplog.messages)
        assert response.status_code == 307

    @patch("boto3.client")
    @patch("aind_data_transfer_service.server.OAuth")
    async def test_auth(
        self,
        mock_set_oauth: MagicMock,
        mock_secrets_client: MagicMock,
        client,
        caplog,
        get_secrets_response,
    ):
        """Tests the auth callback function."""
        mock_set_oauth.return_value.azure.authorize_access_token = AsyncMock(
            return_value={"userinfo": {"some_user": "info"}}
        )
        mock_secrets_client.return_value.get_secret_value.return_value = (
            get_secrets_response
        )
        response = client.get("/auth")
        mock_oauth = mock_set_oauth.return_value
        mock_azure = mock_oauth.azure
        mock_azure.authorize_access_token.assert_called_once()
        assert response.status_code == 200
        assert 0 == len(caplog.messages)

    @patch("boto3.client")
    @patch("aind_data_transfer_service.server.OAuth")
    async def test_auth_error(
        self,
        mock_set_oauth: MagicMock,
        mock_secrets_client: MagicMock,
        client,
        caplog,
        get_secrets_response,
    ):
        """Tests an error in the auth callback function."""
        mock_set_oauth.return_value.azure.authorize_access_token = AsyncMock(
            side_effect=OAuthError("Error Logging In")
        )
        mock_secrets_client.return_value.get_secret_value.return_value = (
            get_secrets_response
        )
        response = client.get("/auth")
        expected_response = {
            "message": "Error Logging In",
            "data": {"error": "OAuthError('Error Logging In: ',)"},
        }
        assert 0 == len(caplog.messages)
        assert response.status_code == 500
        assert response.json() == expected_response

    @patch("boto3.client")
    @patch("aind_data_transfer_service.server.OAuth")
    async def test_auth_error_userinfo(
        self,
        mock_set_oauth: MagicMock,
        mock_secrets_client: MagicMock,
        client,
        caplog,
        get_secrets_response,
    ):
        """Tests the auth callback function when userinfo is not provided."""
        mock_set_oauth.return_value.azure.authorize_access_token = AsyncMock(
            return_value={"invalid": {"some_user": "info"}}
        )
        mock_secrets_client.return_value.get_secret_value.return_value = (
            get_secrets_response
        )
        response = client.get("/auth")
        expected_response = {
            "message": "Error Logging In",
            "data": {
                "error": "ValueError('User info not found in access token.',)"
            },
        }
        assert 0 == len(caplog.messages)
        assert response.status_code == 500
        assert response.json() == expected_response

    @patch("httpx.AsyncClient.patch")
    @patch("httpx.AsyncClient.post")
    async def test_cancel_jobs_200(
        self, mock_post: MagicMock, mock_patch: MagicMock, client, caplog
    ):
        """Tests cancel_job success."""
        mock_patch_response = Response()
        mock_patch_response.status_code = 200
        mock_patch.return_value = mock_patch_response
        mock_post_response = Response()
        mock_post_response.status_code = 200
        mock_post.return_value = mock_post_response
        request_json = {
            "s3_prefix": "abc_123",
            "dag_id": "transform_and_upload_v2",
            "dag_run_id": "manual__2025-11-08T18:20:55.367146+00:00",
        }
        cancel_job_response = client.post(
            url="/api/v2/cancel_job", json=request_json
        )
        assert 200 == cancel_job_response.status_code
        mock_patch.assert_called_with(
            url=(
                "airflow_jobs_url/transform_and_upload_v2/dagRuns/"
                "manual__2025-11-08T18:20:55.367146+00:00"
            ),
            json={"state": "failed"},
        )
        mock_post.assert_called_with(
            url="airflow_jobs_url/cancel_slurm_jobs/dagRuns",
            json={
                "conf": {
                    "dag_run_id": "manual__2025-11-08T18:20:55.367146+00:00",
                    "s3_prefix": "abc_123",
                    "partition": "aind",
                }
            },
        )
        # Logs may include request info

    @patch("httpx.AsyncClient.patch")
    @patch("httpx.AsyncClient.post")
    async def test_cancel_jobs_500(
        self, mock_post: MagicMock, mock_patch: MagicMock, client, caplog
    ):
        """Tests cancel_job error."""
        mock_patch_response = Response()
        mock_patch_response.status_code = 200
        mock_patch.return_value = mock_patch_response
        mock_post_response = Response()
        mock_post_response.status_code = 500
        mock_post.return_value = mock_post_response
        request_json = {
            "s3_prefix": "abc_123",
            "dag_id": "transform_and_upload_v2",
            "dag_run_id": "manual__2025-11-08T18:20:55.367146+00:00",
        }

        cancel_job_response = client.post(
            url="/api/v2/cancel_job", json=request_json
        )
        assert 500 == cancel_job_response.status_code
        assert "Error canceling job." == cancel_job_response.json()["message"]
        mock_patch.assert_called_with(
            url=(
                "airflow_jobs_url/transform_and_upload_v2/dagRuns/"
                "manual__2025-11-08T18:20:55.367146+00:00"
            ),
            json={"state": "failed"},
        )
        mock_post.assert_called_with(
            url="airflow_jobs_url/cancel_slurm_jobs/dagRuns",
            json={
                "conf": {
                    "dag_run_id": "manual__2025-11-08T18:20:55.367146+00:00",
                    "s3_prefix": "abc_123",
                    "partition": "aind",
                }
            },
        )
        # Expect at least error log for the failure
        assert "500 Server Error" in caplog.text


if __name__ == "__main__":
    pytest.main([__file__])
