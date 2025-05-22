"""Tests methods in csv_handler module"""

import csv
import os
import unittest
from datetime import datetime
from pathlib import Path

from aind_data_schema_models.modalities import Modality
from aind_data_schema_models.platforms import Platform

from aind_data_transfer_service.configs.csv_handler import map_csv_row_to_job
from aind_data_transfer_service.models.core import Task, UploadJobConfigsV2

RESOURCES_DIR = Path(os.path.dirname(os.path.realpath(__file__))) / "resources"
SAMPLE_FILE = RESOURCES_DIR / "new_sample.csv"
LEGACY_FILE = RESOURCES_DIR / "legacy_sample.csv"
LEGACY_FILE_2 = RESOURCES_DIR / "legacy_sample2.csv"


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
            UploadJobConfigsV2(
                project_name="Ephys Platform",
                s3_bucket="default",
                platform=Platform.ECEPHYS,
                modalities=[Modality.ECEPHYS],
                tasks={
                    "gather_preliminary_metadata": Task(
                        job_settings={"metadata_dir": "dir/metadata"}
                    ),
                    "modality_transformation_settings": {
                        Modality.ECEPHYS.abbreviation: Task(
                            job_settings={"input_source": "dir/data_set_1"}
                        )
                    },
                },
                subject_id="123454",
                acq_datetime=datetime(2020, 10, 10, 14, 10, 10),
                job_type="ecephys",
            ),
            UploadJobConfigsV2(
                project_name="Behavior Platform",
                s3_bucket="open",
                platform=Platform.BEHAVIOR,
                modalities=[Modality.BEHAVIOR_VIDEOS, Modality.MRI],
                tasks={
                    "modality_transformation_settings": {
                        Modality.BEHAVIOR_VIDEOS.abbreviation: Task(
                            job_settings={"input_source": "dir/data_set_2"}
                        ),
                        Modality.MRI.abbreviation: Task(
                            job_settings={"input_source": "dir/data_set_3"}
                        ),
                    }
                },
                subject_id="123456",
                acq_datetime=datetime(2020, 10, 13, 13, 10, 10),
                job_type="custom",
            ),
            UploadJobConfigsV2(
                project_name="Behavior Platform",
                platform=Platform.BEHAVIOR,
                modalities=[Modality.BEHAVIOR_VIDEOS],
                tasks={
                    "modality_transformation_settings": {
                        Modality.BEHAVIOR_VIDEOS.abbreviation: Task(
                            job_settings={"input_source": "dir/data_set_2"}
                        )
                    }
                },
                subject_id="123456",
                acq_datetime=datetime(2020, 10, 13, 13, 10, 10),
                job_type="default",
            ),
        ]
        self.assertEqual(expected_jobs, jobs)

    def test_map_legacy_csv_row_to_job(self):
        """Tests map_csv_row_to_job method"""

        jobs = []
        with open(LEGACY_FILE, newline="") as csvfile:
            reader = csv.DictReader(csvfile, skipinitialspace=True)
            for row in reader:
                jobs.append(map_csv_row_to_job(row))
        expected_jobs = [
            UploadJobConfigsV2(
                job_type="default",
                s3_bucket="private",
                project_name="Ephys Platform",
                platform=Platform.ECEPHYS,
                modalities=[Modality.ECEPHYS],
                subject_id="123454",
                acq_datetime=datetime(2020, 10, 10, 14, 10, 10),
                tasks={
                    "check_s3_folder_exists_task": Task(
                        skip_task=True,
                    ),
                    "final_check_s3_folder_exist": Task(
                        skip_task=True,
                    ),
                    "modality_transformation_settings": {
                        "ecephys": Task(
                            skip_task=False,
                            job_settings={"input_source": "dir/data_set_1"},
                        )
                    },
                },
                s3_prefix="ecephys_123454_2020-10-10_14-10-10",
            ),
            UploadJobConfigsV2(
                job_type="default",
                s3_bucket="open",
                project_name="Behavior Platform",
                platform=Platform.BEHAVIOR,
                modalities=[Modality.BEHAVIOR_VIDEOS, Modality.MRI],
                subject_id="123456",
                acq_datetime=datetime(2020, 10, 13, 13, 10, 10),
                tasks={
                    "modality_transformation_settings": {
                        "behavior-videos": Task(
                            skip_task=False,
                            job_settings={"input_source": "dir/data_set_2"},
                        ),
                        "MRI": Task(
                            skip_task=False,
                            job_settings={"input_source": "dir/data_set_3"},
                        ),
                    },
                    "codeocean_pipeline_settings": {
                        "behavior-videos": Task(
                            skip_task=False,
                            job_settings={
                                "pipeline_monitor_settings": {
                                    "run_params": {
                                        "capsule_id": (
                                            "1f999652-00a0-4c4b-99b5-"
                                            "64c2985ad070"
                                        )
                                    }
                                }
                            },
                        )
                    },
                },
                s3_prefix="behavior_123456_2020-10-13_13-10-10",
            ),
            UploadJobConfigsV2(
                job_type="default",
                s3_bucket="default",
                project_name="Behavior Platform",
                platform=Platform.BEHAVIOR,
                modalities=[Modality.BEHAVIOR_VIDEOS],
                subject_id="123456",
                acq_datetime=datetime(2020, 10, 13, 13, 10, 10),
                tasks={
                    "modality_transformation_settings": {
                        "behavior-videos": Task(
                            skip_task=False,
                            job_settings={"input_source": "dir/data_set_3"},
                        )
                    }
                },
                s3_prefix="behavior_123456_2020-10-13_13-10-10",
            ),
        ]

        self.assertEqual(expected_jobs, jobs)

    def test_map_old_csv_row_to_job(self):
        """Tests map_csv_row_to_job method"""

        jobs = []
        with open(LEGACY_FILE_2, newline="") as csvfile:
            reader = csv.DictReader(csvfile, skipinitialspace=True)
            for row in reader:
                jobs.append(map_csv_row_to_job(row))
        expected_jobs = [
            UploadJobConfigsV2(
                job_type="default",
                s3_bucket="open",
                project_name="Behavior Platform",
                platform=Platform.BEHAVIOR,
                modalities=[
                    Modality.BEHAVIOR_VIDEOS,
                    Modality.MRI,
                ],
                subject_id="123456",
                acq_datetime=datetime(2020, 10, 13, 13, 10, 10),
                tasks={
                    "modality_transformation_settings": {
                        "behavior-videos": Task(
                            skip_task=False,
                            job_settings={"input_source": "dir/data_set_2"},
                        ),
                        "MRI": Task(
                            skip_task=False,
                            job_settings={"input_source": "dir/data_set_3"},
                        ),
                    },
                    "codeocean_pipeline_settings": {
                        "behavior-videos": Task(
                            skip_task=False,
                            job_settings={
                                "pipeline_monitor_settings": {
                                    "run_params": {
                                        "pipeline_id": (
                                            "1f999652-00a0-4c4b-99b5-"
                                            "64c2985ad070"
                                        )
                                    }
                                }
                            },
                        )
                    },
                },
                s3_prefix="behavior_123456_2020-10-13_13-10-10",
            )
        ]

        self.assertEqual(expected_jobs, jobs)


if __name__ == "__main__":
    unittest.main()
