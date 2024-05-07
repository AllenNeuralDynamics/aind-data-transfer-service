"""Module to test hpc client classes"""

import json
import os
import unittest
from datetime import datetime
from pathlib import Path, PurePosixPath
from unittest.mock import patch

from aind_data_schema.models.modalities import Modality
from aind_data_schema.models.platforms import Platform
from aind_data_schema.models.process_names import ProcessName
from pydantic import SecretStr

from aind_data_transfer_service.configs.job_configs import (
    BasicUploadJobConfigs,
    ModalityConfigs,
)
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
            HpcJobStatusResponse.model_validate(job_json)
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
                end_time=datetime.utcfromtimestamp(1694220246),
                job_id=10994495,
                job_state="RUNNING",
                name="bash",
                comment="",
                start_time=datetime.utcfromtimestamp(1693788246),
                submit_time=datetime.utcfromtimestamp(1693788246),
            ),
            JobStatus(
                end_time=datetime.utcfromtimestamp(1694194372),
                job_id=11005019,
                job_state="TIMEOUT",
                name="my_job_name",
                comment="",
                start_time=datetime.utcfromtimestamp(1694095962),
                submit_time=datetime.utcfromtimestamp(1693963194),
            ),
            JobStatus(
                end_time=None,
                job_id=11005059,
                job_state="PENDING",
                name="analysis.job",
                comment="",
                start_time=None,
                submit_time=datetime.utcfromtimestamp(1694096713),
            ),
            JobStatus(
                end_time=datetime.utcfromtimestamp(1694194337),
                job_id=11013427,
                job_state="COMPLETED",
                name="some_job_2",
                comment="",
                start_time=datetime.utcfromtimestamp(1694193905),
                submit_time=datetime.utcfromtimestamp(1694040232),
            ),
            JobStatus(
                end_time=datetime.utcfromtimestamp(1694194257),
                job_id=11013479,
                job_state="FAILED",
                name="some_command_job",
                comment="",
                start_time=datetime.utcfromtimestamp(1694194237),
                submit_time=datetime.utcfromtimestamp(1694194237),
            ),
            JobStatus(
                end_time=datetime.utcfromtimestamp(1694194147),
                job_id=11013426,
                job_state="OUT_OF_MEMORY",
                name="JOB_NAME",
                comment="",
                start_time=datetime.utcfromtimestamp(1694193905),
                submit_time=datetime.utcfromtimestamp(1694193883),
            ),
        ]

        expected_jinja_list = [
            job.jinja_dict for job in expected_job_status_list
        ]

        expected_job_status_list.sort(
            key=lambda x: x.submit_time, reverse=True
        )
        expected_jinja_list.sort(key=lambda x: x["submit_time"], reverse=True)
        self.assertEqual(expected_job_status_list[0], job_status_list[0])
        self.assertEqual(expected_jinja_list, jinja_list)


class TestJobSubmit(unittest.TestCase):
    """Tests job submit model"""

    @patch.dict(os.environ, {"HPC_NAME": "foobar"}, clear=True)
    def test_hpc_job_submit_model(self):
        """Tests that the hpc job submit settings are set correctly."""
        hpc_job_submit_settings = HpcJobSubmitSettings(environment={})
        self.assertEqual("foobar", hpc_job_submit_settings.name)


class TestHpcJobSubmitSettings(unittest.TestCase):
    """Tests methods in HpcJobSubmitSettings class"""

    example_config = BasicUploadJobConfigs(
        aws_param_store_name="/some/param/store",
        project_name="Behavior Platform",
        s3_bucket="some_bucket",
        platform=Platform.ECEPHYS,
        modalities=[
            ModalityConfigs(
                modality=Modality.ECEPHYS,
                source=(PurePosixPath("dir") / "data_set_1"),
                compress_raw_data=True,
                extra_configs=None,
                skip_staging=False,
            )
        ],
        subject_id="123454",
        acq_datetime=datetime(2020, 10, 10, 14, 10, 10),
        process_name=ProcessName.OTHER,
        temp_directory=None,
        metadata_dir=None,
        log_level="WARNING",
        metadata_dir_force=False,
        dry_run=False,
        force_cloud_sync=False,
    )

    @patch.dict(
        os.environ,
        {
            "HPC_PARTITION": "part",
            "HPC_QOS": "production",
            "HPC_TIME_LIMIT": "180",
            "HPC_TASKS": "1",
            "HPC_NODES": "[1, 1]",
            "HPC_MEMORY_PER_CPU": "8000",
            "HPC_SIF_LOCATION": "a/dir/container.sif",
        },
        clear=True,
    )
    def test_from_upload_job_configs(self):
        """Tests from_basic_job_configs class"""
        hpc_settings = HpcJobSubmitSettings.from_upload_job_configs(
            logging_directory=(PurePosixPath("dir") / "logs"),
            aws_secret_access_key=SecretStr("some_secret"),
            aws_access_key_id="some_key",
            aws_default_region="us-west-2",
            aws_session_token=SecretStr("session_token"),
            **{"name": "ecephys_123454_2020-10-10_14-10-10"},
        )
        sif_location = os.getenv("HPC_SIF_LOCATION")
        command_str = hpc_settings.script_command_str(sif_loc_str=sif_location)
        hpc_env = hpc_settings.environment
        self.assertEqual("part", hpc_settings.partition)
        self.assertEqual("production", hpc_settings.qos)
        self.assertEqual(
            "ecephys_123454_2020-10-10_14-10-10", hpc_settings.name
        )
        self.assertEqual(
            str(
                PurePosixPath("dir")
                / "logs"
                / "ecephys_123454_2020-10-10_14-10-10_error.out"
            ),
            hpc_settings.standard_error,
        )
        self.assertEqual(
            str(
                PurePosixPath("dir")
                / "logs"
                / "ecephys_123454_2020-10-10_14-10-10.out"
            ),
            hpc_settings.standard_out,
        )
        self.assertEqual(180, hpc_settings.time_limit)
        self.assertEqual(8000, hpc_settings.memory_per_cpu)
        self.assertEqual(1, hpc_settings.tasks)
        self.assertEqual([1, 1], hpc_settings.nodes)
        self.assertEqual("/bin:/usr/bin/:/usr/local/bin/", hpc_env["PATH"])
        self.assertEqual(
            "/lib/:/lib64/:/usr/local/lib", hpc_env["LD_LIBRARY_PATH"]
        )
        self.assertEqual(
            "some_secret", hpc_env["SINGULARITYENV_AWS_SECRET_ACCESS_KEY"]
        )
        self.assertEqual(
            "some_key", hpc_env["SINGULARITYENV_AWS_ACCESS_KEY_ID"]
        )
        self.assertEqual(
            "us-west-2", hpc_env["SINGULARITYENV_AWS_DEFAULT_REGION"]
        )
        self.assertEqual(
            "session_token", hpc_env["SINGULARITYENV_AWS_SESSION_TOKEN"]
        )
        self.assertEqual(
            (
                "#!/bin/bash \nsingularity exec --cleanenv a/dir/container.sif"
                " python -m aind_data_transfer.jobs.basic_job"
            ),
            command_str,
        )


if __name__ == "__main__":
    unittest.main()
