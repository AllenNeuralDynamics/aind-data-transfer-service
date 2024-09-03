"""Module to test configs"""

import csv
import os
import unittest
from datetime import datetime
from pathlib import Path, PurePosixPath

from aind_data_schema_models.modalities import Modality
from aind_data_schema_models.platforms import Platform
from aind_data_schema_models.process_names import ProcessName

from aind_data_transfer_service.configs.job_configs import (
    BasicUploadJobConfigs,
    HpcJobConfigs,
    ModalityConfigs,
)

RESOURCES_DIR = Path(os.path.dirname(os.path.realpath(__file__))) / "resources"
SAMPLE_FILE = RESOURCES_DIR / "sample.csv"
SAMPLE_ALT_MODALITY_CASE_FILE = RESOURCES_DIR / "sample_alt_modality_case.csv"


class TestJobConfigs(unittest.TestCase):
    """Tests basic job configs class"""

    expected_job_configs = [
        BasicUploadJobConfigs(
            aws_param_store_name="/some/param/store",
            project_name="Ephys Platform",
            process_capsule_id=None,
            s3_bucket="private",
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
        ),
        BasicUploadJobConfigs(
            aws_param_store_name="/some/param/store",
            project_name="Behavior Platform",
            process_capsule_id="1f999652-00a0-4c4b-99b5-64c2985ad070",
            s3_bucket="open",
            platform=Platform.BEHAVIOR,
            modalities=[
                ModalityConfigs(
                    modality=Modality.BEHAVIOR_VIDEOS,
                    source=(PurePosixPath("dir") / "data_set_2"),
                    compress_raw_data=False,
                    extra_configs=None,
                    skip_staging=False,
                ),
                ModalityConfigs(
                    modality=Modality.MRI,
                    source=(PurePosixPath("dir") / "data_set_3"),
                    compress_raw_data=False,
                    extra_configs=None,
                    skip_staging=False,
                ),
            ],
            subject_id="123456",
            acq_datetime=datetime(2020, 10, 13, 13, 10, 10),
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
            project_name="Behavior Platform",
            process_capsule_id=None,
            s3_bucket="scratch",
            platform=Platform.BEHAVIOR,
            modalities=[
                ModalityConfigs(
                    modality=Modality.BEHAVIOR_VIDEOS,
                    source=(PurePosixPath("dir") / "data_set_2"),
                    compress_raw_data=False,
                    extra_configs=None,
                    skip_staging=False,
                ),
                ModalityConfigs(
                    modality=Modality.BEHAVIOR_VIDEOS,
                    source=(PurePosixPath("dir") / "data_set_3"),
                    compress_raw_data=False,
                    extra_configs=None,
                    skip_staging=False,
                ),
            ],
            subject_id="123456",
            acq_datetime=datetime(2020, 10, 13, 13, 10, 10),
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
            ("behavior_123456_2020-10-13_13-10-10", "behavior-videos", None),
            ("behavior_123456_2020-10-13_13-10-10", "MRI", None),
            ("behavior_123456_2020-10-13_13-10-10", "behavior-videos", None),
            ("behavior_123456_2020-10-13_13-10-10", "behavior-videos1", 1),
        ]
        self.assertEqual(self.expected_job_configs, jobs)
        self.assertEqual(expected_modality_outputs, modality_outputs)

        # Tests validation errors are raised if acq_datetime is
        # not formatted correctly
        with self.assertRaises(Exception) as e1:
            BasicUploadJobConfigs(
                project_name="Behavior Platform",
                s3_bucket="",
                platform=Platform.BEHAVIOR,
                modalities=[Modality.BEHAVIOR_VIDEOS],
                subject_id="12345",
                acq_datetime="1234",
            )

        self.assertTrue(
            (
                "Incorrect datetime format, should be YYYY-MM-DD HH:mm:ss "
                "or MM/DD/YYYY I:MM:SS P"
            )
            in repr(e1.exception)
        )

        # Tests clean_csv_entry returns a default if None
        self.assertEqual(
            BasicUploadJobConfigs.model_fields["log_level"].default,
            BasicUploadJobConfigs._clean_csv_entry(
                csv_key="log_level", csv_value=None
            ),
        )

    def test_parse_alt_csv_file(self):
        """Tests that the jobs can be parsed from a csv file correctly where
        the modalities are lower case."""

        jobs = []

        with open(SAMPLE_ALT_MODALITY_CASE_FILE, newline="") as csvfile:
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
            ("behavior_123456_2020-10-13_13-10-10", "behavior-videos", None),
            ("behavior_123456_2020-10-13_13-10-10", "MRI", None),
            ("behavior_123456_2020-10-13_13-10-10", "behavior-videos", None),
            ("behavior_123456_2020-10-13_13-10-10", "behavior-videos1", 1),
        ]
        self.assertEqual(self.expected_job_configs, jobs)
        self.assertEqual(expected_modality_outputs, modality_outputs)

    def test_malformed_platform(self):
        """Tests that an error is raised if an unknown platform is used"""

        with self.assertRaises(AttributeError) as e:
            BasicUploadJobConfigs(
                aws_param_store_name="/some/param/store",
                project_name="Behavior Platform",
                s3_bucket="some_bucket2",
                platform="MISSING",
                modalities=[
                    ModalityConfigs(
                        modality=Modality.BEHAVIOR_VIDEOS,
                        source=(PurePosixPath("dir") / "data_set_2"),
                        compress_raw_data=False,
                        extra_configs=None,
                        skip_staging=False,
                    ),
                ],
                subject_id="123456",
                acq_datetime=datetime(2020, 10, 13, 13, 10, 10),
                process_name=ProcessName.OTHER,
                temp_directory=None,
                metadata_dir=None,
                log_level="WARNING",
                metadata_dir_force=False,
                dry_run=False,
                force_cloud_sync=False,
            )
        self.assertEqual(
            "AttributeError('Unknown Platform: MISSING')", repr(e.exception)
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
            hpc_sif_location=PurePosixPath("sif_location"),
            hpc_current_working_directory=PurePosixPath("hpc_cwd"),
            hpc_logging_directory=PurePosixPath("hpc_logs"),
            basic_upload_job_configs=job_configs,
        )
        job_name = hpc_configs._job_name()
        self.assertEqual("ecephys_123454_2020-10-10_14-10-10", job_name)

    def test_from_job_and_server_configs(self):
        """Tests hpc configs are computed correctly"""

        job_configs = TestJobConfigs.expected_job_configs[0]
        hpc_configs = HpcJobConfigs(
            hpc_partition="hpc_part",
            hpc_aws_secret_access_key="zxcvbnm",
            hpc_aws_access_key_id="abc-123",
            hpc_aws_session_token="token-42gfwq4",
            hpc_aws_default_region="us-west-2",
            hpc_sif_location=PurePosixPath("sif_location"),
            hpc_current_working_directory=PurePosixPath("hpc_cwd"),
            hpc_logging_directory=PurePosixPath("hpc_logs"),
            basic_upload_job_configs=job_configs,
        )
        hpc_configs2 = HpcJobConfigs(
            **hpc_configs.model_dump(exclude_none=True),
            hpc_alt_exec_command="#!/bin/bash \necho Hello",
        )

        expected_job_def = {
            "job": {
                "name": "ecephys_123454_2020-10-10_14-10-10",
                "nodes": 1,
                "time_limit": "06:00:00",
                "partition": "hpc_part",
                "current_working_directory": "hpc_cwd",
                "standard_output": (
                    "hpc_logs/ecephys_123454_2020-10-10_14-10-10.out"
                ),
                "standard_error": (
                    "hpc_logs/ecephys_123454_2020-10-10_14-10-10_error.out"
                ),
                "memory_per_node": "50gb",
                "environment": {
                    "PATH": "/bin:/usr/bin/:/usr/local/bin/",
                    "LD_LIBRARY_PATH": "/lib/:/lib64/:/usr/local/lib",
                    "SINGULARITYENV_AWS_SECRET_ACCESS_KEY": "zxcvbnm",
                    "SINGULARITYENV_AWS_ACCESS_KEY_ID": "abc-123",
                    "SINGULARITYENV_AWS_DEFAULT_REGION": "us-west-2",
                    "SINGULARITYENV_AWS_SESSION_TOKEN": "token-42gfwq4",
                },
            },
            "script": (
                "#!/bin/bash \nsingularity exec"
                " --cleanenv sif_location"
                " python -m aind_data_transfer.jobs.basic_job"
                " --json-args ' "
                '{"aws_param_store_name":"/some/param/store",'
                '"project_name":"Ephys Platform",'
                '"process_capsule_id":null,'
                '"s3_bucket":"private",'
                '"platform":{"name":"Electrophysiology platform",'
                '"abbreviation":"ecephys"},'
                '"modalities":[{"modality":'
                '{"name":"Extracellular electrophysiology",'
                '"abbreviation":"ecephys"},'
                '"source":"dir/data_set_1",'
                '"compress_raw_data":true,'
                '"extra_configs":null,'
                '"skip_staging":false}],'
                '"subject_id":"123454",'
                '"acq_datetime":"2020-10-10T14:10:10",'
                '"process_name":"Other",'
                '"metadata_dir":null,'
                '"behavior_dir":null,'
                '"log_level":"WARNING",'
                '"metadata_dir_force":false,'
                '"dry_run":false,'
                '"force_cloud_sync":false,'
                '"temp_directory":null} \''
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
