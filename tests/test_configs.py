"""Module to test configs"""

import csv
import json
import os
import unittest
from datetime import date, time
from pathlib import Path
from unittest.mock import MagicMock, patch

from aind_data_schema.data_description import ExperimentType, Modality
from aind_data_schema.processing import ProcessName

from aind_data_transfer_service.configs.job_configs import (
    BasicUploadJobConfigs,
    EndpointConfigs,
    HpcJobConfigs,
    ModalityConfigs,
)
from aind_data_transfer_service.configs.server_configs import ServerConfigs

RESOURCES_DIR = Path(os.path.dirname(os.path.realpath(__file__))) / "resources"
SAMPLE_FILE = RESOURCES_DIR / "sample.csv"


class TestServerConfigs(unittest.TestCase):
    """Tests ServerConfigs class"""

    EXAMPLE_ENV_VAR1 = {
        "HPC_USERNAME": "hpc_user",
        "HPC_PASSWORD": "hpc_password",
        "HPC_TOKEN": "hpc_jwt",
        "HPC_PARTITION": "hpc_part",
        "AWS_ACCESS_KEY": "aws_key",
        "AWS_SECRET_ACCESS_KEY": "aws_secret_key",
        "AWS_REGION": "aws_region",
        "CSRF_SECRET_KEY": "csrf_secret",
        "APP_SECRET_KEY": "app_secret",
        "AWS_ENDPOINTS_PARAM_STORE_NAME": "aws/env/param/store",
        "AWS_CODEOCEAN_TOKEN_SECRETS_NAME": "aws/env/secret/codeocean",
        "AWS_VIDEO_ENCRYPTION_PASSWORD_NAME": "aws/env/secret/vid/encrypt",
    }

    @patch.dict(os.environ, EXAMPLE_ENV_VAR1, clear=True)
    def test_server_configs_env_vars(self):
        """Tests that the server configs can be set from env vars"""
        server_configs = ServerConfigs()
        self.assertEqual("hpc_user", server_configs.hpc_username)
        self.assertEqual(
            "hpc_password", server_configs.hpc_password.get_secret_value()
        )
        self.assertEqual(
            "hpc_jwt", server_configs.hpc_token.get_secret_value()
        )
        self.assertEqual("hpc_part", server_configs.hpc_partition)
        self.assertEqual("aws_key", server_configs.aws_access_key)
        self.assertEqual(
            "aws_secret_key",
            server_configs.aws_secret_access_key.get_secret_value(),
        )
        self.assertEqual("aws_region", server_configs.aws_region)
        self.assertEqual(
            "csrf_secret", server_configs.csrf_secret_key.get_secret_value()
        )
        self.assertEqual(
            "app_secret", server_configs.app_secret_key.get_secret_value()
        )
        self.assertEqual(
            "aws/env/param/store",
            server_configs.aws_endpoints_param_store_name,
        )
        self.assertEqual(
            "aws/env/secret/codeocean",
            server_configs.aws_codeocean_token_secrets_name,
        )
        self.assertEqual(
            "aws/env/secret/vid/encrypt",
            server_configs.aws_video_encryption_password_name,
        )


