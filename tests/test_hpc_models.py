"""Module to test hpc client classes"""

import json
import os
import unittest
from datetime import datetime
from pathlib import Path

from aind_data_transfer_service.hpc.models import (
    HpcJobStatusResponse,
    JobStatus,
)

TEST_DIRECTORY = Path(os.path.dirname(os.path.realpath(__file__)))
MOCK_DB_FILE = TEST_DIRECTORY / "test_server" / "db.json"


class TestJobStatus(unittest.TestCase):
    """Tests methods in JobStatus class"""

    @classmethod
    def setUpClass(cls):
        """Load mock_db before running tests."""

        with open(MOCK_DB_FILE) as f:
            json_contents = json.load(f)
        cls.job_status_response = json_contents["jobs"]

    def test_from_hpc_job_status(self):
        """Tests parsing from hpc response json"""
        hpc_jobs = [
            HpcJobStatusResponse.parse_obj(job_json)
            for job_json in self.job_status_response["jobs"]
        ]
        job_status_list = [
            JobStatus.from_hpc_job_status(hpc_job) for hpc_job in hpc_jobs
        ]
        jinja_list = [job.jinja_dict for job in job_status_list]
        expected_job_status_list = [
            JobStatus(
                end_time=datetime(2023, 9, 8, 17, 44, 6),
                job_id=10994495,
                job_state="RUNNING",
                name="bash",
                start_time=datetime(2023, 9, 3, 17, 44, 6),
                submit_time=datetime(2023, 9, 3, 17, 44, 6),
            ),
            JobStatus(
                end_time=datetime(2023, 9, 8, 10, 32, 52),
                job_id=11005019,
                job_state="TIMEOUT",
                name="my_job_name",
                start_time=datetime(2023, 9, 7, 7, 12, 42),
                submit_time=datetime(2023, 9, 5, 18, 19, 54),
            ),
            JobStatus(
                end_time=None,
                job_id=11005059,
                job_state="PENDING",
                name="analysis.job",
                start_time=None,
                submit_time=datetime(2023, 9, 7, 7, 25, 13),
            ),
            JobStatus(
                end_time=datetime(2023, 9, 8, 10, 32, 17),
                job_id=11013427,
                job_state="COMPLETED",
                name="some_job_2",
                start_time=datetime(2023, 9, 8, 10, 25, 5),
                submit_time=datetime(2023, 9, 6, 15, 43, 52),
            ),
            JobStatus(
                end_time=datetime(2023, 9, 8, 10, 30, 57),
                job_id=11013479,
                job_state="FAILED",
                name="some_command_job",
                start_time=datetime(2023, 9, 8, 10, 30, 37),
                submit_time=datetime(2023, 9, 8, 10, 30, 37),
            ),
            JobStatus(
                end_time=datetime(2023, 9, 8, 10, 29, 7),
                job_id=11013426,
                job_state="OUT_OF_MEMORY",
                name="JOB_NAME",
                start_time=datetime(2023, 9, 8, 10, 25, 5),
                submit_time=datetime(2023, 9, 8, 10, 24, 43),
            ),
        ]

        expected_jinja_list = [
            job.jinja_dict for job in expected_job_status_list
        ]

        self.assertEqual(expected_job_status_list, job_status_list)
        self.assertEqual(expected_jinja_list, jinja_list)
