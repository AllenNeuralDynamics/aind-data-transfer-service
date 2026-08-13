"""Tests methods in models module"""

import json
import os
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import patch

from aind_data_transfer_service.models.internal import (
    AirflowDagRunsRequestParameters,
    AirflowDagRunsResponse,
    JobStatus,
)
from pydantic import ValidationError

TEST_DIRECTORY = Path(os.path.dirname(os.path.realpath(__file__)))
DAG_RUN_RESPONSE = (
    TEST_DIRECTORY / "resources" / "airflow_dag_runs_response.json"
)


class TestJobStatus(unittest.TestCase):
    """Tests JobStatus class"""

    @classmethod
    def setUpClass(cls) -> None:
        """Read json files"""
        with open(DAG_RUN_RESPONSE, "r") as f:
            dag_run_response = json.load(f)

        cls.dag_run_response = dag_run_response

    def test_from_airflow_dag_run(self):
        """Tests from_airflow_dag_run method"""
        dag_response = AirflowDagRunsResponse.model_validate_json(
            json.dumps(self.dag_run_response)
        )
        job_status_0 = JobStatus.from_airflow_dag_run(dag_response.dag_runs[0])
        self.assertEqual(
            "manual__2024-05-18T22:08:52.286765+00:00", job_status_0.job_id
        )

    def test_jinja_dict(self):
        """Tests jinja_dict property"""
        dag_response = AirflowDagRunsResponse.model_validate_json(
            json.dumps(self.dag_run_response)
        )
        job_status_0 = JobStatus.from_airflow_dag_run(dag_response.dag_runs[4])
        jinja_dict = job_status_0.jinja_dict
        expected_output = {
            "dag_id": "transform_and_upload",
            "end_time": datetime(
                2024, 5, 18, 23, 51, 17, 716003, tzinfo=timezone.utc
            ),
            "job_id": "manual__2024-05-18T23:43:19.184853+00:00",
            "job_state": "failed",
            "name": "ecephys_655019_2000-10-10_01-00-24",
            "job_type": "",
            "start_time": datetime(
                2024, 5, 18, 23, 43, 19, 428659, tzinfo=timezone.utc
            ),
            "submit_time": datetime(
                2024, 5, 18, 23, 43, 19, 184853, tzinfo=timezone.utc
            ),
        }

        self.assertEqual(expected_output, jinja_dict)


class TestAirflowDagRunsRequestParameters(unittest.TestCase):
    """Tests AirflowDagRunsRequestParameters class"""

    def test_execution_date_gte_recalculated_per_instance(self):
        """Tests that execution_date_gte uses default_factory, not a static default.

        A static default is computed once at class-definition time and becomes
        stale after 2+ weeks of server uptime, causing 406 errors on
        /api/v1/get_job_status_list. With default_factory the value is
        recalculated fresh for every new instance, so two instances created
        at different mock times must produce different execution_date_gte values.
        """
        time1 = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        time2 = datetime(2026, 1, 2, 12, 0, 0, tzinfo=timezone.utc)

        with patch(
            "aind_data_transfer_service.models.internal.datetime",
            wraps=datetime,
        ) as mock_dt:
            mock_dt.now.return_value = time1
            params1 = AirflowDagRunsRequestParameters()

        with patch(
            "aind_data_transfer_service.models.internal.datetime",
            wraps=datetime,
        ) as mock_dt:
            mock_dt.now.return_value = time2
            params2 = AirflowDagRunsRequestParameters()

        self.assertIsNotNone(params1.execution_date_gte)
        self.assertIsNotNone(params2.execution_date_gte)
        self.assertNotEqual(
            params1.execution_date_gte,
            params2.execution_date_gte,
            "execution_date_gte must be recalculated per instance; "
            "equal values indicate a stale static default was used instead of "
            "default_factory.",
        )

    def test_execution_date_gte_default_cached(self):
        """Tests that a cached date from 3 weeks ago would fail validation."""

        old_cached_date = (
            datetime.now(timezone.utc) - timedelta(weeks=3)
        ).isoformat()

        with self.assertRaises(ValidationError):
            AirflowDagRunsRequestParameters(execution_date_gte=old_cached_date)


if __name__ == "__main__":
    unittest.main()
