"""Module to test configs"""

import csv
import os
import unittest
from datetime import date, time
from pathlib import Path
from unittest.mock import MagicMock, patch

from aind_data_schema.data_description import ExperimentType, Modality
from aind_data_schema.processing import ProcessName

from aind_data_transfer_service.configs.job_configs import (
    BasicUploadJobConfigs,
    HpcJobConfigs,
    ModalityConfigs,
)

RESOURCES_DIR = Path(os.path.dirname(os.path.realpath(__file__))) / "resources"
SAMPLE_FILE = RESOURCES_DIR / "sample.csv"


class TestJobConfigs(unittest.TestCase):
    """Tests basic job configs class"""

    expected_job_configs = [
        BasicUploadJobConfigs(
            aws_param_store_name="/some/param/store",
            s3_bucket="some_bucket",
            experiment_type=ExperimentType.ECEPHYS,
            modalities=[
                ModalityConfigs(
                    modality=Modality.ECEPHYS,
                    source=Path("dir/data_set_1"),
                    compress_raw_data=True,
                    extra_configs=None,
                    skip_staging=False,
                )
            ],
            subject_id="123454",
            acq_date=date(2020, 10, 10),
            acq_time=time(14, 10, 10),
            process_name=ProcessName.OTHER,
            temp_directory=None,
            metadata_dir=None,
            log_level="WARNING",
            metadata_dir_force=False,
            dry_run=False,
            force_cloud_sync=False,
        ),
        BasicUploadJobConfigs(
            aws_param_store_name="/some/param/store",
            s3_bucket="some_bucket2",
            experiment_type=ExperimentType.OTHER,
            modalities=[
                ModalityConfigs(
                    modality=Modality.OPHYS,
                    source=Path("dir/data_set_2"),
                    compress_raw_data=False,
                    extra_configs=None,
                    skip_staging=False,
                ),
                ModalityConfigs(
                    modality=Modality.MRI,
                    source=Path("dir/data_set_3"),
                    compress_raw_data=False,
                    extra_configs=None,
                    skip_staging=False,
                ),
            ],
            subject_id="123456",
            acq_date=date(2020, 10, 13),
            acq_time=time(13, 10, 10),
            process_name=ProcessName.OTHER,
            temp_directory=None,
            metadata_dir=None,
            log_level="WARNING",
            metadata_dir_force=False,
            dry_run=False,
            force_cloud_sync=False,
        ),
        BasicUploadJobConfigs(
            aws_param_store_name="/some/param/store",
            s3_bucket="some_bucket2",
            experiment_type=ExperimentType.OTHER,
            modalities=[
                ModalityConfigs(
                    modality=Modality.OPHYS,
                    source=Path("dir/data_set_2"),
                    compress_raw_data=False,
                    extra_configs=None,
                    skip_staging=False,
                ),
                ModalityConfigs(
                    modality=Modality.OPHYS,
                    source=Path("dir/data_set_3"),
                    compress_raw_data=False,
                    extra_configs=None,
                    skip_staging=False,
                ),
            ],
            subject_id="123456",
            acq_date=date(2020, 10, 13),
            acq_time=time(13, 10, 10),
            process_name=ProcessName.OTHER,
            temp_directory=None,
            metadata_dir=None,
            log_level="WARNING",
            metadata_dir_force=False,
            dry_run=False,
            force_cloud_sync=False,
        ),
    ]

    def test_parse_csv_file(self):
        """Tests that the jobs can be parsed from a csv file correctly."""

        jobs = []

        with open(SAMPLE_FILE, newline="") as csvfile:
            reader = csv.DictReader(csvfile, skipinitialspace=True)
            for row in reader:
                jobs.append(
                    BasicUploadJobConfigs.from_csv_row(
                        row, aws_param_store_name="/some/param/store"
                    )
                )

        modality_outputs = []
        for job in jobs:
            job_s3_prefix = job.s3_prefix
            for modality in job.modalities:
                modality_outputs.append(
                    (
                        job_s3_prefix,
                        modality.default_output_folder_name,
                        modality.number_id,
                    )
                )
        expected_modality_outputs = [
            ("ecephys_123454_2020-10-10_14-10-10", "ecephys", None),
            ("Other_123456_2020-10-13_13-10-10", "ophys", None),
            ("Other_123456_2020-10-13_13-10-10", "mri", None),
            ("Other_123456_2020-10-13_13-10-10", "ophys", None),
            ("Other_123456_2020-10-13_13-10-10", "ophys1", 1),
        ]
        self.assertEqual(self.expected_job_configs, jobs)
        self.assertEqual(expected_modality_outputs, modality_outputs)

        # Tests validation errors are raised if acq_date and acq_time are
        # not formatted correctly
        with self.assertRaises(Exception) as e1:
            BasicUploadJobConfigs(
                s3_bucket="",
                experiment_type=ExperimentType.OTHER,
                modalities=[],
                subject_id="12345",
                acq_date="1234",
                acq_time="1234",
            )

        self.assertTrue(
            "Incorrect date format, should be YYYY-MM-DD or MM/DD/YYYY"
            in repr(e1.exception)
        )
        self.assertTrue(
            "Incorrect time format, should be HH-MM-SS or HH:MM:SS"
            in repr(e1.exception)
        )

        # Tests clean_csv_entry returns a default if None
        self.assertEqual(
            BasicUploadJobConfigs.__fields__["log_level"].default,
            BasicUploadJobConfigs._clean_csv_entry(
                csv_key="log_level", csv_value=None
            ),
        )


