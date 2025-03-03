"""Tests methods in csv_handler module"""
import csv
import os
import unittest
from datetime import datetime
from pathlib import Path, PurePosixPath

from aind_data_schema_models.modalities import Modality
from aind_data_schema_models.platforms import Platform
from aind_data_transfer_models.core import (
    BasicUploadJobConfigs,
    CodeOceanPipelineMonitorConfigs,
    ModalityConfigs,
)

from aind_data_transfer_service.configs.csv_handler import map_csv_row_to_job

RESOURCES_DIR = Path(os.path.dirname(os.path.realpath(__file__))) / "resources"
SAMPLE_FILE = RESOURCES_DIR / "new_sample.csv"


class TestCsvHandler(unittest.TestCase):
    """Tests methods in csv_handler module"""

    def test_map_csv_row_to_job(self):
        """Tests map_csv_row_to_job method"""

        jobs = []
        with open(SAMPLE_FILE, newline="") as csvfile:
            reader = csv.DictReader(csvfile, skipinitialspace=True)
            for row in reader:
                jobs.append(map_csv_row_to_job(row))

        expected_jobs = [
            BasicUploadJobConfigs(
                project_name="Ephys Platform",
                process_capsule_id=None,
                s3_bucket="default",
                platform=Platform.ECEPHYS,
                modalities=[
                    ModalityConfigs(
                        modality=Modality.ECEPHYS,
                        source=PurePosixPath("dir/data_set_1"),
                        compress_raw_data=True,
                        extra_configs=None,
                        slurm_settings=None,
                    )
                ],
                subject_id="123454",
                acq_datetime=datetime(2020, 10, 10, 14, 10, 10),
                metadata_dir=None,
                metadata_dir_force=None,
                force_cloud_sync=False,
            ),
            BasicUploadJobConfigs(
                project_name="Behavior Platform",
                process_capsule_id="1f999652-00a0-4c4b-99b5-64c2985ad070",
                s3_bucket="open",
                platform=Platform.BEHAVIOR,
                modalities=[
                    ModalityConfigs(
                        modality=Modality.BEHAVIOR_VIDEOS,
                        source=PurePosixPath("dir/data_set_2"),
                        compress_raw_data=False,
                        extra_configs=None,
                        slurm_settings=None,
                    ),
                    ModalityConfigs(
                        modality=Modality.MRI,
                        source=PurePosixPath("dir/data_set_3"),
                        compress_raw_data=False,
                        extra_configs=None,
                        slurm_settings=None,
                    ),
                ],
                subject_id="123456",
                acq_datetime=datetime(2020, 10, 13, 13, 10, 10),
                metadata_dir=None,
                metadata_dir_force=None,
                force_cloud_sync=False,
                codeocean_configs=CodeOceanPipelineMonitorConfigs(
                    job_type="custom"
                ),
            ),
            BasicUploadJobConfigs(
                project_name="Behavior Platform",
                process_capsule_id=None,
                s3_bucket="scratch",
                platform=Platform.BEHAVIOR,
                modalities=[
                    ModalityConfigs(
                        modality=Modality.BEHAVIOR_VIDEOS,
                        source=PurePosixPath("dir/data_set_2"),
                        compress_raw_data=False,
                        extra_configs=None,
                        slurm_settings=None,
                    )
                ],
                subject_id="123456",
                acq_datetime=datetime(2020, 10, 13, 13, 10, 10),
                metadata_dir=None,
                metadata_dir_force=None,
                force_cloud_sync=False,
            ),
        ]
        self.assertEqual(expected_jobs, jobs)


if __name__ == "__main__":
    unittest.main()