class TestEndpointConfigs(unittest.TestCase):
    """Tests EndpointConfigs class"""

    EXAMPLE_PARAM_STORE_RESPONSE = json.dumps(
        {
            "codeocean_trigger_capsule_id": "some_capsule_id",
            "metadata_service_domain": "some_ms_domain",
            "aind_data_transfer_repo_location": "some_dtr_location",
        }
    )

    EXAMPLE_CODEOCEAN_SECRETS_RESPONSE = json.dumps(
        {
            "domain": "some_codeocean_domain",
            "token": "some_codeocean_token",
        }
    )

    EXAMPLE_VIDEO_SECRETS_RESPONSE = json.dumps(
        {"password": "some_video_password"}
    )

    @patch.dict(os.environ, TestServerConfigs.EXAMPLE_ENV_VAR1, clear=True)
    @patch("boto3.client")
    def test_resolved_from_env_vars(self, mock_client: MagicMock):
        """Tests that the configs can be resolved from env vars."""
        mock_codeocean_api_token_response = {
            "SecretString": (self.EXAMPLE_CODEOCEAN_SECRETS_RESPONSE)
        }

        mock_video_password_response = {
            "SecretString": self.EXAMPLE_VIDEO_SECRETS_RESPONSE
        }

        mock_client.return_value.get_secret_value.side_effect = [
            mock_codeocean_api_token_response,
            mock_video_password_response,
        ]

        mock_client.return_value.get_parameter.return_value = {
            "Parameter": {"Value": self.EXAMPLE_PARAM_STORE_RESPONSE}
        }

        server_configs = ServerConfigs()
        endpoint_configs = EndpointConfigs.from_aws_params_and_secrets(
            endpoints_param_store_name=(
                server_configs.aws_endpoints_param_store_name
            ),
            codeocean_token_secrets_name=(
                server_configs.aws_codeocean_token_secrets_name
            ),
            video_encryption_password_name=(
                server_configs.aws_video_encryption_password_name
            ),
            temp_directory=server_configs.staging_directory,
        )
        self.assertEqual(
            "some_codeocean_token",
            endpoint_configs.codeocean_api_token.get_secret_value(),
        )
        self.assertEqual(
            "some_video_password",
            endpoint_configs.video_encryption_password.get_secret_value(),
        )
        self.assertEqual(
            "some_codeocean_domain", endpoint_configs.codeocean_domain
        )
        self.assertEqual(
            "some_capsule_id", endpoint_configs.codeocean_trigger_capsule_id
        )
        self.assertIsNone(endpoint_configs.codeocean_trigger_capsule_version)
        self.assertEqual(
            "some_ms_domain", endpoint_configs.metadata_service_domain
        )
        self.assertEqual(
            "some_dtr_location",
            endpoint_configs.aind_data_transfer_repo_location,
        )
        self.assertEqual(
            server_configs.staging_directory, endpoint_configs.temp_directory
        )
        self.assertIsNone(endpoint_configs.codeocean_process_capsule_id)


class TestJobConfigs(unittest.TestCase):
    """Tests basic job configs class"""

    expected_job_configs = [
        BasicUploadJobConfigs(
            codeocean_domain="some_co_domain",
            codeocean_trigger_capsule_id="some_co_cap_id",
            metadata_service_domain="some_msd",
            aind_data_transfer_repo_location="some_dtr",
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
            temp_directory=Path("some_temp_dir"),
            metadata_dir=None,
            log_level="WARNING",
            metadata_dir_force=False,
            dry_run=False,
            force_cloud_sync=False,
        ),
        BasicUploadJobConfigs(
            codeocean_domain="some_co_domain",
            codeocean_trigger_capsule_id="some_co_cap_id",
            metadata_service_domain="some_msd",
            aind_data_transfer_repo_location="some_dtr",
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
            temp_directory=Path("some_temp_dir"),
            metadata_dir=None,
            log_level="WARNING",
            metadata_dir_force=False,
            dry_run=False,
            force_cloud_sync=False,
        ),
        BasicUploadJobConfigs(
            codeocean_domain="some_co_domain",
            codeocean_trigger_capsule_id="some_co_cap_id",
            metadata_service_domain="some_msd",
            aind_data_transfer_repo_location="some_dtr",
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
            temp_directory=Path("some_temp_dir"),
            metadata_dir=None,
            log_level="WARNING",
            metadata_dir_force=False,
            dry_run=False,
            force_cloud_sync=False,
        ),
    ]

    @patch.dict(os.environ, TestServerConfigs.EXAMPLE_ENV_VAR1, clear=True)
    def test_parse_csv_file(self):
        """Tests that the jobs can be parsed from a csv file correctly."""
        endpoint_configs = EndpointConfigs.construct(
            temp_directory="some_temp_dir",
            codeocean_domain="some_co_domain",
            codeocean_trigger_capsule_id="some_co_cap_id",
            metadata_service_domain="some_msd",
            aind_data_transfer_repo_location="some_dtr",
        )

        jobs = []

        with open(SAMPLE_FILE, newline="") as csvfile:
            reader = csv.DictReader(csvfile, skipinitialspace=True)
            for row in reader:
                jobs.append(
                    BasicUploadJobConfigs.from_csv_row(
                        row, endpoints=endpoint_configs
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

    @patch.dict(os.environ, TestServerConfigs.EXAMPLE_ENV_VAR1, clear=True)
    def test_from_job_and_server_configs(self):
        """Tests hpc configs are computed correctly"""
        job_configs = TestJobConfigs.expected_job_configs[0]
        hpc_configs = HpcJobConfigs(
            **job_configs.dict(), hpc_partition="hpc_part"
        )

        self.assertEqual(1, hpc_configs.hpc_n_tasks)
        self.assertEqual(360, hpc_configs.hpc_timeout)
        self.assertEqual(50, hpc_configs.hpc_node_memory)
        self.assertEqual("hpc_part", hpc_configs.hpc_partition)


if __name__ == "__main__":
    unittest.main()
