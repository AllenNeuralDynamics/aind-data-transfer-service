"""Tests methods in models module"""

import json
import os
import unittest
from datetime import datetime, timezone
from pathlib import Path

from aind_data_transfer_service.models.internal import (
    AirflowDagRunsResponse,
    JobStatus,
)

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
        """Tests jinjia dict property"""
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


if __name__ == "__main__":
    unittest.main()