class TestHpcConfigs(unittest.TestCase):
    """Tests methods in HpcConfigs class"""

    def test_job_name_creation(self):
        """Tests that the job name is created correctly"""
        job_configs = TestJobConfigs.expected_job_configs[0]
        hpc_configs = HpcJobConfigs(
            hpc_partition="hpc_part",
            hpc_aws_secret_access_key="zxcvbnm",
            hpc_aws_access_key_id="abc-123",
            hpc_aws_default_region="us-west-2",
            hpc_sif_location=Path("sif_location"),
            hpc_current_working_directory=Path("hpc_cwd"),
            hpc_logging_directory=Path("hpc_logs"),
            basic_upload_job_configs=job_configs,
        )
        job_name = hpc_configs._job_name()
        self.assertTrue(job_name.startswith("job_"))
        self.assertEqual(16, len(job_name))

    @patch(
        "aind_data_transfer_service.configs.job_configs.HpcJobConfigs."
        "_job_name"
    )
    def test_from_job_and_server_configs(self, mock_name: MagicMock):
        """Tests hpc configs are computed correctly"""

        mock_name.return_value = "some_job_name"

        job_configs = TestJobConfigs.expected_job_configs[0]
        hpc_configs = HpcJobConfigs(
            hpc_partition="hpc_part",
            hpc_aws_secret_access_key="zxcvbnm",
            hpc_aws_access_key_id="abc-123",
            hpc_aws_session_token="token-42gfwq4",
            hpc_aws_default_region="us-west-2",
            hpc_sif_location=Path("sif_location"),
            hpc_current_working_directory=Path("hpc_cwd"),
            hpc_logging_directory=Path("hpc_logs"),
            basic_upload_job_configs=job_configs,
        )
        hpc_configs2 = HpcJobConfigs(
            **hpc_configs.dict(exclude_none=True),
            hpc_alt_exec_command="#!/bin/bash \necho Hello",
        )

        expected_job_def = {
            "job": {
                "name": "some_job_name",
                "nodes": 1,
                "time_limit": "06:00:00",
                "partition": "hpc_part",
                "current_working_directory": "hpc_cwd",
                "standard_output": str(Path("hpc_logs") / "some_job_name.out"),
                "standard_error": str(
                    Path("hpc_logs") / "some_job_name_error.out"
                ),
                "memory_per_node": "50gb",
                "environment": (
                    {
                        "PATH": "/bin:/usr/bin/:/usr/local/bin/",
                        "LD_LIBRARY_PATH": "/lib/:/lib64/:/usr/local/lib",
                        "SINGULARITYENV_AWS_SECRET_ACCESS_KEY": "zxcvbnm",
                        "SINGULARITYENV_AWS_ACCESS_KEY_ID": "abc-123",
                        "SINGULARITYENV_AWS_DEFAULT_REGION": "us-west-2",
                        "SINGULARITYENV_AWS_SESSION_TOKEN": "token-42gfwq4",
                    }
                ),
            },
            "script": (
                "#!/bin/bash \nsingularity exec --cleanenv sif_location python"
                " -m aind_data_transfer.jobs.basic_job --json-args '"
                ' {"aws_param_store_name": "/some/param/store",'
                ' "s3_bucket": "some_bucket",'
                ' "experiment_type": "ecephys",'
                ' "modalities": [{"modality":'
                ' {"name": "Extracellular electrophysiology",'
                ' "abbreviation": "ecephys"},'
                ' "source": "dir/data_set_1",'
                ' "compress_raw_data": true, "extra_configs": null,'
                ' "skip_staging": false}],'
                ' "subject_id": "123454", "acq_date": "2020-10-10",'
                ' "acq_time": "14:10:10", "process_name": "Other",'
                ' "metadata_dir": null, "behavior_dir": null,'
                ' "log_level": "WARNING", "metadata_dir_force": false,'
                ' "dry_run": false, "force_cloud_sync": false,'
                ' "temp_directory": null} \''
            ),
        }

        expected_alt_job_def = {
            "job": expected_job_def["job"],
            "script": "#!/bin/bash \necho Hello",
        }

        self.assertEqual(expected_job_def, hpc_configs.job_definition)
        self.assertEqual(
            expected_alt_job_def,
            hpc_configs2.job_definition,
        )
        self.assertEqual(1, hpc_configs.hpc_nodes)
        self.assertEqual(360, hpc_configs.hpc_time_limit)
        self.assertEqual(50, hpc_configs.hpc_node_memory)
        self.assertEqual("hpc_part", hpc_configs.hpc_partition)


if __name__ == "__main__":
    unittest.main()
