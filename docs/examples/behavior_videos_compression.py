"""
This example demonstrates how to perform behavior video compression when a
predefined job_type is not available. However, it might be better to request a
job_type to be stored.
"""

from datetime import datetime

import requests
from aind_data_schema_models.modalities import Modality
from aind_data_schema_models.platforms import Platform

from aind_data_transfer_service.models.core import (
    SubmitJobRequestV2,
    Task,
    UploadJobConfigsV2,
)

# As default, behavior videos are not compressed during upload.
# This example demonstrates how to override the default behavior.
job_type = "default"

acq_datetime = datetime(2024, 5, 9, 12, 31, 22)

behavior_task = Task(
    job_settings={
        "input_source": (
            "/allen/aind/scratch/svc_aind_upload/test_data_sets/"
            "behavior_711256_2024-05-09_12-31-22/behavior"
        )
    }
)

# Using a predefined job_type would simplify this model greatly.
# Alternatively, this model can be validated against the JobSettings
# pydantic class in the aind-behavior-video-transformation package.
behavior_video_job_settings = {
    "input_source": (
        "/allen/aind/scratch/svc_aind_upload/test_data_sets/"
        "behavior_711256_2024-05-09_12-31-22/behavior-videos"
    ),
    "output_directory": "%OUTPUT_LOCATION",  # This will be replaced by svc
    "compression_requested": {"compression_enum": "gamma fix colorspace"},
}
behavior_videos_task = {
    "skip_task": False,
    "image": "ghcr.io/allenneuraldynamics/aind-behavior-video-transformation",
    "image_version": "0.1.7",
    "image_resources": {
        "memory_per_cpu": {"set": True, "number": 250},
        "minimum_cpus_per_node": 32,
        "partition": "aind",
        "qos": "dev",
        "standard_error": (
            "/allen/aind/scratch/svc_aind_airflow/dev/logs/%x_%j_error.out"
        ),
        "tasks": 1,
        "time_limit": {"set": True, "number": 720},
        "standard_output": (
            "/allen/aind/scratch/svc_aind_airflow/dev/logs/%x_%j.out"
        ),
        "environment": [
            "PATH=/bin:/usr/bin/:/usr/local/bin/",
            "LD_LIBRARY_PATH=/lib/:/lib64/:/usr/local/lib",
        ],
        "current_working_directory": ".",
    },
    "job_settings": behavior_video_job_settings,
    "command_script": (
        "#!/bin/bash \nsingularity exec --cleanenv "
        "docker://%IMAGE:%IMAGE_VERSION python -m "
        "aind_behavior_video_transformation.etl "
        "--job-settings ' %JOB_SETTINGS '"
    ),
}

modality_transformation_settings = {
    "behavior": behavior_task,
    "behavior-videos": behavior_videos_task,
}

gather_preliminary_metadata = Task(
    job_settings={
        "metadata_dir": (
            "/allen/aind/scratch/svc_aind_upload/test_data_sets/"
            "behavior_711256_2024-05-09_12-31-22/metadata-dir"
        )
    }
)


upload_job_configs_v2 = UploadJobConfigsV2(
    job_type=job_type,
    project_name="Behavior Platform",
    platform=Platform.BEHAVIOR,
    modalities=[Modality.BEHAVIOR, Modality.BEHAVIOR_VIDEOS],
    subject_id="711256",
    acq_datetime=acq_datetime,
    tasks={
        "modality_transformation_settings": modality_transformation_settings,
        "gather_preliminary_metadata": gather_preliminary_metadata,
    },
)

submit_request_v2 = SubmitJobRequestV2(
    upload_jobs=[upload_job_configs_v2],
)

post_request_content = submit_request_v2.model_dump(
    mode="json", exclude_none=True
)

# Please use the production endpoint for submitting jobs and the dev endpoint
# for running tests.
# endpoint = "http://aind-data-transfer-service"
endpoint = "http://aind-data-transfer-service-dev"  # For testing

submit_job_response = requests.post(
    url=f"{endpoint}/api/v2/submit_jobs",
    json=post_request_content,
)
print(submit_job_response.status_code)
print(submit_job_response.json())
