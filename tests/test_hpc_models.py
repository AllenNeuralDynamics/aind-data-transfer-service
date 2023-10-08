"""Module to test hpc client classes"""

import json
import os
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from aind_data_transfer_service.hpc.models import (
    HpcJobStatusResponse,
    HpcJobSubmitSettings,
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
        job_status_list.sort(key=lambda x: x.submit_time, reverse=True)
        jinja_list.sort(key=lambda x: x["submit_time"], reverse=True)
        expected_job_status_list = [
            JobStatus(
                end_time=datetime.fromtimestamp(1694220246),
                job_id=10994495,
                job_state="RUNNING",
                name="bash",
                start_time=datetime.fromtimestamp(1693788246),
                submit_time=datetime.fromtimestamp(1693788246),
            ),
            JobStatus(
                end_time=datetime.fromtimestamp(1694194372),
                job_id=11005019,
                job_state="TIMEOUT",
                name="my_job_name",
                start_time=datetime.fromtimestamp(1694095962),
                submit_time=datetime.fromtimestamp(1693963194),
            ),
            JobStatus(
                end_time=None,
                job_id=11005059,
                job_state="PENDING",
                name="analysis.job",
                start_time=None,
                submit_time=datetime.fromtimestamp(1694096713),
            ),
            JobStatus(
                end_time=datetime.fromtimestamp(1694194337),
                job_id=11013427,
                job_state="COMPLETED",
                name="some_job_2",
                start_time=datetime.fromtimestamp(1694193905),
                submit_time=datetime.fromtimestamp(1694040232),
            ),
            JobStatus(
                end_time=datetime.fromtimestamp(1694194257),
                job_id=11013479,
                job_state="FAILED",
                name="some_command_job",
                start_time=datetime.fromtimestamp(1694194237),
                submit_time=datetime.fromtimestamp(1694194237),
            ),
            JobStatus(
                end_time=datetime.fromtimestamp(1694194147),
                job_id=11013426,
                job_state="OUT_OF_MEMORY",
                name="JOB_NAME",
                start_time=datetime.fromtimestamp(1694193905),
                submit_time=datetime.fromtimestamp(1694193883),
            ),
        ]

        expected_jinja_list = [
            job.jinja_dict for job in expected_job_status_list
        ]

        expected_job_status_list.sort(
            key=lambda x: x.submit_time, reverse=True
        )
        expected_jinja_list.sort(key=lambda x: x["submit_time"], reverse=True)

        self.assertEqual(expected_job_status_list, job_status_list)
        self.assertEqual(expected_jinja_list, jinja_list)


class TestJobSubmit(unittest.TestCase):
    """Tests job submit model"""

    @patch.dict(os.environ, {"HPC_NAME": "foobar"}, clear=True)
    def test_hpc_job_submit_model(self):
        """Tests that the hpc job submit settings are set correctly."""
        hpc_job_submit_settings = HpcJobSubmitSettings(environment=[])
        self.assertEqual("foobar", hpc_job_submit_settings.name)


if __name__ == "__main__":
    unittest.main()
