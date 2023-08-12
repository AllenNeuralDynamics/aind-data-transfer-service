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
    ModalityConfigs,
)
from aind_data_transfer_service.configs.server_configs import (
    EndpointConfigs,
    ServerConfigs,
)

RESOURCES_DIR = Path(os.path.dirname(os.path.realpath(__file__))) / "resources"
SAMPLE_FILE = RESOURCES_DIR / "sample.csv"


class TestServerConfigs(unittest.TestCase):
    EXAMPLE_ENV_VAR1 = {
        "HPC_USERNAME": "hpc_user",
        "HPC_PASSWORD": "hpc_password",
        "HPC_TOKEN": "hpc_jwt",
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
        endpoint_configs = EndpointConfigs.from_server_configs(
            server_configs=server_configs
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
        self.assertIsNone(endpoint_configs.codeocean_process_capsule_id)


class TestJobConfigs(unittest.TestCase):
    expected_job_configs = [
        BasicUploadJobConfigs(
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
            behavior_dir=None,
            metadata_dir=None,
            log_level="WARNING",
            metadata_dir_force=False,
            dry_run=False,
            force_cloud_sync=False,
        ),
        BasicUploadJobConfigs(
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
            behavior_dir=None,
            metadata_dir=None,
            log_level="WARNING",
            metadata_dir_force=False,
            dry_run=False,
            force_cloud_sync=False,
        ),
    ]

    def test_parse_csv_file(self):
        jobs = []

        with open(SAMPLE_FILE, newline="") as csvfile:
            reader = csv.DictReader(csvfile, skipinitialspace=True)
            for row in reader:
                jobs.append(BasicUploadJobConfigs.from_csv_row(row))
        self.assertEqual(self.expected_job_configs, jobs)


if __name__ == "__main__":
    unittest.main()
